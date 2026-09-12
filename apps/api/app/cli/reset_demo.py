"""Reset catalogue, policy, and demo commerce state. Seed 2026."""

from __future__ import annotations

import asyncio

from app.seed.runner import format_summary
from app.seed.runner import run as seed_run


def main() -> None:
    summary = asyncio.run(seed_run(reset=True))
    print("Demo reset complete. Deterministic seed 2026.")
    print(format_summary(summary))


if __name__ == "__main__":
    main()
