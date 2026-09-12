"""Collect Phase 1 baseline metrics. Does not change commercial behaviour."""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

HERO = (
    "I'm flying from Sydney to Singapore tomorrow and need wireless "
    "noise-cancelling headphones under A$350. I need them delivered today. "
    "I'll wear them for hours, so comfort and reliability matter more than "
    "getting the absolute cheapest option."
)
COUNTER = "Can you get this below A$315?"


def _req(method: str, url: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    request = Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=120) as response:
            raw = response.read().decode()
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        detail = exc.read().decode()
        raise RuntimeError(f"{method} {url} -> {exc.code}: {detail}") from exc


def _timings(payload: dict) -> dict[str, float]:
    match = payload.get("match") or {}
    construction = payload.get("construction") or {}
    optimisation = payload.get("optimisation") or {}
    match_t = match.get("timing") or {}
    cons_t = construction.get("timing") or {}
    opt_t = optimisation.get("timing") or {}
    nego_t = payload.get("timing") or {}
    return {
        "intent_ms": float(match_t.get("intent_parse_ms") or 0),
        "qualification_ms": float(match_t.get("qualification_ms") or 0),
        "semantic_match_ms": float(
            (match_t.get("embedding_ms") or 0) + (match_t.get("rerank_ms") or 0)
        ),
        "offer_construction_ms": float(cons_t.get("total_ms") or 0),
        "optimisation_ms": float(opt_t.get("total_optimisation_ms") or 0),
        "negotiation_turn_ms": float(nego_t.get("total_turn_ms") or 0),
        "total_decision_ms": float(match_t.get("total_ms") or 0)
        + float(cons_t.get("total_ms") or 0)
        + float(opt_t.get("total_optimisation_ms") or 0),
    }


def _summarize(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {"n": 0, "median": 0, "p95": 0}
    p95_index = min(len(ordered) - 1, max(0, round(0.95 * (len(ordered) - 1))))
    return {
        "n": len(ordered),
        "median": round(statistics.median(ordered), 2),
        "p95": round(ordered[p95_index], 2),
    }


def run_hero_create(base: str) -> dict:
    return _req(
        "POST",
        f"{base}/api/v1/negotiations",
        {
            "intent": HERO,
            "parser_mode": "rule_based",
            "buyer_profile": "INTENT_ADAPTED",
            "max_products": 8,
        },
    )


def snapshot_hero(payload: dict) -> dict:
    intent = (payload.get("match") or {}).get("intent") or {}
    qual = (payload.get("match") or {}).get("qualification") or {}
    matches = ((payload.get("match") or {}).get("semantic_matching") or {}).get(
        "matches"
    ) or []
    construction = payload.get("construction") or {}
    optimisation = payload.get("optimisation") or {}
    rec = optimisation.get("recommended_offer") or (payload.get("proposal") or {}).get(
        "offer"
    )
    return {
        "parser_mode": intent.get("parser_type") or intent.get("parser_mode"),
        "parser_version": intent.get("parser_version"),
        "hard_constraints": [
            {
                "field": item.get("field"),
                "operator": item.get("operator"),
                "value": item.get("normalized_value", item.get("value")),
            }
            for item in intent.get("hard_constraints") or []
        ],
        "preferences": [
            {"field": item.get("field"), "importance": item.get("importance")}
            for item in intent.get("soft_preferences") or []
        ],
        "context": [item.get("label") for item in intent.get("context_items") or []],
        "desired_outcomes": [
            item.get("label") for item in intent.get("desired_outcomes") or []
        ],
        "tradeoffs": [
            {
                "preferred": item.get("preferred_dimension"),
                "over": item.get("over_dimension"),
            }
            for item in intent.get("tradeoffs") or []
        ],
        "qualification": {
            "variants_checked": qual.get("variants_checked"),
            "eligible": qual.get("eligible"),
            "violated": qual.get("violated"),
            "uncertain": qual.get("uncertain"),
        },
        "top_matches": [
            {
                "rank": item.get("rank"),
                "product_name": item.get("product_name"),
                "sku": item.get("sku"),
                "overall_semantic_fit": item.get("overall_semantic_fit"),
                "product_fit": item.get("product_fit"),
                "context_fit": item.get("context_fit"),
                "preference_fit": item.get("preference_fit"),
                "evidence_coverage": item.get("evidence_coverage"),
            }
            for item in matches[:5]
        ],
        "construction_summary": construction.get("summary"),
        "construction_input": construction.get("input"),
        "optimisation_summary": optimisation.get("summary"),
        "recommended_offer": {
            "offer_id": rec.get("offer_id") if rec else None,
            "product_name": rec.get("product_name") if rec else None,
            "sku": rec.get("sku") if rec else None,
            "total_price_cents": (rec.get("pricing") or {}).get("total_price_cents")
            if rec
            else None,
            "delivery": (rec.get("delivery") or {}).get("code") if rec else None,
            "warranty_months": (rec.get("warranty") or {}).get("months") if rec else None,
            "bundle": (rec.get("bundle") or {}).get("code") if rec else None,
            "buyer_utility": rec.get("buyer_utility") if rec else None,
            "contribution_margin_cents": rec.get("contribution_margin_cents")
            if rec
            else None,
            "incremental_intervention_cost_cents": rec.get(
                "incremental_intervention_cost_cents"
            )
            if rec
            else None,
            "is_pareto_efficient": rec.get("is_pareto_efficient") if rec else None,
            "product_fit": rec.get("product_fit") if rec else None,
        }
        if rec
        else None,
        "buyer_model": optimisation.get("buyer_model"),
        "session_id": payload.get("session_id"),
        "proposal_id": (payload.get("proposal") or {}).get("proposal_id"),
        "state": payload.get("state"),
    }


def agent_smoke(base: str) -> dict:
    caps = _req("GET", f"{base}/api/v1/agent/capabilities")
    offered = _req(
        "POST",
        f"{base}/api/v1/agent/offers/request",
        {"natural_language_intent": HERO, "buyer_profile": "INTENT_ADAPTED"},
    )
    proposal_id = (offered.get("proposal") or {}).get("proposal_id")
    session_id = offered.get("negotiation_session_id")
    inspected = _req("GET", f"{base}/api/v1/agent/offers/{proposal_id}")
    countered = _req(
        "POST",
        f"{base}/api/v1/agent/offers/counter",
        {"session_id": session_id, "message": COUNTER},
    )
    counter_id = (countered.get("proposal") or {}).get("proposal_id")
    accepted = _req(
        "POST",
        f"{base}/api/v1/agent/offers/accept",
        {
            "session_id": countered.get("negotiation_session_id") or session_id,
            "proposal_id": counter_id,
            "idempotency_key": f"baseline-{uuid.uuid4()}",
        },
    )
    order_ref = (accepted.get("order") or {}).get("order_number") or (
        accepted.get("order") or {}
    ).get("order_id")
    txn_id = accepted.get("transaction_id")
    order = {}
    txn = {}
    if order_ref:
        try:
            order = _req("GET", f"{base}/api/v1/agent/orders/{order_ref}")
        except RuntimeError as exc:
            order = {"error": str(exc)}
    if txn_id:
        try:
            txn = _req("GET", f"{base}/api/v1/agent/transactions/{txn_id}")
        except RuntimeError as exc:
            txn = {"error": str(exc)}
    return {
        "capabilities_ok": bool(caps),
        "request_status": offered.get("status"),
        "inspect_status": inspected.get("status"),
        "counter_status": countered.get("status"),
        "accept_status": accepted.get("status"),
        "order_number": order_ref,
        "transaction_id": txn_id,
        "order_lookup_ok": "error" not in order,
        "transaction_lookup_ok": "error" not in txn or not txn_id,
        "failure_codes": accepted.get("failure_codes"),
    }


def main() -> None:
    base = os.environ.get("ASTRAOS_BASELINE_API_URL", "http://127.0.0.1:8001")
    repeats = int(os.environ.get("BASELINE_HERO_REPEATS", "10"))
    health = _req("GET", f"{base}/health")
    ready = _req("GET", f"{base}/ready")
    print("health", health.get("status"), flush=True)
    print("ready", ready.get("status"), ready.get("degraded_mode"), flush=True)

    print("warmup", flush=True)
    run_hero_create(base)

    samples: list[dict[str, float]] = []
    last = None
    for index in range(repeats):
        started = time.perf_counter()
        last = run_hero_create(base)
        wall = (time.perf_counter() - started) * 1000
        row = _timings(last)
        row["wall_ms"] = round(wall, 2)
        samples.append(row)
        print(f"hero {index + 1}/{repeats} wall={wall:.1f}ms", flush=True)

    hero = snapshot_hero(last or {})
    if last and last.get("session_id") and (last.get("proposal") or {}).get("proposal_id"):
        countered = _req(
            "POST",
            f"{base}/api/v1/negotiations/{last['session_id']}/turns",
            {"message": COUNTER},
        )
        hero["counter"] = {
            "state": countered.get("state"),
            "outcome": (countered.get("proposal") or {}).get("outcome"),
            "reason_codes": (countered.get("proposal") or {}).get("reason_codes"),
            "offer": {
                "product_name": ((countered.get("proposal") or {}).get("offer") or {}).get(
                    "product_name"
                ),
                "total_price_cents": (
                    ((countered.get("proposal") or {}).get("offer") or {}).get("pricing")
                    or {}
                ).get("total_price_cents"),
            },
            "timing": countered.get("timing"),
        }
        accepted = _req(
            "POST",
            f"{base}/api/v1/negotiations/{last['session_id']}/accept",
            {
                "proposal_id": (countered.get("proposal") or last.get("proposal")).get(
                    "proposal_id"
                ),
                "idempotency_key": f"baseline-hero-{uuid.uuid4()}",
            },
        )
        hero["transaction"] = {
            "state": accepted.get("state"),
            "revalidation": accepted.get("revalidation"),
            "reservation": accepted.get("reservation"),
            "order": accepted.get("order"),
            "failure_codes": accepted.get("failure_codes"),
            "timing": accepted.get("timing"),
        }

    print("agent smoke", flush=True)
    smoke = agent_smoke(base)

    latency = {
        key: _summarize([row[key] for row in samples])
        for key in samples[0].keys()
    } if samples else {}

    out = {
        "api": {"health": health, "ready": ready, "base_url": base},
        "hero": hero,
        "latency": latency,
        "agent_smoke": smoke,
        "samples": samples,
    }
    dest = Path(os.environ.get("BASELINE_OUT", "/tmp/astraos_hero_baseline.json"))
    dest.write_text(json.dumps(out, indent=2, default=str))
    print("wrote", dest)


if __name__ == "__main__":
    try:
        main()
    except URLError as exc:
        print("API unreachable:", exc, file=sys.stderr)
        sys.exit(1)
