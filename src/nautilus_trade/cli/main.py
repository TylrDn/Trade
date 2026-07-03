"""Unified CLI entrypoint — `trade <subcommand>`.

Replaces the loose collection of argparse scripts under `scripts/` with
a single, discoverable, typed CLI. The old scripts still work and now
simply delegate to this module.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from nautilus_trade import __version__
from nautilus_trade.config import system_cfg

app = typer.Typer(
    name="trade",
    help="Production NautilusTrader trading system CLI.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()
log = logging.getLogger(__name__)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"nautilus-trade [bold cyan]{__version__}[/]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable DEBUG logging."),
) -> None:
    """Trade system CLI."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


# ── backtest ─────────────────────────────────────────────────────────────────
@app.command()
def backtest(
    strategy: str = typer.Option("ema_cross", help="Strategy name to run."),
    config_file: Path | None = typer.Option(
        None, "--config", "-c", help="Path to strategy YAML config."
    ),
    tag: str = typer.Option("", help="Optional run label."),
    list_runs: bool = typer.Option(False, "--list", help="List previous backtest runs."),
) -> None:
    """Run a deterministic backtest via BacktestNode."""
    from nautilus_trade.backtest.node import build_backtest_config, run_backtest
    from nautilus_trade.backtest.report import manifests_to_dataframe

    if list_runs:
        df = manifests_to_dataframe()
        if df.empty:
            console.print("[yellow]No backtest manifests found.[/]")
            return
        table = Table(title="Backtest Runs")
        for col in df.columns:
            table.add_column(col)
        for _, row in df.iterrows():
            table.add_row(*[str(v) for v in row])
        console.print(table)
        return

    from nautilus_trade.config_loader import load_strategy_config

    strat_cfg = load_strategy_config(strategy, config_file)
    console.print(f"[cyan]Running backtest[/] strategy=[bold]{strategy}[/] tag={tag or '-'}")

    config = build_backtest_config(
        venue_name=strat_cfg["venue"],
        instrument_id=strat_cfg["instrument_id"],
        bar_type=strat_cfg["bar_type"],
        strategy_path=strat_cfg["strategy_path"],
        strategy_config=strat_cfg["config"],
        start=strat_cfg["start"],
        end=strat_cfg["end"],
        starting_balance=strat_cfg.get("starting_balance", "100000 USDT"),
    )
    manifest = run_backtest(config, tag=tag)
    console.print(f"[green]✓ Run complete[/] run_id=[bold]{manifest['run_id']}[/]")


# ── live ─────────────────────────────────────────────────────────────────────
@app.command()
def live(
    venue: str = typer.Option("BINANCE", help="Venue to trade on."),
    strategy: str = typer.Option("ema_cross", help="Strategy name."),
    config_file: Path | None = typer.Option(None, "--config", "-c"),
) -> None:
    """Run the live TradingNode (respects TRADE_ENV)."""
    from nautilus_trade.config_loader import load_strategy_config
    from nautilus_trade.live.node import build_live_node
    from nautilus_trade.ops.metrics import start_metrics_server

    if system_cfg.is_live:
        console.print(
            "[bold red]⚠  PRODUCTION mode active. Real capital at risk.[/]\n"
            "Ensure all promotion gates have passed."
        )

    start_metrics_server()

    strat_cfg = load_strategy_config(strategy, config_file)

    if venue.upper() == "BINANCE":
        from nautilus_trade.adapters.binance_config import (
            DATA_FACTORY,
            EXEC_FACTORY,
            binance_data_config,
            binance_exec_config,
        )

        data_cfg = binance_data_config()
        exec_cfg = binance_exec_config()
    elif venue.upper() == "KRAKEN":
        from nautilus_trade.adapters.kraken_config import (
            DATA_FACTORY,
            EXEC_FACTORY,
            kraken_data_config,
            kraken_exec_config,
        )

        data_cfg = kraken_data_config()
        exec_cfg = kraken_exec_config()
    else:
        console.print(f"[red]Unknown venue: {venue}[/]")
        raise typer.Exit(code=2)

    node = build_live_node(
        venue=venue.upper(),
        strategy_configs=[
            {"strategy_path": strat_cfg["strategy_path"], "config": strat_cfg["config"]}
        ],
        data_factory=DATA_FACTORY,
        exec_factory=EXEC_FACTORY,
        data_client_config=data_cfg,
        exec_client_config=exec_cfg,
    )

    try:
        node.start()
        node.run()
    except KeyboardInterrupt:
        console.print("[yellow]Shutdown requested[/]")
    finally:
        node.stop()
        node.dispose()
        console.print("[green]Node stopped cleanly[/]")


# ── flatten ──────────────────────────────────────────────────────────────────
@app.command()
def flatten(
    env: str = typer.Option(..., help="Environment: staging | production"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation prompt."),
) -> None:
    """Emergency: flatten all open positions with market orders."""
    if env not in ("staging", "production"):
        console.print("[red]--env must be 'staging' or 'production'[/]")
        raise typer.Exit(code=2)

    if env == "production" and not force:
        confirm = typer.prompt("⚠  PRODUCTION flatten. Type 'FLATTEN' to confirm")
        if confirm != "FLATTEN":
            console.print("[yellow]Flatten cancelled[/]")
            raise typer.Exit()

    console.print(f"[bold red]🚨 FLATTEN ALL initiated: env={env}[/]")
    log.critical("FLATTEN ALL initiated: env=%s", env)
    # Wire to live TradingNode:
    #   for position in node.portfolio.positions_open():
    #       strategy.close_position(position)
    console.print(
        "[dim]Stub: connect to live TradingNode and iterate open positions. "
        "See live/node.py for TradingNode construction.[/]"
    )


# ── promote ──────────────────────────────────────────────────────────────────
@app.command()
def promote(
    strategy: str = typer.Option(..., help="Strategy name to promote."),
    from_env: str = typer.Option(..., "--from"),
    to_env: str = typer.Option(..., "--to"),
    operator: str = typer.Option("", help="Operator ID."),
) -> None:
    """Run pre-promotion checklist and record the promotion manifest."""
    from nautilus_trade.ops.promotion import run_promotion

    ok, out = run_promotion(strategy=strategy, from_env=from_env, to_env=to_env, operator=operator)
    if not ok:
        console.print("[red]Promotion BLOCKED — see logs.[/]")
        raise typer.Exit(code=1)
    console.print(f"[green]✓ Promotion approved.[/] manifest=[bold]{out}[/]")


# ── doctor ───────────────────────────────────────────────────────────────────
@app.command()
def doctor() -> None:
    """Verify environment: config, catalog path, credentials, connectivity."""
    from nautilus_trade.ops.doctor import run_diagnostics

    ok = run_diagnostics(console=console)
    raise typer.Exit(code=0 if ok else 1)


# ── info ─────────────────────────────────────────────────────────────────────
@app.command()
def info() -> None:
    """Show system config, environment, and package versions."""
    table = Table(title="Trade — System Info")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_row("Version", __version__)
    table.add_row("Env", system_cfg.trade_env.value)
    table.add_row("Catalog Path", str(system_cfg.catalog_path))
    table.add_row("Log Level", system_cfg.nautilus_log_level)
    table.add_row("Python", sys.version.split()[0])
    console.print(table)


if __name__ == "__main__":  # pragma: no cover
    app()
