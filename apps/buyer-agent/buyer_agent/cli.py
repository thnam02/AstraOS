"""CLI for the independent Buyer Agent."""

from __future__ import annotations

import argparse
import json
import sys

from buyer_agent.config import load_settings
from buyer_agent.missions import get_mission
from buyer_agent.models import BuyerMode
from buyer_agent.runner import BuyerAgentRunner


def _print_run(result: object) -> None:
    from buyer_agent.models import BuyerRunResult

    assert isinstance(result, BuyerRunResult)
    print("BUYER → ASTRAOS")
    print("REQUEST_OFFER")
    print(result.mission.request)
    print()
    print("ASTRAOS → BUYER")
    print(result.end_state)
    if result.final_product:
        total = (
            f"A${result.final_total_cents / 100:.2f}"
            if result.final_total_cents is not None
            else ""
        )
        print(f"{result.final_product}  {total}".strip())
    print()
    print("Actions:", " → ".join(result.actions) or "—")
    if result.order_ref:
        print()
        print("ORDER CONFIRMED")
        print(result.order_ref)
    print()
    print(f"mode={result.buyer_mode} turns={result.turns} run={result.run_id}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="External AstraOS Buyer Agent")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run one buyer mission")
    run.add_argument("--scenario", default="urgent-traveller")
    run.add_argument("--mode", choices=["deterministic", "llm"], default=None)
    run.add_argument("--json", action="store_true")
    ev = sub.add_parser("eval", help="Run the frozen mission set")
    ev.add_argument("--mode", choices=["deterministic", "llm"], default="deterministic")
    ev.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    settings = load_settings()
    runner = BuyerAgentRunner(settings)
    try:
        if args.command == "run":
            mode: BuyerMode | None = args.mode
            result = runner.run(get_mission(args.scenario), mode=mode)
            if args.json:
                print(result.model_dump_json(indent=2))
            else:
                _print_run(result)
            return 0 if result.end_state != "ERROR" else 2
        from buyer_agent.eval import run_eval

        report = run_eval(runner, mode=args.mode)
        text = json.dumps(report, indent=2)
        print(text)
        if args.out:
            from pathlib import Path

            path = Path(args.out)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text + "\n")
        return 0
    finally:
        runner.close()


if __name__ == "__main__":
    sys.exit(main())
