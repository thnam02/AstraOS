"""Deterministic bundle relevance. Never invents a physical SKU."""

from app.decision.intent.models import ShoppingIntent

# MVP ontology: context/outcome label → merchant bundle codes.
BUNDLE_RELEVANCE: dict[str, frozenset[str]] = {
    "long_haul_travel": frozenset(
        {"TRAVEL_ADAPTER", "AIRPLANE_ADAPTER", "HARD_CASE"}
    ),
    "short_travel": frozenset({"TRAVEL_ADAPTER", "HARD_CASE"}),
    "frequent_travel": frozenset(
        {"TRAVEL_ADAPTER", "AIRPLANE_ADAPTER", "HARD_CASE"}
    ),
    "portable_travel": frozenset({"HARD_CASE"}),
    "easy_storage": frozenset({"HARD_CASE"}),
    "travel_convenience": frozenset(
        {"TRAVEL_ADAPTER", "AIRPLANE_ADAPTER", "HARD_CASE"}
    ),
    "gaming": frozenset({"MICROPHONE_ACCESSORY"}),
    "studio": frozenset({"CABLE_ADAPTER"}),
}

NONE_BUNDLE = "NONE"


def intent_labels(intent: ShoppingIntent) -> list[str]:
    labels = [item.label.value for item in intent.context_items]
    labels.extend(item.label.value for item in intent.desired_outcomes)
    labels.extend(tag for tag in intent.context_tags if tag not in labels)
    return labels


def relevant_bundle_codes(intent: ShoppingIntent) -> set[str]:
    codes: set[str] = set()
    triggers: list[str] = []
    for label in intent_labels(intent):
        mapped = BUNDLE_RELEVANCE.get(label)
        if mapped:
            codes.update(mapped)
            triggers.append(label)
    _ = triggers
    return codes


def trigger_labels_for(code: str, intent: ShoppingIntent) -> list[str]:
    hits: list[str] = []
    for label in intent_labels(intent):
        mapped = BUNDLE_RELEVANCE.get(label, frozenset())
        if code in mapped and label not in hits:
            hits.append(label)
    return hits


def bundle_is_context_relevant(code: str, intent: ShoppingIntent) -> bool:
    if code == NONE_BUNDLE or code is None:
        return True
    return code in relevant_bundle_codes(intent)
