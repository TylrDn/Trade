"""Logging setup tests."""

import sys
from unittest.mock import MagicMock

from nautilus_trade.ops import logging_setup
from nautilus_trade.ops.logging_setup import configure_observability


class TestLoggingSetup:
    def test_no_op_without_token(self, monkeypatch) -> None:
        monkeypatch.setattr(logging_setup.ops_cfg, "logfire_token", "")
        configure_observability()

    def test_never_raises_on_logfire_failure(self, monkeypatch) -> None:
        monkeypatch.setattr(logging_setup.ops_cfg, "logfire_token", "token")
        fake = MagicMock()
        fake.configure.side_effect = RuntimeError("network down")
        monkeypatch.setitem(sys.modules, "logfire", fake)
        configure_observability()
