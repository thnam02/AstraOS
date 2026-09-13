"""Import a merchant JSON or CSV feed into the canonical catalogue."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from app.db.session import AsyncSessionLocal
from app.ingestion.adapters.csv_adapter import pack_csv_directory
from app.ingestion.constants import SOURCE_CSV, SOURCE_JSON
from app.ingestion.service import MerchantIngestionService


def _load_payload(path: Path, source: str) -> tuple[bytes, str, str]:
    if path.is_dir():
        return pack_csv_directory(path), SOURCE_CSV, f"{path.name}.zip"
    payload = path.read_bytes()
    key = source.strip().lower()
    if key in {"csv", SOURCE_CSV, "zip"}:
        return payload, SOURCE_CSV, path.name
    return payload, SOURCE_JSON, path.name


async def _run(args: argparse.Namespace) -> dict[str, object]:
    payload, source_type, name = _load_payload(Path(args.file), args.source)
    async with AsyncSessionLocal() as session:
        service = MerchantIngestionService(session)
        result = await service.run(
            payload,
            source_type=source_type,
            source_name=name,
            snapshot_mode=args.mode,
            deactivate_scope=args.scope,
            dry_run=not args.apply,
            initiated_by="cli",
        )
    return result.as_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a merchant catalogue feed.")
    parser.add_argument("--source", default="json", help="json or csv")
    parser.add_argument(
        "--file",
        required=True,
        help="JSON file, CSV zip, or CSV directory",
    )
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", help="Persist the feed")
    parser.add_argument("--mode", default="FULL", choices=("FULL", "DELTA"))
    parser.add_argument("--scope", default="source", choices=("source", "merchant"))
    args = parser.parse_args()
    report = asyncio.run(_run(args))
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
