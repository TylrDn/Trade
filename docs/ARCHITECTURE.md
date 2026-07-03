# Architecture

## Layers

```
┌──────────────────────────────────────────────────────────────┐
│                     OPS PLANE (external)                     │
│  Prometheus · Grafana · Alertmanager · PagerDuty · Logfire   │
└──────────────────────┬───────────────────────────────────────┘
                       │ metrics / logs / alerts
┌──────────────────────▼───────────────────────────────────────┐
│                  SAFETY ENVELOPE                             │
│  CircuitBreaker · PortfolioRiskEngine · FeedHealthMonitor    │
│  ExecutionGateway · KillSwitch                               │
└──────────────────────┬───────────────────────────────────────┘
                       │ validated order intents
┌──────────────────────▼───────────────────────────────────────┐
│              NAUTILUSTRADER CORE RUNTIME                     │
│  MessageBus · Cache · Clock · Portfolio · Accounting         │
│  Strategies · Actors · ExecutionAlgorithms                   │
│  OrderManagementSystem · EventStore                          │
└───────┬──────────────────────────────────┬───────────────────┘
        │ venue adapters                    │ data adapters
┌───────▼──────────┐              ┌─────────▼───────────────────┐
│ EXECUTION GW     │              │ DATA LAYER                  │
│ Binance / Kraken │              │ Parquet Catalog · Feeds     │
│ ExecutionClient  │              │ HistoricalLoader · Fallback │
└───────┬──────────┘              └─────────────────────────────┘
        │
┌───────▼──────────┐
│ LIVE VENUE APIS  │
│ REST + WebSocket │
└──────────────────┘

RESEARCH PLANE (separate env, no live creds)
  BacktestNode · DataCatalog · ParameterSweeps · PromotionGates
```

## Package layout

| Path                                          | Purpose                                                     |
| --------------------------------------------- | ----------------------------------------------------------- |
| `src/nautilus_trade/config.py`                | Typed Pydantic settings for env, risk, adapters, ops        |
| `src/nautilus_trade/config_loader.py`         | Loads strategy / venue YAML configs from `configs/`         |
| `src/nautilus_trade/catalog.py`               | Parquet data catalog access                                 |
| `src/nautilus_trade/logging.py`               | structlog + stdlib configuration                            |
| `src/nautilus_trade/cli/`                     | Typer-based `trade` CLI                                     |
| `src/nautilus_trade/strategies/`              | Strategy families (all inherit from `BaseStrategy`)         |
| `src/nautilus_trade/actors/`                  | Regime / signal / filter actors                             |
| `src/nautilus_trade/risk/engine.py`           | Portfolio-level risk engine with daily P&L tracking         |
| `src/nautilus_trade/execution/gateway.py`     | Single choke point for order intents                        |
| `src/nautilus_trade/adapters/`                | Venue adapter configuration factories                       |
| `src/nautilus_trade/data/loader.py`           | Historical OHLCV → Parquet catalog loader                   |
| `src/nautilus_trade/data/feeds.py`            | Live feed staleness monitor                                 |
| `src/nautilus_trade/backtest/`                | BacktestNode runner + reports                               |
| `src/nautilus_trade/live/`                    | TradingNode runner + reconciliation                         |
| `src/nautilus_trade/ops/metrics.py`           | Prometheus metrics registry                                 |
| `src/nautilus_trade/ops/alerts.py`            | Slack + PagerDuty alert routing                             |
| `src/nautilus_trade/ops/circuit_breaker.py`   | System-wide trading halt gate                               |
| `src/nautilus_trade/ops/event_store.py`       | Append-only JSONL audit trail                               |
| `src/nautilus_trade/ops/doctor.py`            | `trade doctor` diagnostics                                  |
| `src/nautilus_trade/ops/promotion.py`         | Testable promotion gate runner                              |

## Environments

| Env          | Node               | Credentials | Purpose                                       |
| ------------ | ------------------ | ----------- | --------------------------------------------- |
| `research`   | `BacktestNode`     | None        | Strategy development, sweeps, reports         |
| `staging`    | `TradingNode`      | Sandbox     | Reconciliation, recovery, ops validation      |
| `production` | `TradingNode`      | Vault       | Live execution, hard risk gates               |

## Order lifecycle (live)

1. Strategy generates a signal in `on_bar` or `on_quote`.
2. Strategy computes `OrderIntent` and calls `ExecutionGateway.submit(...)`.
3. Gateway checks the circuit breaker.
4. Gateway calls `PortfolioRiskEngine.check_before_order(...)`.
5. If approved, strategy calls `self.submit_order(order)` (NautilusTrader).
6. NautilusTrader's own `RiskEngine` runs its checks (never bypassed in live).
7. Order flows to the venue adapter and out over WebSocket / REST.
8. Fill event returns → strategy updates portfolio → `PortfolioRiskEngine.record_fill()`.
9. Metrics + event store updated on every state transition.

## Two-layer risk

- **Strategy-local:** Configured in the strategy's own `StrategyConfig`
  (e.g. `EmaCrossConfig.max_position_notional_usd`). Blocks bad signals early.
- **Portfolio-global:** `PortfolioRiskEngine` enforces daily loss, aggregate
  notional, leverage, open-order caps. Never bypassed in live.

## Halt paths

Any of these tripping halts the whole system via the CircuitBreaker:

- Daily loss limit hit (`record_fill` in `PortfolioRiskEngine`).
- Stale feed (`FeedHealthMonitor.check_all`).
- Reconciliation failure (`LiveReconciler`).
- Operator manual trip.
- Any unhandled exception on the trading path.

Resume requires an explicit operator call to `PortfolioRiskEngine.resume(...)`
(or `CircuitBreaker.reset()`), which is logged and alerted on.
