"""Real HTTP loopback: Buyer Agent package → public /agent/* only."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
import uvicorn
from buyer_agent.client import AstraOSAgentClient
from buyer_agent.config import BuyerAgentSettings
from buyer_agent.missions import get_mission
from buyer_agent.proposal import contains_private_keys
from buyer_agent.runner import BuyerAgentRunner

from app.main import app

pytestmark = pytest.mark.buyer_agent_network


def _free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start_server() -> tuple[uvicorn.Server, str]:
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)

    def _run() -> None:
        server.run()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        if server.started:
            try:
                httpx.get(f"{url}/health", timeout=0.2)
                break
            except httpx.HTTPError:
                pass
        time.sleep(0.05)
    return server, url


@pytest.fixture(scope="module")
def agent_base() -> str:
    server, url = _start_server()
    yield url
    server.should_exit = True


def test_real_http_request_inspect_counter_accept(agent_base: str) -> None:
    settings = BuyerAgentSettings(astraos_agent_base_url=agent_base)
    with AstraOSAgentClient(settings) as client:
        caps = client.capabilities()
        assert caps["protocol_name"] == "astraos-agent"
        assert "request_offer" in caps["operations"]
        offered = client.request_offer(
            "I need wireless ANC headphones under A$350 delivered today "
            "for a long flight. Comfort matters more than the cheapest option."
        )
        assert contains_private_keys(offered) == []
        assert offered["proposal"]
        proposal_id = offered["proposal"]["proposal_id"]
        session_id = offered["negotiation_session_id"]
        inspected = client.inspect_offer(proposal_id)
        assert inspected["proposal"]["proposal_id"] == proposal_id
        countered = client.counter_offer(
            session_id,
            message="Can you get the total a bit lower while keeping same-day?",
            constraints={"max_total_price_cents": 32000},
        )
        assert countered["proposal"]
        delivery = countered["proposal"].get("delivery") or {}
        assert delivery.get("days") == 0 or delivery.get("days") is None
        accepted = client.accept_offer(
            countered["negotiation_session_id"],
            countered["proposal"]["proposal_id"],
            f"e2e-{uuid4()}",
        )
        assert accepted["status"] in {"CONFIRMED", "REVALIDATION_FAILED"}
        if accepted["status"] == "CONFIRMED":
            order = client.get_order(accepted["order"]["order_number"])
            assert order["order_number"].startswith("AST-")
            client.get_transaction(str(accepted["transaction_id"]))


def test_runner_hero_deterministic_http(agent_base: str) -> None:
    settings = BuyerAgentSettings(
        astraos_agent_base_url=agent_base,
        buyer_agent_mode="deterministic",
    )
    runner = BuyerAgentRunner(settings)
    try:
        result = runner.run(get_mission("urgent-traveller"), persist=False)
    finally:
        runner.close()
    assert result.end_state in {
        "ACCEPTED",
        "REJECTED",
        "NO_SAFE_OFFER",
        "MAX_TURNS",
        "TRANSACTION_FAILED",
    }
    assert result.session_id or result.end_state == "NO_SAFE_OFFER"


def test_multi_persona_http(agent_base: str) -> None:
    settings = BuyerAgentSettings(
        astraos_agent_base_url=agent_base,
        buyer_agent_mode="deterministic",
    )
    runner = BuyerAgentRunner(settings)
    ends: list[str] = []
    try:
        for scenario in (
            "urgent-traveller",
            "budget-buyer",
            "assurance-buyer",
            "quality-buyer",
            "balanced",
        ):
            result = runner.run(get_mission(scenario), persist=False)
            ends.append(result.end_state)
            assert result.end_state != "ERROR"
    finally:
        runner.close()
    assert len(set(ends)) >= 1


def test_buyer_agent_package_is_separate() -> None:
    root = Path(__file__).resolve().parents[2] / "buyer-agent" / "buyer_agent"
    assert root.is_dir()
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
    assert "app.services" not in text
    assert "app.decision" not in text
    assert "AgentGatewayService" not in text
