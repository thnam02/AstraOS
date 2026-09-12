"""Rule vs LLM intent evaluation on the frozen labelled fixture."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path
from typing import Any

from app.decision.intent.parser import parse_intent
from app.decision.intent.provider import provider_configured
from app.eval.intent_cases import load_intent_eval_cases
from app.eval.intent_metrics import mean, score_case

ERROR_CATEGORIES = {
    "missed_hard_constraint": "critical_omission",
    "invented_hard_constraint": "hard_field_false_positive",
}


def _prf(rows: list[dict[str, Any]], key: str) -> dict[str, float]:
    return {
        "precision": round(mean(row[key]["precision"] for row in rows), 4),
        "recall": round(mean(row[key]["recall"] for row in rows), 4),
        "f1": round(mean(row[key]["f1"] for row in rows), 4),
    }


def _summarize(
    rows: list[dict[str, Any]],
    latencies: list[float],
    extras: dict[str, Any],
) -> dict[str, Any]:
    ordered = sorted(latencies)
    p95_index = min(len(ordered) - 1, max(0, round(0.95 * (len(ordered) - 1))))
    p95 = ordered[p95_index] if ordered else 0
    return {
        "cases": len(rows),
        "hard_constraints": _prf(rows, "hard"),
        "soft_preferences": _prf(rows, "preferences"),
        "context": _prf(rows, "contexts"),
        "desired_outcomes": _prf(rows, "outcomes"),
        "values": _prf(rows, "values"),
        "tradeoffs": _prf(rows, "tradeoffs"),
        "ambiguity": _prf(rows, "ambiguities"),
        "unsupported_needs": _prf(rows, "unsupported"),
        "hard_constraint_false_positive_rate": round(
            mean(1.0 if row["hard_field_false_positive"] else 0.0 for row in rows), 4
        ),
        "critical_constraint_omission_rate": round(
            mean(1.0 if row["critical_omission"] else 0.0 for row in rows), 4
        ),
        "schema_valid_rate": extras.get("schema_valid_rate", 1.0),
        "llm_success_rate": extras.get("llm_success_rate"),
        "fallback_rate": extras.get("fallback_rate", 0.0),
        "repair_rate": extras.get("repair_rate", 0.0),
        "mean_latency_ms": round(mean(latencies), 2) if latencies else 0.0,
        "p50_latency_ms": round(statistics.median(ordered), 2) if ordered else 0.0,
        "p95_latency_ms": round(p95, 2),
    }


async def evaluate_parser(mode: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    fallbacks = 0
    repairs = 0
    successes = 0
    errors: list[dict[str, Any]] = []
    for case in cases:
        started = time.perf_counter()
        intent = await parse_intent(case["query"], parser_mode=mode)
        latency = (time.perf_counter() - started) * 1000
        latencies.append(latency)
        meta = intent.parser_metadata
        if meta and meta.fallback_used:
            fallbacks += 1
        if meta and meta.repair_count:
            repairs += 1
        if mode != "llm" or (meta and meta.parser_used == "llm"):
            successes += 1
        scored = score_case(intent, case)
        scored["id"] = case["id"]
        scored["group"] = case.get("group")
        scored["latency_ms"] = round(latency, 2)
        scored["parser_used"] = intent.parser_type
        scored["fallback_used"] = bool(meta.fallback_used) if meta else False
        rows.append(scored)
        categories = _error_categories(scored)
        scored["error_categories"] = categories
        if categories:
            errors.append(
                {
                    "id": case["id"],
                    "query": case["query"],
                    "group": case.get("group"),
                    "categories": categories,
                    "critical_omissions": scored["critical_omissions"],
                    "hard_false_positives": scored["hard_false_positives"],
                    "parser_used": intent.parser_type,
                }
            )
    extras = {
        "schema_valid_rate": 1.0,
        "llm_success_rate": round(successes / len(cases), 4) if mode == "llm" else None,
        "fallback_rate": round(fallbacks / len(cases), 4) if cases else 0.0,
        "repair_rate": round(repairs / len(cases), 4) if cases else 0.0,
    }
    return {
        "mode": mode,
        "metrics": _summarize(rows, latencies, extras),
        "errors": errors[:40],
        "cases": rows,
    }


async def run_benchmark(*, include_llm: bool | None = None) -> dict[str, Any]:
    fixture = load_intent_eval_cases()
    cases = list(fixture["cases"])
    rule = await evaluate_parser("rule_based", cases)
    llm_configured = provider_configured()
    run_llm = include_llm if include_llm is not None else llm_configured
    llm: dict[str, Any] | None = None
    if run_llm:
        llm = await evaluate_parser("llm", cases)
    llm_measured = bool(
        llm
        and llm["metrics"].get("llm_success_rate")
        and llm["metrics"]["llm_success_rate"] > 0
    )
    return {
        "dataset_version": fixture["version"],
        "case_count": len(cases),
        "groups": _group_counts(cases),
        "rule_based": {"metrics": rule["metrics"], "errors": rule["errors"]},
        "llm": {"metrics": llm["metrics"], "errors": llm["errors"]} if llm else None,
        "llm_ran": bool(llm),
        "llm_configured": llm_configured,
        "llm_extraction_measured": llm_measured,
        "label": "SYNTHETIC LABELS ARE MANUAL. Not generated by the evaluated model.",
        "note": (
            None
            if llm_measured
            else (
                "LLM extraction quality was not measured. "
                "Without credentials the factory falls back to rule_based. "
                "Do not treat fallback F1 as LLM accuracy."
            )
        ),
    }


def _error_categories(scored: dict[str, Any]) -> list[str]:
    categories: list[str] = []
    if scored.get("critical_omission"):
        categories.append("missed_hard_constraint")
    if scored.get("hard_field_false_positive"):
        categories.append("invented_hard_constraint")
    if (
        scored["hard"]["f1"] < 1
        and scored["hard"]["precision"] < 1
        and not scored.get("hard_field_false_positive")
    ):
        categories.append("wrong_operator_or_normalization")
    if scored["preferences"]["recall"] > 0 and scored.get("hard_field_false_positive"):
        categories.append("preference_to_mandatory")
    if scored["tradeoffs"]["recall"] < 1:
        categories.append("missed_tradeoff")
    if scored["ambiguities"]["recall"] < 1:
        categories.append("ambiguity_guessed_or_missed")
    if scored["unsupported"]["recall"] < 1:
        categories.append("unsupported_need_dropped")
    if scored["contexts"]["precision"] < 1:
        categories.append("hallucinated_context")
    return list(dict.fromkeys(categories))


def _group_counts(cases: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        tag = str(case.get("group") or "other")
        counts[tag] = counts.get(tag, 0) + 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 2 intent evaluation")
    parser.add_argument("--llm", action="store_true", help="Force LLM evaluation")
    parser.add_argument("--rule-only", action="store_true")
    parser.add_argument(
        "--out",
        default="",
        help="Optional JSON output path",
    )
    args = parser.parse_args()
    include_llm = False if args.rule_only else (True if args.llm else None)
    report = asyncio.run(run_benchmark(include_llm=include_llm))
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        dest = Path(args.out)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text)


if __name__ == "__main__":
    main()
