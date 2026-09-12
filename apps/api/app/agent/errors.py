"""Machine-readable agent-protocol errors. No commercial decisions."""

from enum import StrEnum


class AgentErrorCode(StrEnum):
    INVALID_INTENT = "INVALID_INTENT"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    NO_ELIGIBLE_PRODUCT = "NO_ELIGIBLE_PRODUCT"
    NO_POLICY_SAFE_OFFER = "NO_POLICY_SAFE_OFFER"
    PROPOSAL_EXPIRED = "PROPOSAL_EXPIRED"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    NEGOTIATION_LIMIT_REACHED = "NEGOTIATION_LIMIT_REACHED"
    TRANSACTION_REVALIDATION_FAILED = "TRANSACTION_REVALIDATION_FAILED"
    INVALID_SESSION_STATE = "INVALID_SESSION_STATE"
    PROPOSAL_NOT_FOUND = "PROPOSAL_NOT_FOUND"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    CONSTRAINT_DISCREPANCY = "CONSTRAINT_DISCREPANCY"
    UNSUPPORTED_INSTRUCTION = "UNSUPPORTED_INSTRUCTION"


class AgentProtocolError(Exception):
    """Protocol/state error. Commercial declines use a normal response status."""

    def __init__(
        self,
        code: AgentErrorCode,
        machine_message: str,
        *,
        human_debug_message: str | None = None,
        allowed_next_actions: list[str] | None = None,
        http_status: int = 400,
    ) -> None:
        super().__init__(machine_message)
        self.code = code
        self.machine_message = machine_message
        self.human_debug_message = human_debug_message
        self.allowed_next_actions = allowed_next_actions or ["REQUEST"]
        self.http_status = http_status

    def as_dict(self) -> dict[str, object]:
        retryable = self.http_status >= 500
        return {
            "error_code": self.code.value,
            "machine_message": self.machine_message,
            "human_debug_message": self.human_debug_message,
            "allowed_next_actions": self.allowed_next_actions,
            "retryable": retryable,
        }
