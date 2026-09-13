# Phase 6 — Merchant Data Ingestion

Phase 6 adds a merchant ingestion boundary so AstraOS can load a real
catalogue without editing Python fixtures. Downstream decision services
still operate only on the canonical commerce model. Phase 1–5 artifacts
were not overwritten. Commercial decision formulas were not changed.

## Previous Data Model

Confirmed before this phase:

- Canonical ORM remains `Product`, `ProductVariant`, `InventoryRecord`,
  `DeliveryOption`, `WarrantyOption`, `BundleOption`, `ReturnPolicy`,
  `AttributeEvidence`, `DataSource`, `MerchantPolicy`
- Demo merchant: Astra Electronics, 12 brands, deterministic seed
- Identity was internal UUID + SKU. No stable `external_id` on products
- Seed evidence was labelled as AstraOS synthetic fixtures
- Semantic documents (`product_semantic.v1`) hash name, brand, category,
  capability attributes, and same-day eligibility — not price or stock
- `make reset-demo` rebuilds the bundled seed and must keep working

## New Ingestion Architecture

```
EXTERNAL MERCHANT DATA
        ↓
MerchantDataAdapter (JSON / CSV)
        ↓
ExternalMerchantSnapshot
        ↓
VALIDATION
        ↓
NORMALISATION
        ↓
CanonicalMerchantSnapshot
        ↓
MerchantIngestionService (upsert + lineage)
        ↓
Canonical AstraOS model
        ↓
Selective semantic index refresh
        ↓
Ready for decisioning
```

Package: `apps/api/app/ingestion/`. Adapters read only. They do not
write SQLAlchemy rows. Routes and the CLI call the service, not the
database directly.

## Supported Sources

- Versioned JSON snapshot (`schema_version: "1.0"`)
- CSV directory or zip of entity files

Shopify, SAP, PIM, ERP, and OMS connectors are not implemented. They
would plug into `MerchantDataAdapter`.

## External Schema

Documented in `examples/merchant-data/README.md`.

Identity:

- products: `external_id` (not display name)
- variants: `sku`
- options: `code`

Database UUIDs are not required input. Stable UUIDs are derived with
`uuid5` from an ingestion namespace.

Example feed: fictional **Harbor Sound Co.**
(`EXAMPLE_MERCHANT_IMPORT`). It is not an export of the Astra Electronics
seed.

| Entity | Count |
| --- | ---: |
| Products | 14 |
| Variants | 15 |
| Inventory | 15 |
| Delivery options | 3 |
| Warranties | 2 |
| Bundles | 2 |
| Return policies | 2 |
| Evidence facts | 7 |

## Validation

Errors (record cannot enter the canonical model):

- unsupported schema version
- missing product `external_id` / name
- missing variant SKU
- orphan variant / inventory / evidence / bundle link
- duplicate or conflicting external IDs (not last-row-wins)
- non-positive price, negative COGS, negative inventory
- currency ≠ AUD
- invalid delivery enum / verification status

Warnings (record may enter; uncertainty is preserved):

- missing optional attributes (`battery_hours`, `weight_g`, …)
- unnamed provenance source type
- reservation clamp when imported physical stock < AstraOS reservations

Missing COGS is an error. The canonical `cogs_cents` column is NOT NULL
and AstraOS will not invent margin.

## Normalisation

- Money: `A$279`, `279`, `price_cents` → integer AUD cents
- Weight: `230 grams`, `0.23 kg` → grams
- Warranty: `36 months`, `3 years` → months
- Delivery: `same-day`, `SAME DAY` → `SAME_DAY`
- Currency: AUD only. No FX.

If a value is absent, it stays absent / UNKNOWN. Harbor Mini has no
`battery_hours`. Harbor Night has no `weight_g`. Those keys are omitted.

## Idempotency

Upsert on `external_id` / `sku` / option `code`. Canonical fingerprints
detect unchanged rows.

Eval on Harbor Sound:

- first apply: 14 products created, 15 variants created
- exact duplicate: created = 0, updated = 0, unchanged = 60
- rename one product: products updated = 1, embeddings refreshed = 1

## Full Snapshot Semantics

Default mode is `FULL` with `deactivate_scope=source`.

A full snapshot means: this source is the complete current set for
**that source system**. Missing imported products/variants become
inactive. Seed rows (`source_system` is null) stay active.

`DELTA` upserts only. Hard delete is not used; historical orders remain
valid.

## Evidence / Provenance

Imported facts carry:

- `source_type` (`MERCHANT_PRODUCT_FEED`, `MERCHANT_INVENTORY`,
  `PRICING_FEED`, `WARRANTY_POLICY`, `RETURN_POLICY`,
  `EXAMPLE_MERCHANT_IMPORT`)
- `source_record_id`
- `import_run_id`
- `observed_at` / `expires_at` from the feed when supplied

Imported data is never labelled as an AstraOS synthetic fixture. The
example feed is labelled as an example import, not a live retailer.

## Semantic Reindexing

After apply, only variants whose semantic fingerprint changed are
re-embedded.

- name / brand / category / description / semantic attributes / same-day
  → refresh
- inventory quantity → no re-embed
- price / COGS → no re-embed (`product_semantic.v1` does not include them)

Harbor first apply: 15 documents changed, 15 embeddings refreshed
(40.3 ms hashing provider). Rename: 1 refreshed.

## API

Merchant-side only. Not on `/api/v1/agent/*`.

- `POST /api/v1/merchant/ingestion/validate` — dry-run
- `POST /api/v1/merchant/ingestion/import` — apply
- `GET /api/v1/merchant/ingestion/runs`
- `GET /api/v1/merchant/ingestion/runs/{id}`
- `GET /api/v1/merchant/ingestion/status`

Uploads accept JSON `{snapshot}` or `content_base64` (CSV/zip). Limit
2 MB. `.json` / `.csv` / `.zip` only. Pickle is rejected.

## CLI

```bash
python -m app.cli ingest --source json --file examples/merchant-data/harbor-sound.json
python -m app.cli ingest --source json --file examples/merchant-data/harbor-sound.json --apply
make ingest
make ingest APPLY=1
```

Default is dry-run.

## Merchant Data UI

`IngestionPanel` on Merchant Data:

- Upload merchant feed (JSON / CSV / zip)
- Validation summary (received, would create/update, warnings, errors)
- Apply import
- Compact run history (time, source, status, counts, index)

Imported catalogue rows show an Imported badge. Product inspector shows
the feed source. Decision screens do not branch on `data_mode`.

## End-to-End Imported Merchant Test

Eval imported Harbor Sound, temporarily deactivated the demo seed, then
called the unchanged external Buyer Agent gateway:

- status `PROPOSED`
- policy `POLICY_SAFE`
- proposal SKU `HS-CAB-12-BLK` (Harbor Cabin 12)
- qualification: 15 imported variants checked, 5 eligible
- semantic top SKU `HS-CAB-12-BLK`
- 150 offer configurations, 60 policy-safe, 10 Pareto

No Buyer Agent changes. No seed function in that request path.

## Performance

Hashing embeddings, Harbor Sound (14 products / 15 variants):

| Step | ms |
| --- | ---: |
| Validation | 0.7 |
| Dry-run total | 40.3 |
| Apply total | 133.2 |
| DB apply | 78.8 |
| Reindex | 40.3 |

These are small-catalogue numbers, not enterprise throughput.

## Limitations

- Single-merchant hackathon database. Import attaches to the existing
  merchant (Astra Electronics) and sets `data_mode=MIXED`
- AUD only
- Full snapshot deactivation is source-scoped by default so the demo
  seed survives
- Missing COGS is rejected rather than marked “economics unavailable”
  after insert, because `cogs_cents` is required on the variant row
- `/ready` `import_index` compares embedding count to all variants,
  including a few pre-existing seed rows without vectors
- No Shopify/SAP/HTTP pull connector
- Example Harbor feed is fictional
- Inventory import is physical on-hand → `units_available`. Reservations
  are preserved. If reserved > imported physical stock, reserved is
  clamped and a warning is raised
- HTTP apply is merchant-namespace only; there is still no auth system

## Recommendation

Phase 7 — Hero Evidence Realification.

Do not begin Phase 7 automatically.
