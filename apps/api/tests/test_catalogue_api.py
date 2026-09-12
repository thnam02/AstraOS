"""Catalogue and merchant policy HTTP API."""

from fastapi.testclient import TestClient


def test_product_listing(client: TestClient) -> None:
    response = client.get("/api/v1/catalogue/products", params={"limit": 20})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 100
    assert payload["items"]
    first = payload["items"][0]
    assert "brand" in first
    assert first["variants"]


def test_product_listing_brand_filter(client: TestClient) -> None:
    response = client.get(
        "/api/v1/catalogue/products", params={"brand": "Aurora Audio"}
    )
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["brand"] == "Aurora Audio"


def test_product_detail(client: TestClient) -> None:
    listing = client.get("/api/v1/catalogue/products", params={"limit": 1})
    product_id = listing.json()["items"][0]["id"]
    response = client.get(f"/api/v1/catalogue/products/{product_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["product"]["id"] == product_id
    assert payload["variants"]
    variant = payload["variants"][0]
    assert "inventory" in variant
    assert "delivery_options" in variant
    assert "warranty_options" in variant
    assert "bundle_options" in variant
    assert "return_policies" in variant
    assert "evidence" in variant


def test_variant_detail(client: TestClient) -> None:
    listing = client.get("/api/v1/catalogue/products", params={"limit": 1})
    variant_id = listing.json()["items"][0]["variants"][0]["id"]
    response = client.get(f"/api/v1/catalogue/variants/{variant_id}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == variant_id
    assert payload["base_price_cents"] > 0
    assert isinstance(payload["attributes"], dict)


def test_missing_product_404(client: TestClient) -> None:
    response = client.get(
        "/api/v1/catalogue/products/00000000-0000-4000-8000-000000000099"
    )
    assert response.status_code == 404


def test_catalogue_stats(client: TestClient) -> None:
    response = client.get("/api/v1/catalogue/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["products"] >= 100
    assert payload["variants"] >= 300
    assert payload["brands"] == 12
    assert "headphones" in payload["categories"]
    assert payload["evidence_records"] >= 2500


def test_merchant_policy_get(client: TestClient) -> None:
    response = client.get("/api/v1/merchant/policy")
    assert response.status_code == 200
    payload = response.json()
    assert payload["minimum_margin_rate"] == 0.15
    assert payload["maximum_discount_rate"] == 0.10
    assert payload["delivery_subsidy_enabled"] is True


def test_merchant_policy_patch_persists(client: TestClient) -> None:
    original = client.get("/api/v1/merchant/policy").json()
    response = client.patch(
        "/api/v1/merchant/policy",
        json={"minimum_margin_rate": 0.18, "bundle_enabled": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["minimum_margin_rate"] == 0.18
    assert payload["bundle_enabled"] is False
    restore = client.patch(
        "/api/v1/merchant/policy",
        json={
            "minimum_margin_rate": original["minimum_margin_rate"],
            "bundle_enabled": original["bundle_enabled"],
        },
    )
    assert restore.status_code == 200


def test_merchant_policy_patch_invalid(client: TestClient) -> None:
    response = client.patch(
        "/api/v1/merchant/policy", json={"maximum_discount_rate": 1.5}
    )
    assert response.status_code == 422
