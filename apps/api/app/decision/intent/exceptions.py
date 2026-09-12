"""Intent parsing errors."""


class IntentParseError(ValueError):
    """Raised when a parser cannot produce a valid ShoppingIntent."""


class LLMParserUnavailable(IntentParseError):
    """Raised when LLM mode is requested but no client/credentials exist."""


class UnsupportedIntentFieldError(IntentParseError):
    """Raised when an LLM invents a field or operator outside the allow-list."""
