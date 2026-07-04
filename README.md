# Trade — Production NautilusTrader System

A fully layered, production-grade algorithmic trading system built on [NautilusTrader](https://nautilustrader.io). Covers research → deterministic backtest → paper/staging → live execution, with observability, risk controls, and ops tooling.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OPS PLANE (external)                     │
│  Prometheus · Grafana · Alertmanager · PagerDuty            │
└─────────────────────┬───────────────────────────────────────┘
                      │ metrics / logs / alerts
┌─────────────────────▼───────────────────────────────────────┐
│                SAFETY ENVELOPE (LiveRuntime)                │
│  CircuitBreaker · PortfolioRiskEngine · ExecutionGateway    │
│  FeedHealthGuard · RegimeFilterActor · ReconciliationActor  │
└─────────────────────┬───────────────────────────────────────┘
                      │ validated order intents
┌─────────────────────▼───────────────────────────────────────┐
│             NAUTILUSTRADER CORE RUNTIME                     │
│  MessageBus · Cache · Clock · Portfolio · Accounting        │
│  Strategies · Actors · OrderManagementSystem                │
└──────┬──────────────────────────────────┬───────────────────┘
       │ venue adapters                    │ data adapters
┌──────▼──────────┐              ┌─────────▼──────────────────┐
│ EXECUTION GW    │              │ DATA LAYER                  │
│ Binance/Kraken  │              │ Parquet Catalog             │
└──────┬──────────┘              └────────────────────────────┘
       │
┌──────▼──────────┐
│ LIVE VENUE APIS  │
│ REST + WebSocket │
└─────────────────┘
```

Live launch composes a shared [`LiveRuntime`](nautilus_trade/live/runtime.py) that wires one `CircuitBreaker`, `PortfolioRiskEngine`, `ExecutionGateway`, reconciler, and JSONL `EventStore`. Strategies receive the gateway via importable factories during `TradingNode.build()`.

---

## Environments

| Environment | Node | Credentials | Purpose |
|---|---|---|---|
| `research` | `BacktestNode` | None | Strategy development, parameter sweeps, report generation |
| `staging` | `TradingNode` (paper) | Sandbox only | Reconciliation tests, recovery tests, operational validation |
| `production` | `TradingNode` (live) | Vault-managed | Live execution, hard risk gates, emergency flatten |

---

## Repository Layout

```
nautilus_trade/
  config.py            # Typed configs for all environments
  catalog.py           # Parquet data catalog management
  strategies/          # Strategy family modules
  actors/              # Market regime and feed-health actors
  portfolio/           # Portfolio stats and PnL helpers (venue-neutral)
  execution/           # Execution gateway
  adapters/            # Venue adapter configs and reconciliation snapshots
  backtest/            # BacktestNode runner and reports
  live/                # LiveRuntime, TradingNode builder, live actors
  ops/                 # Metrics, alerts, event store, circuit breaker
scripts/               # Operational runbooks as scripts
tests/                 # Unit and integration-gated tests
infra/                 # Prometheus, Grafana, Docker configs
.github/workflows/     # CI pipeline
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -e ".[dev]"

# 2. Copy env template
cp .env.example .env
# Fill in your API keys, secrets, etc.

# 3. Run backtest (requires populated catalog — see scripts/run_backtest.py)
python3 scripts/run_backtest.py
python3 scripts/run_backtest.py --list

# 4. Promote strategy to staging (interactive checklist)
python3 scripts/promote_strategy.py --strategy ema_cross --from research --to staging

# 5. Run live with safety envelope (staging first)
TRADE_ENV=staging python3 scripts/run_live.py

# Emergency: flatten all positions (bypasses gateway; uses dedicated flatten node)
python3 scripts/flatten_all.py --env staging
python3 scripts/flatten_all.py --env production
```

---

## Non-Negotiable Controls

1. **Two-layer risk** — strategy-local limits plus portfolio-global pre-flight via `ExecutionGateway` (advisory at application layer; see Safety boundaries)
2. **Reconciliation loop** — startup and periodic balance/position checks against Binance REST (Binance-only today)
3. **Feed-health guardrails** — stale bar data trips the shared circuit breaker
4. **Circuit breakers** — daily loss, per-position notional, portfolio notional, leverage, open orders, reconciliation mismatch, stale feed, missing venue credentials
5. **Audit trail** — safety events written to `./logs/events/events_<run_id>.jsonl`
6. **Promotion gates** — interactive checklist via `scripts/promote_strategy.py` (manual attestation, not automated verification)

---

## Safety boundaries (honest)

| Control | Enforcement level | Notes |
|---|---|---|
| `ExecutionGateway` | Advisory pre-flight | Strategies must call `BaseStrategy.submit_order_guarded()`. Direct `submit_order()`, emergency flatten, and optional `flatten_on_stop` bypass the gateway. OMS-level blocking is future work. |
| Daily P&L / halt | Application layer | Derived from Nautilus `position.realized_pnl` deltas (USDT-settled scope). Unavailable position state records zero delta and logs a warning. |
| Reconciliation | Fail-closed in staging/production | Missing credentials or fetch errors trip the breaker. Balance/position compare only when venue snapshot status is `ok`. |
| Emergency flatten | Intentional bypass | Market orders; waits for flat or timeout; documented slippage risk. |
| Normal shutdown | Positions preserved by default | `EmaCrossConfig.flatten_on_stop` defaults to `false`. |

---

## Testing

```bash
python3 -m pytest tests/ -v
```

In minimal environments without `nautilus_trader` / `prometheus_client`, heavy-dependency tests skip cleanly via `pytest.importorskip`. CI installs full dependencies and runs the complete suite.

---

## Planned / not yet implemented

- KillSwitch module (README previously listed it; use circuit breaker + flatten for now)
- Historical data loader under `nautilus_trade/data/`
- Logfire integration (`LOGFIRE_TOKEN` in `.env.example` is reserved)

---

## License

MIT
