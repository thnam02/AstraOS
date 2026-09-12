"""Startup and /ready checks. Does not make commercial decisions."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.gateway import CAPABILITIES
from app.agent.schemas import ReadinessCheck, ReadyResponse
from app.config import settings
from app.models import MerchantPolicy, ProductVariant, VariantEmbedding
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
    checks.append(
        ReadinessCheck(
            name="seed_catalogue",
            ok=bool(variants and variants > 0),
            detail=f"{variants or 0} variants",
        )
    )

    embeddings = await session.scalar(
        select(func.count()).select_from(VariantEmbedding)
    )
    embed_ok = bool(embeddings and embeddings > 0)
    checks.append(
        ReadinessCheck(
            name="embeddings",
            ok=True,
            detail=f"{embeddings or 0} cached; local hashing fallback available",
            required=False,
        )
    )
    if not embed_ok:
        degraded.append("embeddings_cache_empty")

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
