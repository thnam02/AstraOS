"""Product semantic documents contain only merchant-supported facts."""

from app.decision.retrieval.documents import build_product_document, document_hash
from tests.qualification_fixtures import snapshot


def test_document_is_deterministic() -> None:
    variant = snapshot(name="Aurora Travel Pro")
    first = build_product_document(variant)
    second = build_product_document(variant)
    assert first.text == second.text
    assert first.version == second.version


def test_missing_attributes_are_omitted() -> None:
    variant = snapshot(attributes={"wireless": True})
    document = build_product_document(variant)
    names = {fact.name for fact in document.facts}
    assert "anc" not in names
    assert "battery_hours" not in names
    assert "wireless" in names
    assert "38-hour" not in document.text


def test_document_does_not_invent_luxury() -> None:
    variant = snapshot()
    document = build_product_document(variant)
    assert "luxur" not in document.text.lower()


def test_same_day_fact_from_fulfilment() -> None:
    document = build_product_document(snapshot())
    assert any(fact.name == "same_day_eligible" for fact in document.facts)


def test_document_hash_is_stable() -> None:
    document = build_product_document(snapshot(name="Sonic Cabin 32"))
    assert document_hash(document) == document_hash(document.text)
    changed = build_product_document(
        snapshot(
            name="Sonic Cabin 32",
            attributes={"wireless": True, "battery_hours": 10},
        )
    )
    assert document_hash(document) != document_hash(changed)
