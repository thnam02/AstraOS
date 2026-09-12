"""Single-lever counterfactuals from the conceptual baseline."""

from collections.abc import Sequence

from app.decision.optimisation.baseline import lever_family
from app.decision.optimisation.models import CounterfactualRow, ScoredOffer


def _efficiency(delta_utility: float, cost_cents: int) -> float | None:
    if cost_cents > 0:
        return round(delta_utility / (cost_cents / 100.0), 6)
    if delta_utility > 0:
        return None
    return 0.0


def _row(
    *,
    lever: str,
    label: str,
    offer: ScoredOffer,
    baseline: ScoredOffer,
) -> CounterfactualRow:
    delta_u = offer.utility.score - baseline.utility.score
    delta_c = (
        offer.economics.contribution_margin_cents
        - baseline.economics.contribution_margin_cents
    )
    cost = offer.economics.incremental_intervention_cost_cents
    return CounterfactualRow(
        lever=lever,
        label=label,
        offer_id=offer.offer_id,
        policy_safe=offer.policy.policy_safe,
        buyer_utility=offer.utility.score,
        delta_utility=round(delta_u, 6),
        contribution_margin_cents=offer.economics.contribution_margin_cents,
        delta_contribution_cents=delta_c,
        incremental_intervention_cost_cents=cost,
        intervention_efficiency=_efficiency(delta_u, cost),
        total_price_cents=offer.total_customer_price_cents,
        delivery_code=offer.delivery_code,
        warranty_code=offer.warranty_code,
        bundle_code=offer.bundle_code,
        return_policy_code=offer.return_policy_code,
    )


def _label(offer: ScoredOffer, family: str) -> str:
    if family == "price":
        rate = offer.economics.revenue_forgone_vs_list_cents
        return f"-{rate / 100:.0f} price" if rate else "Base price"
    if family == "delivery":
        return offer.delivery_name or offer.delivery_code
    if family == "warranty":
        return f"{offer.warranty_months}-month warranty"
    if family == "bundle":
        return offer.bundle_name or offer.bundle_code or "Bundle"
    if family == "returns":
        return f"{offer.return_window_days or 30}-day returns"
    return family


def build_counterfactuals(
    scored: Sequence[ScoredOffer],
    *,
    variant_id: object,
    baseline: ScoredOffer | None,
) -> list[CounterfactualRow]:
    if baseline is None:
        return []
    rows = [_row(lever="baseline", label="Baseline", offer=baseline, baseline=baseline)]
    seen: set[str] = set()
    for item in scored:
        if item.variant_id != variant_id or item.offer_id == baseline.offer_id:
            continue
        # Need the raw candidate comparison — use codes already on ScoredOffer.
        family = _family_from_scored(item, baseline)
        if family is None:
            continue
        key = (
            f"{family}:{item.delivery_code}:{item.warranty_code}:"
            f"{item.bundle_code}:{item.return_policy_code}:"
            f"{item.product_price_cents}"
        )
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            _row(
                lever=family,
                label=_label(item, family),
                offer=item,
                baseline=baseline,
            )
        )
    rows.sort(key=lambda row: (row.lever != "baseline", row.lever, -row.delta_utility))
    return rows


def _family_from_scored(offer: ScoredOffer, baseline: ScoredOffer) -> str | None:
    class _Shim:
        def __init__(self, item: ScoredOffer) -> None:
            forgone = item.economics.revenue_forgone_vs_list_cents
            self.price_adjustment_type = "BASE" if forgone == 0 else "DISCOUNT"
            self.price_adjustment_rate = item.economics.revenue_forgone_vs_list_cents
            self.delivery_code = item.delivery_code
            self.warranty_code = item.warranty_code
            self.bundle_code = item.bundle_code
            self.return_policy_code = item.return_policy_code

    return lever_family(_Shim(offer), _Shim(baseline))  # type: ignore[arg-type]


def best_single_lever(
    rows: Sequence[CounterfactualRow], family: str
) -> CounterfactualRow | None:
    candidates = [
        item
        for item in rows
        if item.lever == family and item.policy_safe and item.offer_id is not None
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: (item.buyer_utility, item.contribution_margin_cents),
    )
