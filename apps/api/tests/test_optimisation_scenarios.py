"""Same catalogue, different intent → different merchant response."""

from fastapi.testclient import TestClient

URGENT = (
    "I'm flying tonight and need ANC headphones under A$350 delivered today. "
    "Comfort matters more than the cheapest price."
)
BUDGET = (
    "I want the cheapest wireless noise-cancelling headphones under A$250. "
    "Standard delivery is fine."
)
ASSURANCE = (
    "I need reliable ANC headphones under A$350 with a long warranty. "
    "I care more about reliability than price."
)


def _recommend(client: TestClient, intent: str, profile: str) -> dict:
    response = client.post(
        "/api/v1/decision/run",
        json={
            "intent": intent,
            "parser_mode": "rule_based",
            "buyer_profile": profile,
            "max_products": 5,
        },
    )
    assert response.status_code == 200
    return response.json()["optimisation"]


def test_different_intents_can_select_different_offers(client: TestClient) -> None:
    urgent = _recommend(client, URGENT, "URGENT_TRAVELLER")
    budget = _recommend(client, BUDGET, "BUDGET_SHOPPER")
    if not urgent["recommended_offer"] or not budget["recommended_offer"]:
        return
    urgent_rec = urgent["recommended_offer"]
    budget_rec = budget["recommended_offer"]
    different = (
        urgent_rec["offer_id"] != budget_rec["offer_id"]
        or urgent_rec["delivery"]["code"] != budget_rec["delivery"]["code"]
        or urgent_rec["pricing"]["product_price_cents"]
        != budget_rec["pricing"]["product_price_cents"]
    )
    assert different
    urgent_w = urgent["buyer_model"]["weights"]
    budget_w = budget["buyer_model"]["weights"]
    assert urgent_w["delivery"] > budget_w["delivery"]
    assert budget_w["price"] > urgent_w["price"]


def test_assurance_weights_warranty(client: TestClient) -> None:
    result = _recommend(client, ASSURANCE, "ASSURANCE_BUYER")
    assert result["buyer_model"]["weights"]["warranty"] >= 0.25
