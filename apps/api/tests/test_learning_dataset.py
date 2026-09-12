"""Grouped splits and dataset filters."""

from app.decision.learning.dataset import build_dataset, grouped_split


def _row(group: str, selected: bool, price: int) -> dict:
    return {
        "id": f"{group}-{price}",
        "group_id": group,
        "mission_id": group,
        "features": {
            "w_product": 0.3,
            "w_price": 0.2,
            "w_delivery": 0.2,
            "w_warranty": 0.1,
            "w_bundle": 0.1,
            "w_returns": 0.1,
            "comfort_importance": 0.5,
            "reliability_importance": 0.4,
            "warranty_importance": 0.2,
            "price_importance": 0.3,
            "has_long_haul": 0.0,
            "has_commuting": 0.0,
            "has_gaming": 0.0,
            "has_studio": 0.0,
            "product_fit": 0.7,
            "context_fit": 0.4,
            "preference_fit": 0.4,
            "evidence_coverage": 0.5,
            "total_price_cents": float(price),
            "budget_headroom": 0.1,
            "delivery_days": 0.0 if selected else 2.0,
            "is_same_day": 1.0 if selected else 0.0,
            "warranty_months": 12.0,
            "bundle_present": 0.0,
            "return_window_days": 30.0,
            "discount_rate": 0.0,
            "contribution_margin_rate": 0.3,
            "intervention_cost_cents": 0.0,
            "price_x_price_importance": 0.1,
            "delivery_x_delivery_importance": 0.2,
            "warranty_x_warranty_importance": 0.1,
            "fit_x_product_importance": 0.2,
            "buyer_profile": "BALANCED",
            "delivery_code": "SAME_DAY" if selected else "STANDARD",
        },
        "selected": selected,
        "policy_safe": True,
        "hard_constraints_satisfied": True,
        "outcome_source": "SIMULATED_ARENA",
        "buyer_utility": 0.8 if selected else 0.5,
        "total_price_cents": price,
    }


def test_invalid_and_real_rows_are_dropped() -> None:
    rows = [
        _row("m1", True, 20000),
        {
            **_row("m1", False, 21000),
            "policy_safe": False,
        },
        {
            **_row("m2", True, 22000),
            "outcome_source": "FUTURE_REAL_COMMERCE",
        },
        _row("m3", False, 23000),
    ]
    dataset = build_dataset(rows, seed=2026)
    assert dataset.size == 2
    assert set(dataset.groups) == {"m1", "m3"}


def test_same_seed_is_deterministic() -> None:
    rows = [_row(f"m{idx}", idx % 2 == 0, 20000 + idx) for idx in range(12)]
    first = build_dataset(rows, seed=2026)
    second = build_dataset(rows, seed=2026)
    assert first.y.tolist() == second.y.tolist()
    assert first.groups == second.groups
    assert first.X[0] == second.X[0]


def test_grouped_split_has_no_mission_leakage() -> None:
    rows = []
    for idx in range(20):
        rows.append(_row(f"m{idx}", True, 20000 + idx))
        rows.append(_row(f"m{idx}", False, 25000 + idx))
    dataset = build_dataset(rows, seed=2026)
    split = grouped_split(dataset, seed=2026)
    train, val, test = (
        set(split.train.groups),
        set(split.validation.groups),
        set(split.test.groups),
    )
    assert not (train & val)
    assert not (train & test)
    assert not (val & test)
    assert split.train.size + split.validation.size + split.test.size == dataset.size
