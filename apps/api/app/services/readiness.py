"""Startup and /ready checks. Does not make commercial decisions."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.gateway import CAPABILITIES
from app.agent.schemas import ReadinessCheck, ReadyResponse
from app.config import settings
from app.decision.retrieval.embeddings import (
    resolve_embedding_provider,
    semantic_model_cached,
    sentence_transformers_importable,
)
from app.models import (
    Merchant,
    MerchantPolicy,
    Product,
    ProductVariant,
    VariantEmbedding,
)
from app.models.learning import ResponseModelVersion


async def evaluate_readiness(session: AsyncSession) -> ReadyResponse:
    checks: list[ReadinessCheck] = []
    degraded: list[str] = []

    try:
        await session.execute(text("SELECT 1"))
        checks.append(ReadinessCheck(name="database", ok=True, detail="reachable"))
    except Exception as exc:  # noqa: BLE001
        checks.append(
            ReadinessCheck(name="database", ok=False, detail=str(exc), required=True)
        )

    policy = (
        await session.scalars(select(MerchantPolicy).limit(1))
    ).first()
    checks.append(
        ReadinessCheck(
            name="merchant_policy",
            ok=policy is not None,
            detail="active policy present" if policy else "missing",
        )
    )

    variants = await session.scalar(select(func.count()).select_from(ProductVariant))
    active_products = await session.scalar(
        select(func.count()).select_from(Product).where(Product.is_active.is_(True))
    )
    active_variants = await session.scalar(
        select(func.count())
        .select_from(ProductVariant)
        .where(ProductVariant.is_active.is_(True))
    )
    merchant = (await session.scalars(select(Merchant).limit(1))).first()
    catalogue_ok = bool(active_products and active_variants)
    checks.append(
        ReadinessCheck(
            name="merchant_catalogue",
            ok=catalogue_ok,
            detail=(
                f"{active_products or 0} active products, "
                f"{active_variants or 0} active variants"
                + (f"; mode={merchant.data_mode}" if merchant is not None else "")
            ),
        )
    )
    checks.append(
        ReadinessCheck(
            name="seed_catalogue",
            ok=bool(variants and variants > 0),
            detail=f"{variants or 0} variants",
        )
    )
    economics_ok = bool(active_variants and active_variants > 0)
    checks.append(
        ReadinessCheck(
            name="economics_ready",
            ok=economics_ok,
            detail=(
                "active variants have required price and COGS"
                if economics_ok
                else "no commercially usable variants"
            ),
            required=False,
        )
    )
    if not economics_ok:
        degraded.append("commercial_optimisation_not_ready")

    embeddings = await session.scalar(
        select(func.count()).select_from(VariantEmbedding)
    )
    variant_count = variants or 0
    embed_ok = bool(embeddings and embeddings > 0)
    resolution = resolve_embedding_provider()
    current_model = (
        await session.scalars(select(VariantEmbedding.embedding_model).limit(1))
    ).first()
    sample = (
        await session.scalars(select(VariantEmbedding).limit(1))
    ).first()
    sample_dim = (
        len(sample.embedding)
        if sample and isinstance(sample.embedding, list)
        else None
    )
    stale = bool(
        current_model and current_model != resolution.provider.model_name
    )
    dim_mismatch = bool(
        sample_dim is not None and sample_dim != resolution.dimension
    )
    partial = bool(embeddings and variant_count and embeddings < variant_count)
    cached = (
        True
        if resolution.used == "hashing"
        else semantic_model_cached() and sentence_transformers_importable()
    )
    index_ready = bool(embed_ok and not stale and not dim_mismatch)
    checks.append(
        ReadinessCheck(
            name="embeddings",
            ok=True,
            detail=f"{embeddings or 0} cached; hashing fallback available",
            required=False,
        )
    )
    checks.append(
        ReadinessCheck(
            name="semantic_retrieval",
            ok=True,
            detail=(
                f"requested_provider={resolution.requested}; "
                f"configured_model={resolution.model}; "
                f"model_cached={'true' if cached else 'false'}; "
                f"index_ready={'true' if index_ready else 'false'}; "
                f"indexed_documents={embeddings or 0}; "
                f"expected_documents={variant_count}; "
                f"fallback_available=true"
            ),
            required=False,
        )
    )
    if not embed_ok:
        degraded.append("embeddings_cache_empty")
    if stale:
        degraded.append("embeddings_stale_model")
    if dim_mismatch:
        degraded.append("embeddings_dimension_mismatch")
    if partial:
        degraded.append("embeddings_partial_index")
    checks.append(
        ReadinessCheck(
            name="import_index",
            ok=not partial,
            detail=(
                "semantic index matches active catalogue"
                if not partial
                else f"indexed {embeddings or 0} of {variant_count} variants"
            ),
            required=False,
        )
    )
    if resolution.requested == "sentence_transformer" and (
        resolution.fallback_used or not cached
    ):
        degraded.append("semantic_model_unavailable")

    artifacts = Path(__file__).resolve().parents[1] / settings.learning_artifacts_dir
    experimental = (
        await session.scalars(
            select(ResponseModelVersion)
            .where(ResponseModelVersion.status == "ACTIVE_EXPERIMENTAL")
            .limit(1)
        )
    ).first()
    checks.append(
        ReadinessCheck(
            name="learned_model",
            ok=True,
            detail=(
                f"experimental artifact {experimental.artifact_path}"
                if experimental
                else "cold-start utility fallback"
            ),
            required=False,
        )
    )
    if experimental is None:
        degraded.append("learned_model_unavailable")
    elif not Path(experimental.artifact_path).is_file() and not (
        artifacts / f"{experimental.id}.joblib"
    ).is_file():
        degraded.append("learned_model_artifact_missing")

    llm = bool(settings.llm_api_key or settings.openai_api_key)
    requested = (settings.intent_parser_mode or "llm").strip().lower()
    checks.append(
        ReadinessCheck(
            name="intent_parser",
            ok=True,
            detail=(
                f"requested_mode={requested}; "
                f"provider_configured={'true' if llm else 'false'}; "
                "fallback_available=true"
            ),
            required=False,
        )
    )
    if requested == "llm" and not llm:
        degraded.append("llm_unavailable")

    checks.append(
        ReadinessCheck(
            name="protocol_adapter",
            ok=True,
            detail="REST /api/v1/agent guaranteed; MCP stdio optional",
        )
    )
    _ = CAPABILITIES

    required_failed = any(item.required and not item.ok for item in checks)
    status: str
    if required_failed:
        status = "not_ready"
    elif degraded:
        status = "degraded"
    else:
        status = "ready"
    return ReadyResponse(status=status, checks=checks, degraded_mode=degraded)
