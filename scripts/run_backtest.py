"""Legacy entrypoint — delegates to `trade backtest`.

Prefer:  trade backtest --strategy ema_cross --tag my_experiment
"""

from __future__ import annotations

import sys

from nautilus_trade.cli.main import app


def main() -> None:
    sys.argv = ["trade", "backtest", *sys.argv[1:]]
    app()


if __name__ == "__main__":
    main()
