"""Prometheus metrics for the trading system.

All metrics are defined here as module-level constants so they are
registered once and importable anywhere without double-registration.

Metrics are scraped by Prometheus and visualized in Grafana.
"""

from __future__ import annotations

import logging
import threading
import time

from prometheus_client import Counter, Gauge, start_http_server

from nautilus_trade.config import ops_cfg, risk_cfg

log = logging.getLogger(__name__)
_metrics_start_monotonic: float | None = None

# ── Order flow ────────────────────────────────────────────────────────────────
# trade_orders_submitted_total counts gateway pre-flight approvals, not venue acks.
# Fill latency (submit → fill) is not wired yet; requires submit timestamp tracking.
ORDER_SUBMITTED = Counter(
    "trade_orders_submitted_total",
    "Total orders approved by ExecutionGateway pre-flight",
    ["strategy"],
)

ORDER_BLOCKED = Counter(
    "trade_orders_blocked_total",
    "Total orders blocked by risk or circuit breaker",
    ["reason", "strategy"],
)

# ── Risk ──────────────────────────────────────────────────────────────────────
DAILY_PNL_USD = Gauge(
    "trade_daily_pnl_usd",
    "Realized daily P&L in USD",
)

PORTFOLIO_NOTIONAL_USD = Gauge(
    "trade_portfolio_notional_usd",
    "Strict complete open position notional in USD; not updated when incomplete",
)

PORTFOLIO_NOTIONAL_INCOMPLETE = Gauge(
    "trade_portfolio_notional_incomplete",
    "1 when strict portfolio notional cannot be computed due to missing MID prices",
)

MAX_DAILY_LOSS_USD = Gauge(
    "trade_risk_max_daily_loss_usd",
    "Configured max daily loss limit in USD (from RISK_MAX_DAILY_LOSS_USD)",
)

DAILY_LOSS_WARNING_USD = Gauge(
    "trade_risk_daily_loss_warning_usd",
    "Daily loss warning threshold in USD (80% of max daily loss limit)",
)

CIRCUIT_TRIPS = Counter(
    "trade_circuit_trips_total",
    "Total circuit breaker trip events",
    ["reason"],
)

PORTFOLIO_HALTED = Gauge(
    "trade_portfolio_halted",
    "1 when portfolio risk engine has halted trading, else 0",
)

PNL_TRACKING_DEGRADED = Counter(
    "trade_pnl_tracking_degraded_total",
    "Fill events where realized PnL could not be resolved from position state",
)

# ── Feed health ───────────────────────────────────────────────────────────────
FEED_STALE = Counter(
    "trade_feed_stale_total",
    "Total stale feed episodes detected (one increment per episode, not per poll)",
    ["instrument"],
)

# ── System ────────────────────────────────────────────────────────────────────
SYSTEM_UPTIME = Gauge(
    "trade_system_uptime_seconds",
    "Process uptime in seconds since metrics server start",
)


def refresh_system_uptime() -> None:
    """Update the system uptime gauge from monotonic clock."""
    if _metrics_start_monotonic is None:
        return
    SYSTEM_UPTIME.set(time.monotonic() - _metrics_start_monotonic)


def _uptime_refresh_loop(interval_seconds: float = 60.0) -> None:
    while True:
        refresh_system_uptime()
        time.sleep(interval_seconds)


def start_metrics_server() -> None:
    """Start the Prometheus HTTP metrics endpoint."""
    global _metrics_start_monotonic
    _metrics_start_monotonic = time.monotonic()
    refresh_system_uptime()
    MAX_DAILY_LOSS_USD.set(risk_cfg.max_daily_loss_usd)
    DAILY_LOSS_WARNING_USD.set(risk_cfg.max_daily_loss_usd * 0.8)
    start_http_server(ops_cfg.prometheus_port)
    threading.Thread(
        target=_uptime_refresh_loop,
        name="metrics-uptime",
        daemon=True,
    ).start()
