"""Legacy entrypoint — delegates to `trade flatten`.

Prefer:  trade flatten --env production
"""

from __future__ import annotations

import sys

from nautilus_trade.cli.main import app


def main() -> None:
    sys.argv = ["trade", "flatten", *sys.argv[1:]]
    app()


if __name__ == "__main__":
    main()
