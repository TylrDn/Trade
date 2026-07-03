"""Smoke tests for the `trade` CLI entrypoint.

These invoke the CLI in-process via typer's Runner. Marked `integration`
because they exercise multiple modules together.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from nautilus_trade.cli.main import app

pytestmark = pytest.mark.integration

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "nautilus-trade" in result.stdout


def test_info_shows_env() -> None:
    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "research" in result.stdout.lower()


def test_doctor_runs_and_reports() -> None:
    result = runner.invoke(app, ["doctor"])
    # Doctor may return non-zero if optional deps are missing; we just
    # want to confirm it produces the diagnostics table.
    assert "Trade Doctor" in result.stdout
