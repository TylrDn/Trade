#!/usr/bin/env python3
"""Operator kill switch CLI."""

from __future__ import annotations

import argparse
import logging
import uuid

from nautilus_trade.live.runtime import create_live_runtime
from nautilus_trade.ops.kill_switch import KillSwitch

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Trigger operator kill switch")
    parser.add_argument("--reason", required=True, help="Kill switch reason")
    parser.add_argument("--operator", required=True, help="Operator ID or name")
    args = parser.parse_args()

    runtime = create_live_runtime(f"kill-{uuid.uuid4().hex[:8]}")
    try:
        KillSwitch(runtime).trigger(args.reason, args.operator)
        log.info("Kill switch triggered; run flatten_all.py if positions must be closed")
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
