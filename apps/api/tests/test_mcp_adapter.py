"""MCP adapter is a thin REST client. No merchant logic."""

from pathlib import Path

from app.agent import mcp_server
from app.agent.mcp_server import TOOLS


def test_mcp_tools_are_compact() -> None:
    names = {item["name"] for item in TOOLS}
    assert names == {
        "astraos_capabilities",
        "astraos_request_offer",
        "astraos_inspect_offer",
        "astraos_counter_offer",
        "astraos_accept_offer",
        "astraos_get_order",
        "astraos_get_transaction",
    }


def test_mcp_module_has_no_pricing_logic() -> None:
    text = Path(mcp_server.__file__).read_text(encoding="utf-8")
    lowered = text.lower()
    assert "pareto" not in lowered
    assert "cogs" not in lowered
    assert "minimum_margin" not in lowered
