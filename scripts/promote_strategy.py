"""Legacy entrypoint — delegates to `trade promote`.

Prefer:  trade promote --strategy ema_cross --from research --to staging
"""

from __future__ import annotations

import sys

from nautilus_trade.cli.main import app


def main() -> None:
    sys.argv = ["trade", "promote", *sys.argv[1:]]
    app()


if __name__ == "__main__":
    main()
