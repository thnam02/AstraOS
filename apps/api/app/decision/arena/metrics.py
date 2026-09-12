"""Arena metric formulas. Contribution per opportunity is the hero KPI."""

from collections import defaultdict

from app.decision.arena.models import (
    ArenaBenchmarkSummary,
    ArenaMissionResult,
    PairwiseRow,
    SegmentMetrics,
    StrategyMetrics,
)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def compute_strategy_metrics(
    results: list[ArenaMissionResult],
    strategy: str,
) -> StrategyMetrics:
    missions = len(results)
    wins = 0
    win_contrib: list[float] = []
    utilities: list[float] = []
    interventions: list[float] = []
    hard_violations = 0
    policy_violations = 0
    no_offer = 0
    default_utilities: dict[str, float] = {}
    for result in results:
        default = next(
            (
                item
                for item in result.responses
                if item.strategy_name == "DEFAULT" and item.buyer_utility is not None
            ),
            None,
        )
        if default and default.buyer_utility is not None:
            default_utilities[result.mission.id] = default.buyer_utility
        row = next(
            (item for item in result.responses if item.strategy_name == strategy),
            None,
        )
        if row is None:
            no_offer += 1
            continue
        if row.offer_id is None:
            no_offer += 1
        if row.offer_id is not None and not row.hard_constraints_satisfied:
            hard_violations += 1
        if (
            row.offer_id is not None
            and not row.policy_safe
            and row.hard_constraints_satisfied
        ):
            policy_violations += 1
        if row.buyer_utility is not None:
            utilities.append(row.buyer_utility)
        if row.intervention_cost_cents is not None:
            interventions.append(float(row.intervention_cost_cents))
        if (
            not result.selection.no_purchase
            and result.selection.selected_strategy == strategy
        ):
            wins += 1
            if row.merchant_contribution_cents is not None:
                win_contrib.append(float(row.merchant_contribution_cents))
    deltas: list[float] = []
    effs: list[float] = []
    for result in results:
        row = next(
            (item for item in result.responses if item.strategy_name == strategy),
            None,
        )
        if row is None or row.buyer_utility is None:
            continue
        base = default_utilities.get(result.mission.id)
        if base is None:
            continue
        delta = row.buyer_utility - base
        deltas.append(delta)
        cost = float(row.intervention_cost_cents or 0)
        if cost > 0:
            effs.append(delta / (cost / 100.0))
    avg_win = _mean(win_contrib)
    per_opp = (wins / missions) * (avg_win or 0) if missions else 0.0
    return StrategyMetrics(
        strategy_name=strategy,
        missions=missions,
        wins=wins,
        selection_rate=round(wins / missions, 6) if missions else 0.0,
        avg_buyer_utility=_mean(utilities),
        avg_contribution_when_selected=avg_win,
        contribution_per_opportunity_cents=round(per_opp, 4),
        avg_intervention_cost_cents=_mean(interventions),
        hard_constraint_violation_rate=round(hard_violations / missions, 6)
        if missions
        else 0.0,
        policy_violation_rate=round(policy_violations / missions, 6)
        if missions
        else 0.0,
        no_offer_rate=round(no_offer / missions, 6) if missions else 0.0,
        transaction_completion_rate=0.0,
        avg_utility_vs_default=_mean(deltas),
        intervention_efficiency=_mean(effs),
    )


def compute_segments(
    results: list[ArenaMissionResult],
    strategies: list[str],
) -> list[SegmentMetrics]:
    buckets: dict[tuple[str, str, str], list[ArenaMissionResult]] = defaultdict(list)
    for result in results:
        profile = result.mission.buyer_profile
        tags = result.mission.scenario_tags or ["unspecified"]
        for tag in tags:
            for strategy in strategies:
                buckets[(tag, profile, strategy)].append(result)
    rows: list[SegmentMetrics] = []
    for (tag, profile, strategy), group in sorted(buckets.items()):
        wins = sum(
            1
            for item in group
            if not item.selection.no_purchase
            and item.selection.selected_strategy == strategy
        )
        utils: list[float] = []
        contribs: list[float] = []
        for item in group:
            row = next(
                (r for r in item.responses if r.strategy_name == strategy),
                None,
            )
            if row and row.buyer_utility is not None:
                utils.append(row.buyer_utility)
            if (
                row
                and not item.selection.no_purchase
                and item.selection.selected_strategy == strategy
                and row.merchant_contribution_cents is not None
            ):
                contribs.append(float(row.merchant_contribution_cents))
        rows.append(
            SegmentMetrics(
                scenario_tag=tag,
                buyer_profile=profile,
                strategy_name=strategy,
                missions=len(group),
                wins=wins,
                selection_rate=round(wins / len(group), 6) if group else 0.0,
                avg_buyer_utility=_mean(utils),
                avg_contribution_cents=_mean(contribs),
            )
        )
    return rows


def pairwise_matrix(
    results: list[ArenaMissionResult],
    strategies: list[str],
) -> list[PairwiseRow]:
    rows: list[PairwiseRow] = []
    for i, left in enumerate(strategies):
        for right in strategies[i + 1 :]:
            left_wins = 0
            right_wins = 0
            other = 0
            for item in results:
                chosen = item.selection.selected_strategy
                if item.selection.no_purchase or chosen not in {left, right}:
                    other += 1
                elif chosen == left:
                    left_wins += 1
                else:
                    right_wins += 1
            n = len(results) or 1
            rows.append(
                PairwiseRow(
                    left=left,
                    right=right,
                    left_wins=round(left_wins / n, 6),
                    right_wins=round(right_wins / n, 6),
                    no_purchase_or_other=round(other / n, 6),
                )
            )
    return rows


def summarize(
    results: list[ArenaMissionResult],
    *,
    strategies: list[str],
    seed: int,
    config: dict,
    timing: dict[str, float],
) -> ArenaBenchmarkSummary:
    no_purchase = sum(1 for item in results if item.selection.no_purchase)
    n = len(results)
    return ArenaBenchmarkSummary(
        mission_count=n,
        no_purchase_rate=round(no_purchase / n, 6) if n else 0.0,
        seed=seed,
        strategies=strategies,
        strategy_metrics=[
            compute_strategy_metrics(results, name) for name in strategies
        ],
        segment_metrics=compute_segments(results, strategies),
        pairwise=pairwise_matrix(results, strategies),
        timing=timing,
        config=config,
    )
