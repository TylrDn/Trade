# Trade — Production NautilusTrader System

A fully layered, production-grade algorithmic trading system built on [NautilusTrader](https://nautilustrader.io). Covers research → deterministic backtest → paper/staging → live execution, with full observability, risk controls, and ops tooling.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OPS PLANE (external)                     │
│  Prometheus · Grafana · Alertmanager · PagerDuty · Logfire  │
└─────────────────────┬───────────────────────────────────────┘
                      │ metrics / logs / alerts
┌─────────────────────▼───────────────────────────────────────┐
│                SAFETY ENVELOPE                              │
│  CircuitBreaker · RiskEngine · FeedHealthGuard · KillSwitch │
└─────────────────────┬───────────────────────────────────────┘
                      │ validated order intents
┌─────────────────────▼───────────────────────────────────────┐
│             NAUTILUSTRADER CORE RUNTIME                     │
│  MessageBus · Cache · Clock · Portfolio · Accounting        │
│  Strategies · Actors · ExecutionAlgorithms                  │
│  OrderManagementSystem · EventStore                         │
└──────┬──────────────────────────────────┬───────────────────┘
       │ venue adapters                    │ data adapters
┌──────▼──────────┐              ┌─────────▼──────────────────┐
│ EXECUTION GW    │              │ DATA LAYER                  │
│ Binance/Kraken  │              │ Parquet Catalog · Feeds     │
│ ExecutionClient │              │ HistoricalLoader · Fallback │
└──────┬──────────┘              └────────────────────────────┘
       │
┌──────▼──────────┐
│ LIVE VENUE APIS  │
│ REST + WebSocket │
└─────────────────┘

RESEARCH PLANE (separate env, no live creds)
  BacktestNode · DataCatalog · ParameterSweeps · PromotionGates
```

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
  actors/              # Market regime, signal, filter actors
  risk/                # Risk engine and circuit breakers
  execution/           # Execution gateway
  adapters/            # Venue adapter configs (Binance, Kraken)
  data/                # Historical loader and live feeds
  backtest/            # BacktestNode runner and reports
  live/                # TradingNode runner and reconciler
  ops/                 # Metrics, alerts, event store
scripts/               # Operational runbooks as scripts
tests/                 # Strategy, risk, and reconciler tests
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

# 3. Load historical data into catalog
python scripts/run_backtest.py --instrument BTC-USDT-PERP --start 2024-01-01 --end 2025-01-01

# 4. Run backtest
python scripts/run_backtest.py --strategy ema_cross --config configs/ema_cross.json

# 5. Promote strategy to staging
python scripts/promote_strategy.py --strategy ema_cross --env staging

# 6. Run live (after staging validation)
python scripts/run_live.py --strategy ema_cross --env production

# Emergency: flatten all positions immediately
python scripts/flatten_all.py --env production
```

---

## Non-Negotiable Controls

1. **Two-layer risk** — strategy-local + portfolio-global before any live order
2. **Reconciliation loop** — orders, fills, balances continuously verified against venue
3. **Feed-health guardrails** — stale data, clock drift, crossed books halt trading
4. **Circuit breakers** — max daily loss, max position, max notional, volatility spike
5. **Deterministic replay** — every event durably captured, replayable
6. **Promotion gates** — no strategy reaches live without tracked manifest passing research + staging

---

## Promotion Gates (required before live)

- [ ] Backtest passes with tracked manifest and reproducible output
- [ ] Strategy survives parameter sensitivity analysis
- [ ] Paper node reconciliation: orders, fills, balances correct after restart
- [ ] Feed-failure recovery test passed
- [ ] All risk limits exercised and confirmed tripping correctly
- [ ] Emergency flatten script tested in staging
- [ ] Ops alerts verified firing correctly

---

## License

MIT
