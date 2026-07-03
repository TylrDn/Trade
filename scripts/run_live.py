"""Legacy entrypoint — delegates to `trade live`.

Prefer:  TRADE_ENV=staging trade live --venue BINANCE --strategy ema_cross
"""

from __future__ import annotations

import sys

from nautilus_trade.cli.main import app


def main() -> None:
    sys.argv = ["trade", "live", *sys.argv[1:]]
    app()


if __name__ == "__main__":
    main()
