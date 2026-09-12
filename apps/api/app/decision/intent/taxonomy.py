"""Canonical Stage 3 intent labels. Parsers must not invent new ones."""

from enum import StrEnum


class ContextLabel(StrEnum):
    LONG_HAUL_TRAVEL = "long_haul_travel"
    SHORT_TRAVEL = "short_travel"
    COMMUTING = "commuting"
    OFFICE = "office"
    GAMING = "gaming"
    STUDIO = "studio"
    SPORTS = "sports"
    FREQUENT_TRAVEL = "frequent_travel"
    EXTENDED_CONTINUOUS_USE = "extended_continuous_use"


class OutcomeLabel(StrEnum):
    LOW_FATIGUE = "low_fatigue"
    STRONG_NOISE_ISOLATION = "strong_noise_isolation"
    LONG_BATTERY_ENDURANCE = "long_battery_endurance"
    RELIABLE_EXTENDED_USE = "reliable_extended_use"
    PORTABLE_TRAVEL = "portable_travel"
    CLEAR_CALLS = "clear_calls"
    IMMERSIVE_AUDIO = "immersive_audio"
    EASY_STORAGE = "easy_storage"
    WEATHER_RESILIENCE = "weather_resilience"
    TRAVEL_CONVENIENCE = "travel_convenience"


class ValueField(StrEnum):
    DURABILITY = "durability"
    REPAIRABILITY = "repairability"
    SUSTAINABILITY = "sustainability"


class TradeoffDimension(StrEnum):
    COMFORT = "comfort"
    RELIABILITY = "reliability"
    PRICE = "price"
    BATTERY = "battery"
    WEIGHT = "weight"
    TRAVEL = "travel"
    DELIVERY = "delivery"
    WARRANTY = "warranty"


CANONICAL_CONTEXTS = {item.value for item in ContextLabel}
CANONICAL_OUTCOMES = {item.value for item in OutcomeLabel}
CANONICAL_VALUES = {item.value for item in ValueField}
CANONICAL_TRADEOFFS = {item.value for item in TradeoffDimension}
