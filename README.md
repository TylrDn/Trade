# Trade — Staging-Grade NautilusTrader System

A layered algorithmic trading system built on [NautilusTrader](https://nautilustrader.io). Covers research → deterministic backtest → paper/staging → live execution, with observability, risk controls, and ops tooling. The live path is composed and safety-tested, but **not all controls are OMS-enforced** — see Safety boundaries.

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
pip install -e ".[dev,kraken]"

# 2. Copy env template (default TRADE_VENUE=kraken)
cp .env.example .env
# Fill in KRAKEN_FUTURES_DEMO_* or BINANCE_* keys

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
3. **Feed-health guardrails** — stale bar data or startup timeout (no first bar within grace) trips the shared circuit breaker
4. **Circuit breakers** — daily loss, per-position notional, portfolio notional, leverage, open orders, reconciliation mismatch, stale feed, missing venue credentials
5. **Audit trail** — safety events written to `./logs/events/events_<run_id>.jsonl`
6. **Promotion gates** — interactive checklist via `scripts/promote_strategy.py` (manual attestation, not automated verification)

---

## Safety boundaries (honest)

| Control | Enforcement level | Notes |
|---|---|---|
| `ExecutionGateway` | Advisory + OMS block on direct submit | Strategies use `submit_order_guarded()` / `submit_exit_guarded()`. Direct `submit_order()` / `close_position()` blocked in staging/production when gateway wired (no orphaned engine state). Emergency flatten and `flatten_on_stop` bypass documented. |
| Daily P&L / halt | Application layer | Derived from Nautilus `position.realized_pnl` deltas (USDT-settled scope). Unresolved PnL in staging/production halts trading and trips the breaker — it is **not** recorded as zero loss. |
| Feed health | Fail-closed in staging/production | Stale bars trip the breaker. If no first bar arrives within `RISK_FEED_STARTUP_GRACE_SECONDS`, startup timeout trips the breaker. Research allows startup without first bar. |
| Portfolio notional | Fail-closed in staging/production | Gateway blocks new orders when any open position lacks a MID price. `trade_portfolio_notional_incomplete=1` when strict notional is unknown; notional gauge is not updated with partial sums. |
| Reconciliation | Fail-closed in staging/production | Missing credentials or fetch errors trip the breaker. USDT balance compare; cache-validated position mapping with distinct mapping vs mismatch events. |
| Circuit breaker reset | Operator-guarded in production | `reset()` and `resume()` require an explicit operator ID in `TRADE_ENV=production`. |
| Emergency flatten | Intentional bypass | Market orders; waits for flat or timeout; documented slippage risk. |
| Normal shutdown | Positions preserved by default | `EmaCrossConfig.flatten_on_stop` defaults to `false`. |
| Metrics | Honest semantics | `trade_orders_submitted_total` counts gateway approvals. `trade_fill_latency_seconds` records approval-to-fill when submit timestamp known. Alert thresholds use exported gauges set at metrics server start. |

**EmaCross intentional gateway bypasses** (documented, not guarded):

- `gateway=None` at construction — backtest/research path; `on_start` logs that portfolio-level risk checks are bypassed
- `EmaCrossConfig.flatten_on_stop=True` — `on_stop` calls `close_all_positions()` for emergency flatten semantics (same bypass class as `scripts/flatten_all.py`)

---

## Testing

```bash
python3 -m pytest tests/ -v
make test-integration   # LiveRuntime / TradingNode composition smoke tests
make test-staging       # Fail-closed safety tests under TRADE_ENV=staging
python3 scripts/smoke_testnet.py --dry-run  # CI-safe smoke assertion check
python3 scripts/load_catalog.py --symbol BTCUSDT --start 2024-01-01T00:00:00 --end 2024-01-31T00:00:00
```

Manual testnet validation (not CI): see [docs/testnet_smoke.md](docs/testnet_smoke.md). Store evidence in [`runs/testnet_smoke/`](runs/testnet_smoke/) (template + BLOCKED placeholder committed; dated evidence files added after manual runs).

In minimal environments without `nautilus_trader` / `prometheus_client`, heavy-dependency tests skip cleanly via `pytest.importorskip`. CI installs full dependencies and runs the complete suite including `@pytest.mark.integration` tests.

---

## Operational tooling

- **Kill switch:** `python3 scripts/kill_switch.py --reason ... --operator ...` (trips breaker; run flatten separately)
- **Smoke validation:** `python3 scripts/smoke_testnet.py --dry-run` (CI) or `--events ./logs/events/events_<run_id>.jsonl`
- **Soak tracking:** `python3 scripts/soak_status.py --events ./logs/events/events_<run_id>.jsonl`
- **Catalog loader:** `python3 scripts/load_catalog.py` (see `--help` for partial-download resume notes)
- **Logfire:** optional via `LOGFIRE_TOKEN` (never blocks emergency flatten on bootstrap failure)
- **Testnet CI:** `.github/workflows/testnet-smoke.yml` (dry-run on push; live via `workflow_dispatch`)

## Planned / not yet implemented

- Automatic catalog resume cursor (loader v1 writes per-chunk staging only; Kraken history Phase 9)
- Full multi-currency FX desk (v1 converter protocol + USDT default only)

---

## License

MIT
