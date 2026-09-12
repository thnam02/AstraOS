"""One-off Stage 9 hero training. Synthetic outcomes only."""

from __future__ import annotations

import asyncio
import json
import os

os.environ.setdefault("POSTGRES_DB", "astraos_test")

from app.db.session import AsyncSessionLocal
from app.services.learning import LearningService


async def main() -> None:
    target = int(os.environ.get("LEARNING_TARGET", "2500"))
    seed = int(os.environ.get("ASTRAOS_LEARNING_SEED", "2026"))
    async with AsyncSessionLocal() as session:
        service = LearningService(session)
        dataset = await service.generate_dataset(
            interaction_count_target=target, seed=seed
        )
        print(
            json.dumps(
                {
                    "dataset_id": str(dataset.id),
                    "interaction_count": dataset.interaction_count,
                    "positive_count": dataset.positive_count,
                    "negative_count": dataset.negative_count,
                    "audit": dataset.dataset_metadata.get("audit"),
                    "build_ms": dataset.dataset_metadata.get("build_ms"),
                    "mission_count": dataset.dataset_metadata.get("mission_count"),
                    "leakage_violations": dataset.dataset_metadata.get(
                        "leakage_violations"
                    ),
                },
                indent=2,
            )
        )
        result = await service.train(dataset.id, seed=seed)
        slim_ablations = {
            name: {
                "brier": row["classification"]["brier"],
                "log_loss": row["classification"]["log_loss"],
                "roc_auc": row["classification"].get("roc_auc"),
                "top1": row["ranking"]["top1"],
            }
            for name, row in result["ablations"].items()
        }
        print(
            json.dumps(
                {
                    "selected_algorithm": result["selected_algorithm"],
                    "reports": result["reports"],
                    "ablations": slim_ablations,
                    "hero_mission": result["hero_mission"],
                    "timing": result["results"]["timing"],
                    "split": result["results"]["split"],
                    "disclaimer": result["disclaimer"],
                },
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
