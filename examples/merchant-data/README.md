# Example merchant feed

Versioned snapshot schema: `1.0`.

This is a fictional **Harbor Sound Co.** catalogue. It is an
`EXAMPLE_MERCHANT_IMPORT`, not a live retailer extract and not the
Astra Electronics demo seed.

```
Merchant feed (JSON or CSV)
    ↓
Ingestion adapter
    ↓
Canonical AstraOS model
    ↓
Decision engine
```

## JSON

`harbor-sound.json`

External identifiers:

- products: `external_id`
- variants: `sku`
- options: `code`

Do not send AstraOS database UUIDs.

Money fields accept `A$279`, `279`, or `price_cents`.
Currency must be `AUD`. Missing COGS is an error. Missing optional
attributes stay unknown.

## CSV bundle

Directory or zip of:

| File | Identity |
| --- | --- |
| merchant.csv | optional merchant row |
| products.csv | `external_id` |
| variants.csv | `sku`, `product_external_id` |
| inventory.csv | `sku`, `units_available` (physical on-hand) |
| delivery.csv | `code` |
| warranties.csv | `code` |
| bundles.csv | `code` |
| returns.csv | `code` |
| variant_delivery.csv | `sku`, `code` |
| variant_warranty.csv | `sku`, `code` |
| variant_bundle.csv | `sku`, `code` |
| variant_returns.csv | `sku`, `code` |
| evidence.csv | `sku`, `attribute_name` |

## CLI

```bash
python -m app.cli ingest --source json --file examples/merchant-data/harbor-sound.json
python -m app.cli ingest --source json --file examples/merchant-data/harbor-sound.json --apply
python -m app.cli ingest --source csv --file examples/merchant-data/csv --apply
```
