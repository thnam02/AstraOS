"""Apply a validated merchant feed onto the canonical catalogue."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ingestion.constants import (
    MODE_DEMO_SEED,
    MODE_IMPORTED,
    MODE_MIXED,
    SCOPE_MERCHANT,
    SCOPE_SOURCE,
    SNAPSHOT_FULL,
    STATUS_APPLYING,
    STATUS_COMPLETED,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_DRY_RUN,
    STATUS_FAILED,
    STATUS_REINDEXING,
    STATUS_VALIDATING,
    ingest_uuid,
)
from app.ingestion.fingerprint import (
    commercial_fingerprint,
    existing_commercial_fingerprint,
    existing_inventory_fingerprint,
    existing_product_fingerprint,
    inventory_fingerprint,
    product_fingerprint,
    semantic_fingerprint,
)
from app.ingestion.pipeline import (
    IngestionPayloadError,
    assert_upload_safe,
    prepare_snapshot,
)
from app.ingestion.reindex import refresh_semantic_index
from app.ingestion.result import IngestionIssue, IngestionResult
from app.ingestion.schemas import CanonicalMerchantSnapshot, CanonicalVariantLink
from app.models import (
    AttributeEvidence,
    BundleOption,
    DataSource,
    DeliveryOption,
    InventoryRecord,
    Merchant,
    MerchantIngestionRun,
    MerchantObjective,
    MerchantPolicy,
    Product,
    ProductVariant,
    ReturnPolicy,
    VariantBundleOption,
    VariantDeliveryOption,
    VariantReturnPolicy,
    VariantWarrantyOption,
    WarrantyOption,
)
from app.repositories.ingestion import IngestionRunRepository
from app.seed.ids import stable_uuid


class MerchantIngestionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = IngestionRunRepository(session)

    async def run(
        self,
        payload: bytes,
        *,
        source_type: str,
        source_name: str,
        snapshot_mode: str = SNAPSHOT_FULL,
        deactivate_scope: str = SCOPE_SOURCE,
        dry_run: bool = True,
        initiated_by: str = "merchant_api",
        commit: bool = True,
        skip_upload_check: bool = False,
    ) -> IngestionResult:
        started = time.perf_counter()
        if not skip_upload_check:
            assert_upload_safe(source_name, payload)
        result = IngestionResult(
            status=STATUS_VALIDATING,
            schema_version="",
            source_type=source_type,
            source_name=source_name,
            file_hash=None,
            snapshot_mode=snapshot_mode,
            dry_run=dry_run,
        )
        validate_started = time.perf_counter()
        try:
            _external, canonical, issues, digest = prepare_snapshot(
                payload, source_type=source_type, source_name=source_name
            )
        except (IngestionPayloadError, ValueError) as exc:
            result.issues.append(
                IngestionIssue("ERROR", "invalid_feed", str(exc), location="file")
            )
            result.status = STATUS_FAILED
            result.total_ms = (time.perf_counter() - started) * 1000
            await self._persist_run(result, initiated_by=initiated_by, commit=commit)
            return result
        result.file_hash = digest
        result.issues.extend(issues)
        result.schema_version = (canonical.schema_version if canonical else "") or ""
        result.validation_ms = (time.perf_counter() - validate_started) * 1000
        if canonical is None or result.errors:
            result.status = STATUS_FAILED
            if canonical is not None:
                self._count_received(result, canonical)
                result.records_rejected = result.records_received
            result.rollup()
            result.total_ms = (time.perf_counter() - started) * 1000
            await self._persist_run(result, initiated_by=initiated_by, commit=commit)
            return result

        self._count_received(result, canonical)
        merchant = await self._ensure_merchant(canonical)
        await self._diff(result, canonical)
        if dry_run:
            result.status = STATUS_DRY_RUN
            result.merchant_data_mode = merchant.data_mode
            result.economics_ready = self._economics_ready(canonical)
            result.economics_reason = (
                None if result.economics_ready else "missing economics fields"
            )
            result.rollup()
            result.total_ms = (time.perf_counter() - started) * 1000
            await self._persist_run(
                result,
                merchant_id=merchant.id,
                initiated_by=initiated_by,
                commit=commit,
            )
            return result

        run = await self._persist_run(
            result,
            merchant_id=merchant.id,
            initiated_by=initiated_by,
            commit=False,
            status=STATUS_APPLYING,
        )
        apply_started = time.perf_counter()
        semantic_ids: set[uuid.UUID] = set()
        try:
            await self._apply(
                result,
                canonical,
                merchant=merchant,
                run_id=run.id,
                snapshot_mode=snapshot_mode,
                deactivate_scope=deactivate_scope,
                semantic_ids=semantic_ids,
            )
            await self.session.flush()
        except Exception as exc:  # noqa: BLE001
            await self.session.rollback()
            result.status = STATUS_FAILED
            result.issues.append(
                IngestionIssue("ERROR", "apply_failed", str(exc), location="apply")
            )
            result.total_ms = (time.perf_counter() - started) * 1000
            await self._persist_run(
                result,
                merchant_id=merchant.id,
                initiated_by=initiated_by,
                commit=commit,
            )
            return result
        result.apply_ms = (time.perf_counter() - apply_started) * 1000
        result.status = STATUS_REINDEXING
        if commit:
            await self._write_run_fields(run, result)
            await self.session.commit()

        result.semantic_documents_changed = len(semantic_ids)
        reindex_started = time.perf_counter()
        try:
            refreshed, reused = await refresh_semantic_index(
                self.session, sorted(semantic_ids)
            )
            result.embeddings_refreshed = refreshed
            result.embeddings_reused = reused
            index_status = "READY"
        except Exception as exc:  # noqa: BLE001
            result.issues.append(
                IngestionIssue(
                    "WARNING",
                    "reindex_failed",
                    f"Catalogue was saved but semantic refresh failed: {exc}",
                    location="index",
                )
            )
            index_status = "FAILED"
        result.reindex_ms = (time.perf_counter() - reindex_started) * 1000
        await self._refresh_data_mode(merchant)
        result.merchant_data_mode = merchant.data_mode
        result.economics_ready = True
        result.status = (
            STATUS_COMPLETED_WITH_WARNINGS
            if result.warnings or index_status == "FAILED"
            else STATUS_COMPLETED
        )
        result.rollup()
        result.total_ms = (time.perf_counter() - started) * 1000
        run = await self.runs.get(run.id) or run
        run.index_status = index_status
        await self._write_run_fields(run, result)
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
        result.run_id = str(run.id)
        return result

    async def list_runs(self, *, limit: int = 20) -> list[MerchantIngestionRun]:
        return list(await self.runs.list_recent(limit=limit))

    async def get_run(self, run_id: uuid.UUID) -> MerchantIngestionRun | None:
        return await self.runs.get(run_id)

    def _count_received(
        self, result: IngestionResult, snapshot: CanonicalMerchantSnapshot
    ) -> None:
        result.products.received = len(snapshot.products)
        result.variants.received = len(snapshot.variants)
        result.inventory.received = len(snapshot.inventory)
        result.delivery_options.received = len(snapshot.delivery_options)
        result.warranty_options.received = len(snapshot.warranties)
        result.bundles.received = len(snapshot.bundles)
        result.return_policies.received = len(snapshot.return_policies)
        result.evidence.received = len(snapshot.evidence)

    def _economics_ready(self, snapshot: CanonicalMerchantSnapshot) -> bool:
        return any(
            row.base_price_cents > 0 and row.cogs_cents >= 0
            for row in snapshot.variants
        )

    async def _diff(
        self, result: IngestionResult, snapshot: CanonicalMerchantSnapshot
    ) -> None:
        products = (
            {
                row.external_id: row
                for row in (
                    await self.session.scalars(
                        select(Product).where(
                            Product.external_id.in_(
                                [item.external_id for item in snapshot.products]
                            )
                        )
                    )
                ).all()
            }
            if snapshot.products
            else {}
        )
        variants = (
            {
                row.sku: row
                for row in (
                    await self.session.scalars(
                        select(ProductVariant)
                        .options(selectinload(ProductVariant.inventory))
                        .where(
                            ProductVariant.sku.in_(
                                [item.sku for item in snapshot.variants]
                            )
                        )
                    )
                ).all()
            }
            if snapshot.variants
            else {}
        )
        for product in snapshot.products:
            existing_product = products.get(product.external_id)
            if existing_product is None:
                result.products.created += 1
            elif existing_product_fingerprint(
                external_id=existing_product.external_id or product.external_id,
                name=existing_product.name,
                brand=existing_product.brand,
                category=existing_product.category,
                description=existing_product.description,
                model_number=existing_product.model_number,
                manufacturer=existing_product.manufacturer,
                is_active=existing_product.is_active,
            ) == product_fingerprint(product):
                result.products.unchanged += 1
            else:
                result.products.updated += 1
        for variant in snapshot.variants:
            existing_variant = variants.get(variant.sku)
            if existing_variant is None:
                result.variants.created += 1
            elif existing_commercial_fingerprint(
                sku=existing_variant.sku,
                currency=existing_variant.currency,
                base_price_cents=existing_variant.base_price_cents,
                cogs_cents=existing_variant.cogs_cents,
                variant_name=existing_variant.variant_name,
                is_active=existing_variant.is_active,
            ) == commercial_fingerprint(variant) and (
                existing_variant.attributes == variant.attributes
            ):
                result.variants.unchanged += 1
            else:
                result.variants.updated += 1
        for stock in snapshot.inventory:
            mapped = variants.get(stock.sku)
            record = mapped.inventory if mapped is not None else None
            if record is None:
                result.inventory.created += 1
            elif existing_inventory_fingerprint(
                sku=stock.sku,
                units_available=record.units_available,
                warehouse_code=record.warehouse_code,
            ) == inventory_fingerprint(stock):
                result.inventory.unchanged += 1
            else:
                result.inventory.updated += 1
        await self._diff_options(result, snapshot)
        result.evidence.created = len(snapshot.evidence)
        result.products.deactivated = await self._count_would_deactivate(
            snapshot, entity="product"
        )
        result.variants.deactivated = await self._count_would_deactivate(
            snapshot, entity="variant"
        )

    async def _count_would_deactivate(
        self, snapshot: CanonicalMerchantSnapshot, *, entity: str
    ) -> int:
        if entity == "product":
            incoming = {row.external_id for row in snapshot.products}
            products = (
                await self.session.scalars(
                    select(Product).where(
                        Product.source_system == snapshot.source_type,
                        Product.is_active.is_(True),
                    )
                )
            ).all()
            return sum(
                1 for product in products if (product.external_id or "") not in incoming
            )
        incoming_skus = {row.sku for row in snapshot.variants}
        variants = (
            await self.session.scalars(
                select(ProductVariant).where(
                    ProductVariant.source_system == snapshot.source_type,
                    ProductVariant.is_active.is_(True),
                )
            )
        ).all()
        return sum(1 for variant in variants if variant.sku not in incoming_skus)

    async def _diff_options(
        self, result: IngestionResult, snapshot: CanonicalMerchantSnapshot
    ) -> None:
        result.delivery_options.unchanged = len(snapshot.delivery_options)
        result.warranty_options.unchanged = len(snapshot.warranties)
        result.bundles.unchanged = len(snapshot.bundles)
        result.return_policies.unchanged = len(snapshot.return_policies)
        for item, model, bucket in (
            (snapshot.delivery_options, DeliveryOption, result.delivery_options),
            (snapshot.warranties, WarrantyOption, result.warranty_options),
            (snapshot.bundles, BundleOption, result.bundles),
            (snapshot.return_policies, ReturnPolicy, result.return_policies),
        ):
            bucket.unchanged = 0
            bucket.created = 0
            bucket.updated = 0
            for row in item:
                existing = (
                    await self.session.scalars(
                        select(model).where(model.code == row.code)
                    )
                ).first()
                if existing is None:
                    bucket.created += 1
                else:
                    bucket.unchanged += 1

    async def _apply(
        self,
        result: IngestionResult,
        snapshot: CanonicalMerchantSnapshot,
        *,
        merchant: Merchant,
        run_id: uuid.UUID,
        snapshot_mode: str,
        deactivate_scope: str,
        semantic_ids: set[uuid.UUID],
    ) -> None:
        _ = merchant
        option_ids = await self._upsert_options(snapshot)
        product_ids, semantic_products = await self._upsert_products(
            result, snapshot, run_id
        )
        variant_ids = await self._upsert_variants(
            result, snapshot, product_ids, run_id, semantic_ids
        )
        for sku, variant_id in variant_ids.items():
            product_ext = next(
                item.product_external_id
                for item in snapshot.variants
                if item.sku == sku
            )
            if product_ids.get(product_ext) in semantic_products:
                semantic_ids.add(variant_id)
        await self._upsert_inventory(result, snapshot, variant_ids)
        await self._upsert_links(snapshot, variant_ids, option_ids)
        await self._upsert_evidence(result, snapshot, variant_ids)
        if snapshot_mode == SNAPSHOT_FULL:
            await self._deactivate_missing(
                result, snapshot, deactivate_scope=deactivate_scope
            )

    async def _upsert_options(
        self, snapshot: CanonicalMerchantSnapshot
    ) -> dict[str, dict[str, uuid.UUID]]:
        ids: dict[str, dict[str, uuid.UUID]] = {
            "delivery": {},
            "warranty": {},
            "bundle": {},
            "return": {},
        }
        for delivery in snapshot.delivery_options:
            existing_delivery = (
                await self.session.scalars(
                    select(DeliveryOption).where(DeliveryOption.code == delivery.code)
                )
            ).first()
            if existing_delivery is None:
                existing_delivery = DeliveryOption(
                    id=ingest_uuid("delivery", delivery.code),
                    code=delivery.code,
                    name=delivery.name,
                    description=delivery.description,
                    delivery_days=delivery.delivery_days,
                    merchant_cost_cents=delivery.merchant_cost_cents,
                    customer_charge_cents=delivery.customer_charge_cents,
                    enabled=delivery.enabled,
                )
                self.session.add(existing_delivery)
            else:
                existing_delivery.name = delivery.name
                existing_delivery.description = delivery.description
                existing_delivery.delivery_days = delivery.delivery_days
                existing_delivery.merchant_cost_cents = delivery.merchant_cost_cents
                existing_delivery.customer_charge_cents = delivery.customer_charge_cents
                existing_delivery.enabled = delivery.enabled
            await self.session.flush()
            ids["delivery"][delivery.code] = existing_delivery.id
        for warranty in snapshot.warranties:
            existing_warranty = (
                await self.session.scalars(
                    select(WarrantyOption).where(WarrantyOption.code == warranty.code)
                )
            ).first()
            if existing_warranty is None:
                existing_warranty = WarrantyOption(
                    id=ingest_uuid("warranty", warranty.code),
                    code=warranty.code,
                    name=warranty.name,
                    months=warranty.months,
                    merchant_cost_cents=warranty.merchant_cost_cents,
                    customer_price_cents=warranty.customer_price_cents,
                    enabled=warranty.enabled,
                )
                self.session.add(existing_warranty)
            else:
                existing_warranty.name = warranty.name
                existing_warranty.months = warranty.months
                existing_warranty.merchant_cost_cents = warranty.merchant_cost_cents
                existing_warranty.customer_price_cents = warranty.customer_price_cents
                existing_warranty.enabled = warranty.enabled
            await self.session.flush()
            ids["warranty"][warranty.code] = existing_warranty.id
        for bundle in snapshot.bundles:
            existing_bundle = (
                await self.session.scalars(
                    select(BundleOption).where(BundleOption.code == bundle.code)
                )
            ).first()
            if existing_bundle is None:
                existing_bundle = BundleOption(
                    id=ingest_uuid("bundle", bundle.code),
                    code=bundle.code,
                    name=bundle.name,
                    description=bundle.description,
                    merchant_cost_cents=bundle.merchant_cost_cents,
                    customer_price_cents=bundle.customer_price_cents,
                    enabled=bundle.enabled,
                    attributes=bundle.attributes,
                )
                self.session.add(existing_bundle)
            else:
                existing_bundle.name = bundle.name
                existing_bundle.description = bundle.description
                existing_bundle.merchant_cost_cents = bundle.merchant_cost_cents
                existing_bundle.customer_price_cents = bundle.customer_price_cents
                existing_bundle.enabled = bundle.enabled
                existing_bundle.attributes = bundle.attributes
            await self.session.flush()
            ids["bundle"][bundle.code] = existing_bundle.id
        for policy in snapshot.return_policies:
            existing_policy = (
                await self.session.scalars(
                    select(ReturnPolicy).where(ReturnPolicy.code == policy.code)
                )
            ).first()
            if existing_policy is None:
                existing_policy = ReturnPolicy(
                    id=ingest_uuid("return", policy.code),
                    code=policy.code,
                    name=policy.name,
                    return_window_days=policy.return_window_days,
                    restocking_fee_rate=(
                        Decimal(str(policy.restocking_fee_rate))
                        if policy.restocking_fee_rate is not None
                        else None
                    ),
                    conditions=policy.conditions,
                    merchant_expected_cost_cents=policy.merchant_expected_cost_cents,
                    enabled=policy.enabled,
                )
                self.session.add(existing_policy)
            else:
                existing_policy.name = policy.name
                existing_policy.return_window_days = policy.return_window_days
                existing_policy.restocking_fee_rate = (
                    Decimal(str(policy.restocking_fee_rate))
                    if policy.restocking_fee_rate is not None
                    else None
                )
                existing_policy.conditions = policy.conditions
                existing_policy.merchant_expected_cost_cents = (
                    policy.merchant_expected_cost_cents
                )
                existing_policy.enabled = policy.enabled
            await self.session.flush()
            ids["return"][policy.code] = existing_policy.id
        if not ids["delivery"]:
            for delivery_row in (
                await self.session.scalars(select(DeliveryOption))
            ).all():
                ids["delivery"][delivery_row.code] = delivery_row.id
        if not ids["warranty"]:
            for warranty_row in (
                await self.session.scalars(select(WarrantyOption))
            ).all():
                ids["warranty"][warranty_row.code] = warranty_row.id
        if not ids["bundle"]:
            for bundle_row in (await self.session.scalars(select(BundleOption))).all():
                ids["bundle"][bundle_row.code] = bundle_row.id
        if not ids["return"]:
            for policy_row in (await self.session.scalars(select(ReturnPolicy))).all():
                ids["return"][policy_row.code] = policy_row.id
        return ids

    async def _upsert_products(
        self,
        result: IngestionResult,
        snapshot: CanonicalMerchantSnapshot,
        run_id: uuid.UUID,
    ) -> tuple[dict[str, uuid.UUID], set[uuid.UUID]]:
        ids: dict[str, uuid.UUID] = {}
        semantic_products: set[uuid.UUID] = set()
        created = updated = unchanged = 0
        for item in snapshot.products:
            existing = (
                await self.session.scalars(
                    select(Product).where(Product.external_id == item.external_id)
                )
            ).first()
            digest = product_fingerprint(item)
            if existing is None:
                existing = Product(
                    id=ingest_uuid("product", item.external_id),
                    name=item.name,
                    brand=item.brand,
                    category=item.category,
                    description=item.description,
                    model_number=item.model_number,
                    manufacturer=item.manufacturer,
                    external_id=item.external_id,
                    source_system=snapshot.source_type,
                    source_record_id=item.external_id,
                    import_run_id=run_id,
                    is_active=item.is_active,
                )
                self.session.add(existing)
                created += 1
                semantic_products.add(existing.id)
            else:
                current = existing_product_fingerprint(
                    external_id=existing.external_id or item.external_id,
                    name=existing.name,
                    brand=existing.brand,
                    category=existing.category,
                    description=existing.description,
                    model_number=existing.model_number,
                    manufacturer=existing.manufacturer,
                    is_active=existing.is_active,
                )
                existing.name = item.name
                existing.brand = item.brand
                existing.category = item.category
                existing.description = item.description
                existing.model_number = item.model_number
                existing.manufacturer = item.manufacturer
                existing.external_id = item.external_id
                existing.source_system = snapshot.source_type
                existing.source_record_id = item.external_id
                existing.import_run_id = run_id
                existing.is_active = item.is_active
                if current == digest:
                    unchanged += 1
                else:
                    updated += 1
                    semantic_products.add(existing.id)
            await self.session.flush()
            ids[item.external_id] = existing.id
        result.products.created = created
        result.products.updated = updated
        result.products.unchanged = unchanged
        return ids, semantic_products

    async def _upsert_variants(
        self,
        result: IngestionResult,
        snapshot: CanonicalMerchantSnapshot,
        product_ids: dict[str, uuid.UUID],
        run_id: uuid.UUID,
        semantic_ids: set[uuid.UUID],
    ) -> dict[str, uuid.UUID]:
        products = {row.external_id: row for row in snapshot.products}
        same_day = {
            link.sku
            for link in snapshot.variant_delivery
            if link.available and link.option_code == "SAME_DAY"
        }
        ids: dict[str, uuid.UUID] = {}
        created = updated = unchanged = 0
        for item in snapshot.variants:
            product = products[item.product_external_id]
            existing = (
                await self.session.scalars(
                    select(ProductVariant)
                    .options(
                        selectinload(ProductVariant.product),
                        selectinload(ProductVariant.delivery_options).selectinload(
                            VariantDeliveryOption.delivery_option
                        ),
                    )
                    .where(ProductVariant.sku == item.sku)
                )
            ).first()
            product_id = product_ids[item.product_external_id]
            next_semantic = semantic_fingerprint(
                product, item, same_day=item.sku in same_day
            )
            if existing is None:
                existing = ProductVariant(
                    id=ingest_uuid("variant", item.sku),
                    product_id=product_id,
                    sku=item.sku,
                    variant_name=item.variant_name,
                    currency=item.currency,
                    base_price_cents=item.base_price_cents,
                    cogs_cents=item.cogs_cents,
                    attributes=item.attributes,
                    is_active=item.is_active,
                    source_system=snapshot.source_type,
                    source_record_id=item.sku,
                    import_run_id=run_id,
                )
                self.session.add(existing)
                created += 1
                semantic_ids.add(existing.id)
            else:
                prev_same_day = any(
                    link.available
                    and link.delivery_option is not None
                    and link.delivery_option.code == "SAME_DAY"
                    for link in existing.delivery_options
                )
                previous_product = existing.product
                prev_semantic = semantic_fingerprint(
                    type(product)(
                        external_id=item.product_external_id,
                        name=previous_product.name,
                        brand=previous_product.brand,
                        category=previous_product.category,
                        description=previous_product.description,
                        model_number=previous_product.model_number,
                        manufacturer=previous_product.manufacturer,
                        is_active=previous_product.is_active,
                    ),
                    type(item)(
                        sku=existing.sku,
                        product_external_id=item.product_external_id,
                        variant_name=existing.variant_name,
                        currency=existing.currency,
                        base_price_cents=existing.base_price_cents,
                        cogs_cents=existing.cogs_cents,
                        attributes=dict(existing.attributes or {}),
                        is_active=existing.is_active,
                    ),
                    same_day=prev_same_day,
                )
                commercial_changed = existing_commercial_fingerprint(
                    sku=existing.sku,
                    currency=existing.currency,
                    base_price_cents=existing.base_price_cents,
                    cogs_cents=existing.cogs_cents,
                    variant_name=existing.variant_name,
                    is_active=existing.is_active,
                ) != commercial_fingerprint(item)
                attr_changed = dict(existing.attributes or {}) != item.attributes
                existing.product_id = product_id
                existing.variant_name = item.variant_name
                existing.currency = item.currency
                existing.base_price_cents = item.base_price_cents
                existing.cogs_cents = item.cogs_cents
                existing.attributes = item.attributes
                existing.is_active = item.is_active
                existing.source_system = snapshot.source_type
                existing.source_record_id = item.sku
                existing.import_run_id = run_id
                if commercial_changed or attr_changed:
                    updated += 1
                else:
                    unchanged += 1
                if prev_semantic != next_semantic:
                    semantic_ids.add(existing.id)
            await self.session.flush()
            ids[item.sku] = existing.id
        result.variants.created = created
        result.variants.updated = updated
        result.variants.unchanged = unchanged
        return ids

    async def _upsert_inventory(
        self,
        result: IngestionResult,
        snapshot: CanonicalMerchantSnapshot,
        variant_ids: dict[str, uuid.UUID],
    ) -> None:
        created = updated = unchanged = 0
        for item in snapshot.inventory:
            variant_id = variant_ids[item.sku]
            existing = (
                await self.session.scalars(
                    select(InventoryRecord).where(
                        InventoryRecord.variant_id == variant_id
                    )
                )
            ).first()
            if existing is None:
                self.session.add(
                    InventoryRecord(
                        id=ingest_uuid("inventory", item.sku),
                        variant_id=variant_id,
                        units_available=item.units_available,
                        units_reserved=0,
                        warehouse_code=item.warehouse_code,
                    )
                )
                created += 1
                continue
            digest = inventory_fingerprint(item)
            current = existing_inventory_fingerprint(
                sku=item.sku,
                units_available=existing.units_available,
                warehouse_code=existing.warehouse_code,
            )
            reserved = int(existing.units_reserved)
            if reserved > item.units_available:
                result.issues.append(
                    IngestionIssue(
                        "WARNING",
                        "reservation_clamped",
                        (
                            f"SKU {item.sku}: imported physical stock "
                            f"{item.units_available} is below AstraOS reservations "
                            f"{reserved}. Reservations were clamped. External quantity "
                            "is treated as physical on-hand, not available-to-sell."
                        ),
                        location=f"inventory[{item.sku}]",
                        record_id=item.sku,
                    )
                )
                reserved = item.units_available
            existing.units_available = item.units_available
            existing.units_reserved = reserved
            existing.warehouse_code = item.warehouse_code
            if current == digest:
                unchanged += 1
            else:
                updated += 1
        result.inventory.created = created
        result.inventory.updated = updated
        result.inventory.unchanged = unchanged

    async def _upsert_links(
        self,
        snapshot: CanonicalMerchantSnapshot,
        variant_ids: dict[str, uuid.UUID],
        option_ids: dict[str, dict[str, uuid.UUID]],
    ) -> None:
        await self._replace_links(
            snapshot.variant_delivery,
            variant_ids,
            option_ids["delivery"],
            VariantDeliveryOption,
            "delivery_option_id",
        )
        await self._replace_links(
            snapshot.variant_warranty,
            variant_ids,
            option_ids["warranty"],
            VariantWarrantyOption,
            "warranty_option_id",
        )
        await self._replace_links(
            snapshot.variant_bundle,
            variant_ids,
            option_ids["bundle"],
            VariantBundleOption,
            "bundle_option_id",
        )
        await self._replace_links(
            snapshot.variant_returns,
            variant_ids,
            option_ids["return"],
            VariantReturnPolicy,
            "return_policy_id",
        )

    async def _replace_links(
        self,
        links: list[CanonicalVariantLink],
        variant_ids: dict[str, uuid.UUID],
        option_ids: dict[str, uuid.UUID],
        model: type[Any],
        fk_name: str,
    ) -> None:
        touched = {variant_ids[link.sku] for link in links if link.sku in variant_ids}
        if not touched:
            return
        existing = (
            await self.session.scalars(
                select(model).where(model.variant_id.in_(touched))
            )
        ).all()
        for row in existing:
            await self.session.delete(row)
        await self.session.flush()
        for link in links:
            if link.sku not in variant_ids or link.option_code not in option_ids:
                continue
            kwargs = {
                "id": ingest_uuid(model.__tablename__, link.sku, link.option_code),
                "variant_id": variant_ids[link.sku],
                fk_name: option_ids[link.option_code],
                "available": link.available,
            }
            self.session.add(model(**kwargs))

    async def _upsert_evidence(
        self,
        result: IngestionResult,
        snapshot: CanonicalMerchantSnapshot,
        variant_ids: dict[str, uuid.UUID],
    ) -> None:
        created = updated = unchanged = 0
        for item in snapshot.evidence:
            source = await self._source(item.source_type, item.source_name)
            variant_id = variant_ids[item.sku]
            existing = (
                await self.session.scalars(
                    select(AttributeEvidence).where(
                        AttributeEvidence.variant_id == variant_id,
                        AttributeEvidence.attribute_name == item.attribute_name,
                        AttributeEvidence.source_id == source.id,
                    )
                )
            ).first()
            if existing is None:
                self.session.add(
                    AttributeEvidence(
                        id=ingest_uuid(
                            "evidence", item.sku, item.attribute_name, item.source_type
                        ),
                        variant_id=variant_id,
                        attribute_name=item.attribute_name,
                        value=item.value,
                        source_id=source.id,
                        source_reference=item.source_reference,
                        confidence=item.confidence,
                        verification_status=item.verification_status,
                        observed_at=item.observed_at,
                        expires_at=item.expires_at,
                    )
                )
                created += 1
                continue
            changed = (
                existing.value != item.value
                or existing.verification_status != item.verification_status
                or existing.source_reference != item.source_reference
            )
            existing.value = item.value
            existing.source_reference = item.source_reference
            existing.confidence = item.confidence
            existing.verification_status = item.verification_status
            existing.observed_at = item.observed_at
            existing.expires_at = item.expires_at
            if changed:
                updated += 1
            else:
                unchanged += 1
        result.evidence.created = created
        result.evidence.updated = updated
        result.evidence.unchanged = unchanged

    async def _deactivate_missing(
        self,
        result: IngestionResult,
        snapshot: CanonicalMerchantSnapshot,
        *,
        deactivate_scope: str,
    ) -> None:
        incoming_products = {row.external_id for row in snapshot.products}
        incoming_skus = {row.sku for row in snapshot.variants}
        product_query = select(Product).where(Product.is_active.is_(True))
        variant_query = select(ProductVariant).where(ProductVariant.is_active.is_(True))
        if deactivate_scope != SCOPE_MERCHANT:
            product_query = product_query.where(
                Product.source_system == snapshot.source_type
            )
            variant_query = variant_query.where(
                ProductVariant.source_system == snapshot.source_type
            )
        deactivated_products = 0
        for product in (await self.session.scalars(product_query)).all():
            if (product.external_id or "") not in incoming_products:
                product.is_active = False
                deactivated_products += 1
        deactivated_variants = 0
        for variant in (await self.session.scalars(variant_query)).all():
            if variant.sku not in incoming_skus:
                variant.is_active = False
                deactivated_variants += 1
        result.products.deactivated = deactivated_products
        result.variants.deactivated = deactivated_variants

    async def _source(self, source_type: str, name: str) -> DataSource:
        existing = (
            await self.session.scalars(
                select(DataSource).where(
                    DataSource.source_type == source_type, DataSource.name == name
                )
            )
        ).first()
        if existing is not None:
            return existing
        row = DataSource(
            id=ingest_uuid("source", source_type, name),
            name=name,
            source_type=source_type,
            reference=f"import://{source_type}",
            description="Imported merchant evidence. Not an AstraOS synthetic fixture.",
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def _ensure_merchant(self, snapshot: CanonicalMerchantSnapshot) -> Merchant:
        merchant = (await self.session.scalars(select(Merchant).limit(1))).first()
        if merchant is not None:
            return merchant
        merchant = Merchant(
            id=stable_uuid("merchant", snapshot.merchant_code or "IMPORTED"),
            name=snapshot.merchant_name or "Imported merchant",
            code=snapshot.merchant_code or "IMPORTED_MERCHANT",
            currency=snapshot.currency,
            data_mode=MODE_IMPORTED,
        )
        self.session.add(merchant)
        await self.session.flush()
        self.session.add(
            MerchantPolicy(
                id=stable_uuid("policy", "imported"),
                merchant_id=merchant.id,
                name="Imported merchant default policy",
                is_active=True,
                minimum_margin_rate=Decimal("0.1500"),
                maximum_discount_rate=Decimal("0.1000"),
                delivery_subsidy_enabled=True,
                warranty_upgrade_enabled=True,
                bundle_enabled=True,
                flexible_returns_enabled=True,
                loyalty_enabled=False,
                maximum_delivery_subsidy_cents=1000,
                maximum_warranty_subsidy_cents=1400,
                maximum_bundle_subsidy_cents=900,
            )
        )
        self.session.add(
            MerchantObjective(
                id=stable_uuid("objective", "imported"),
                merchant_id=merchant.id,
                mode="BALANCED",
                buyer_weight=Decimal("0.5000"),
                merchant_weight=Decimal("0.5000"),
                version="merchant-objective-v1",
                is_active=True,
            )
        )
        await self.session.flush()
        return merchant

    async def _refresh_data_mode(self, merchant: Merchant) -> None:
        imported = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Product)
                .where(
                    Product.is_active.is_(True),
                    Product.source_system.is_not(None),
                )
            )
            or 0
        )
        seed = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Product)
                .where(Product.is_active.is_(True), Product.source_system.is_(None))
            )
            or 0
        )
        if imported and seed:
            merchant.data_mode = MODE_MIXED
        elif imported:
            merchant.data_mode = MODE_IMPORTED
        else:
            merchant.data_mode = MODE_DEMO_SEED

    async def _persist_run(
        self,
        result: IngestionResult,
        *,
        merchant_id: uuid.UUID | None = None,
        initiated_by: str,
        commit: bool,
        status: str | None = None,
    ) -> MerchantIngestionRun:
        result.rollup()
        run = MerchantIngestionRun(
            merchant_id=merchant_id,
            source_type=result.source_type,
            source_name=result.source_name,
            schema_version=result.schema_version or "1.0",
            snapshot_mode=result.snapshot_mode,
            file_hash=result.file_hash,
            status=status or result.status,
            initiated_by=initiated_by,
        )
        await self._write_run_fields(run, result)
        self.session.add(run)
        await self.session.flush()
        result.run_id = str(run.id)
        if commit:
            await self.session.commit()
        return run

    async def _write_run_fields(
        self, run: MerchantIngestionRun, result: IngestionResult
    ) -> None:
        result.rollup()
        run.status = result.status
        run.records_received = result.records_received
        run.records_created = result.records_created
        run.records_updated = result.records_updated
        run.records_unchanged = result.records_unchanged
        run.records_rejected = result.records_rejected
        run.records_deactivated = result.records_deactivated
        run.warning_count = len(result.warnings)
        run.error_count = len(result.errors)
        run.semantic_documents_changed = result.semantic_documents_changed
        run.embeddings_refreshed = result.embeddings_refreshed
        run.warnings = [item.as_dict() for item in result.warnings[:50]]
        run.errors = [item.as_dict() for item in result.errors[:50]]
        run.summary = result.as_dict()
        run.completed_at = datetime.now(UTC)
        run.file_hash = result.file_hash
        if result.status in {
            STATUS_COMPLETED,
            STATUS_COMPLETED_WITH_WARNINGS,
            STATUS_DRY_RUN,
            STATUS_FAILED,
        }:
            run.completed_at = datetime.now(UTC)
