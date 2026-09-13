#!/bin/sh
set -eu

echo "AstraOS API: migrating database…"
alembic upgrade head

echo "AstraOS API: ensuring demo catalogue…"
python - <<'PY'
import asyncio
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal
from app.models.product import ProductVariant
from app.seed.runner import run


async def ensure_seed() -> None:
    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(ProductVariant))
    if count and count > 0:
        print(f"catalogue already present ({count} variants); skip seed")
        return
    print("catalogue empty; running seed…")
    await run(reset=False)


asyncio.run(ensure_seed())
PY

PORT="${PORT:-8000}"
echo "AstraOS API: starting on :${PORT}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
