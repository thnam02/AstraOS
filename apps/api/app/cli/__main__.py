"""python -m app.cli reset-demo | demo hero"""

from __future__ import annotations

import sys


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in {"reset-demo", "reset"}:
        from app.cli.reset_demo import main as reset_main

        reset_main()
        return
    if args[0] == "demo":
        sys.argv = [sys.argv[0], *args[1:]]
        from app.cli.demo import main as demo_main

        demo_main()
        return
    raise SystemExit(
        "Usage: python -m app.cli reset-demo | python -m app.cli demo hero"
    )


if __name__ == "__main__":
    main()
