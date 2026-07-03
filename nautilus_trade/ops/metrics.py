"""Prometheus metrics for the trading system.

All metrics are defined here as module-level constants so they are
registered once and importable anywhere without double-registration.

Metrics are scraped by Prometheus and visualized in Grafana.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, start_http_server

from nautilus_trade.config import ops_cfg

# ── Order flow ────────────────────────────────────────────────────────────────
ORDER_SUBMITTED = Counter(
    "trade_orders_submitted_total",
    "Total orders approved and submitted",
    ["strategy"],
)

ORDER_BLOCKED = Counter(
    "trade_orders_blocked_total",
    "Total orders blocked by risk or circuit breaker",
    ["reason", "strategy"],
)

ORDER_FILL_LATENCY = Histogram(
    "trade_order_fill_latency_seconds",
    "Time from order submission to fill confirmation",
    ["venue"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ── Risk ──────────────────────────────────────────────────────────────────────
DAILY_PNL_USD = Gauge(
    "trade_daily_pnl_usd",
    "Realized daily P&L in USD",
)

PORTFOLIO_NOTIONAL_USD = Gauge(
    "trade_portfolio_notional_usd",
    "Total open position notional in USD",
)

CIRCUIT_TRIPS = Counter(
    "trade_circuit_trips_total",
    "Total circuit breaker trip events",
    ["reason"],
)

# ── Feed health ───────────────────────────────────────────────────────────────
FEED_STALE = Counter(
    "trade_feed_stale_total",
    "Total stale feed detection events",
    ["instrument"],
)

# ── System ────────────────────────────────────────────────────────────────────
SYSTEM_UPTIME = Gauge(
    "trade_system_uptime_seconds",
    "System uptime in seconds",
)


def start_metrics_server() -> None:
    """Start the Prometheus HTTP metrics endpoint."""
    start_http_server(ops_cfg.prometheus_port)
