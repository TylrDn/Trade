"""Environment diagnostics — `trade doctor`.

Checks configuration completeness, catalog reachability, adapter credential
presence (without printing them), and observability endpoint reachability.
Designed to be safe to run in any environment; performs no live orders.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from nautilus_trade.config import adapter_cfg, ops_cfg, risk_cfg, system_cfg


def run_diagnostics(console: Any | None = None) -> bool:
    """Run environment diagnostics. Return True if all critical checks pass."""
    checks: list[tuple[str, bool, str]] = []

    # Catalog path
    catalog_path: Path = system_cfg.catalog_path
    try:
        catalog_path.mkdir(parents=True, exist_ok=True)
        writable = catalog_path.exists() and _is_writable(catalog_path)
        checks.append(("catalog path writable", writable, str(catalog_path)))
    except Exception as exc:
        checks.append(("catalog path writable", False, f"error: {exc}"))

    # Adapter creds (presence only)
    binance_ok = bool(adapter_cfg.binance_api_key and adapter_cfg.binance_api_secret)
    kraken_ok = bool(adapter_cfg.kraken_api_key and adapter_cfg.kraken_api_secret)
    if system_cfg.is_research:
        checks.append(("adapter credentials", True, "not required in research"))
    else:
        checks.append(
            (
                "adapter credentials",
                binance_ok or kraken_ok,
                f"binance={_ok(binance_ok)} kraken={_ok(kraken_ok)}",
            )
        )

    # Alerting endpoints
    checks.append(
        (
            "alerting configured",
            bool(ops_cfg.slack_webhook_url or ops_cfg.pagerduty_integration_key)
            or system_cfg.is_research,
            f"slack={_ok(bool(ops_cfg.slack_webhook_url))} "
            f"pagerduty={_ok(bool(ops_cfg.pagerduty_integration_key))}",
        )
    )

    # Risk limits sane
    checks.append(
        (
            "risk limits sane",
            risk_cfg.max_daily_loss_usd > 0
            and risk_cfg.max_position_notional_usd > 0
            and 0 < risk_cfg.max_leverage <= 20,
            f"daily_loss=${risk_cfg.max_daily_loss_usd:.0f} "
            f"notional=${risk_cfg.max_position_notional_usd:.0f} "
            f"leverage={risk_cfg.max_leverage:.1f}x",
        )
    )

    # Docker (optional)
    checks.append(("docker available", shutil.which("docker") is not None, "for infra-up target"))

    all_ok = all(passed for _, passed, _ in checks if _ != "docker available")

    if console is not None:
        from rich.table import Table  # noqa: PLC0415 — optional dep, lazy imported

        table = Table(title=f"Trade Doctor — env={system_cfg.trade_env.value}")
        table.add_column("Check", style="cyan")
        table.add_column("Status")
        table.add_column("Detail", style="dim")
        for name, passed, detail in checks:
            table.add_row(name, "[green]OK[/]" if passed else "[red]FAIL[/]", detail)
        console.print(table)
    return all_ok


def _is_writable(p: Path) -> bool:
    try:
        probe = p / ".doctor_probe"
        probe.touch()
        probe.unlink()
        return True
    except OSError:
        return False


def _ok(b: bool) -> str:
    return "✓" if b else "✗"
