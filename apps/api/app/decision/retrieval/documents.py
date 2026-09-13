"""Deterministic product semantic documents. Facts only, no invented copy."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from app.decision.eligibility.snapshot import VariantSnapshot

DOCUMENT_VERSION = "product_semantic.v1"


@dataclass(frozen=True)
class DocumentFact:
    name: str
    value: Any
    phrase: str


@dataclass
class ProductSemanticDocument:
    variant_id: str
    sku: str
    product_name: str
    brand: str
    version: str
    facts: list[DocumentFact] = field(default_factory=list)
    text: str = ""


def build_product_document(snapshot: VariantSnapshot) -> ProductSemanticDocument:
    """Build a document from merchant facts. Missing attributes are omitted."""
    facts: list[DocumentFact] = []
    attrs = snapshot.attributes
    wireless = attrs.get("wireless")
    form = "wireless" if wireless is True else "wired" if wireless is False else ""
    category_line = " ".join(part for part in (form, "over-ear headphones") if part)

    def add(name: str, value: Any, phrase: str) -> None:
        if value is None:
            return
        facts.append(DocumentFact(name=name, value=value, phrase=phrase))

    if attrs.get("anc") is True:
        add("anc", True, "active noise cancellation")
    elif attrs.get("anc") is False:
        add("anc", False, "no active noise cancellation")
    battery = attrs.get("battery_hours")
    if battery is not None:
        add("battery_hours", battery, f"{battery}-hour battery")
    weight = attrs.get("weight_g")
    if weight is not None:
        add("weight_g", weight, f"{weight}g")
    if attrs.get("foldable") is True:
        add("foldable", True, "foldable")
    if wireless is True:
        add("wireless", True, "wireless")
    elif wireless is False:
        add("wireless", False, "wired")
    comfort = attrs.get("comfort_score")
    if comfort is not None:
        add("comfort_score", comfort, f"comfort score {comfort}")
    travel = attrs.get("travel_score")
    if travel is not None:
        add("travel_score", travel, f"travel score {travel}")
    if attrs.get("microphone") is True:
        add("microphone", True, "built-in microphone")
    water = attrs.get("water_resistance")
    if water:
        add("water_resistance", water, f"water resistance {water}")
    same_day = any(
        option.available and option.enabled and option.days == 0
        for option in snapshot.deliveries
    )
    if snapshot.deliveries:
        add("same_day_eligible", same_day, "same-day eligible" if same_day else "")
        if not same_day:
            facts[-1] = DocumentFact(
                name="same_day_eligible",
                value=False,
                phrase="no same-day delivery",
            )

    usecase = _derived_usecase(facts)
    lines = [
        f"Product: {snapshot.product_name}",
        f"Brand: {snapshot.brand}",
        f"Category: {category_line or snapshot.category}",
        "Verified facts:",
    ]
    for fact in facts:
        if fact.phrase:
            lines.append(f"- {fact.phrase}")
    if usecase:
        lines.append(f"Use-case representation: {usecase}")
    return ProductSemanticDocument(
        variant_id=str(snapshot.variant_id),
        sku=snapshot.sku,
        product_name=snapshot.product_name,
        brand=snapshot.brand,
        version=DOCUMENT_VERSION,
        facts=facts,
        text="\n".join(lines),
    )


def document_hash(document: ProductSemanticDocument | str) -> str:
    text = document if isinstance(document, str) else document.text
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _derived_usecase(facts: list[DocumentFact]) -> str:
    """Template use-case text from present facts only."""
    names = {fact.name: fact.value for fact in facts}
    parts: list[str] = []
    if names.get("anc") is True:
        parts.append("ANC headphones")
    else:
        parts.append("headphones")
    if names.get("weight_g") is not None and float(names["weight_g"]) <= 250:
        parts.insert(0, "Lightweight")
    clauses: list[str] = []
    if names.get("travel_score") is not None and float(names["travel_score"]) >= 0.7:
        clauses.append("long-duration travel")
    if names.get("comfort_score") is not None and float(names["comfort_score"]) >= 0.7:
        clauses.append("extended wear")
    if names.get("foldable") is True or names.get("wireless") is True:
        clauses.append("portable use")
    if not clauses:
        return ""
    lead = " ".join(parts)
    return f"{lead} suited to {', '.join(clauses)}."
