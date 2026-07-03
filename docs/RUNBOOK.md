# Operations Runbook

## Daily start-of-day

1. `trade doctor` — verify env, creds, catalog, risk limits.
2. Check Grafana dashboard for overnight incidents.
3. Verify Alertmanager silences are cleared.
4. Confirm feeds are healthy (no `trade_feed_stale_total` growth in last hour).

## Starting live / paper

```bash
# Paper (default)
TRADE_ENV=staging trade live --venue BINANCE --strategy ema_cross

# Production — requires all promotion gates passed
TRADE_ENV=production trade live --venue BINANCE --strategy ema_cross
```

Confirm within 60s of start:

- `trade_system_uptime_seconds` metric is incrementing.
- Reconciliation ran and passed (log: `Reconciliation passed`).
- No `trade_orders_blocked_total{reason="circuit_open"}` on startup.

## Common alerts

### `trade_circuit_trips_total` increased

1. Check the log around the trip time — `CIRCUIT BREAKER TRIPPED: <reason>`.
2. If **stale feed**: check venue status page and network. Wait for feeds
   to recover, then `trade doctor` and manually reset (see below).
3. If **daily loss limit**: review fills in the event store JSONL. Do **not**
   auto-resume — require operator review of the strategy P&L.

### `trade_feed_stale_total` increased

1. Verify network to venue.
2. Check WebSocket connectivity in NautilusTrader logs.
3. If persistent, halt manually and consult venue status.

### Reconciliation failure

1. Halt is automatic. Do not resume.
2. Compare internal state (from event store) with venue's REST endpoints
   directly to determine ground truth.
3. Manually adjust internal state or flatten and restart.

## Emergency flatten

```bash
trade flatten --env production   # requires typing 'FLATTEN' to confirm
trade flatten --env staging --force
```

Fills market orders to close every open position. Use when circuit trips
require positions be closed before human review.

## Resuming after a halt

Only after operator review:

```python
from nautilus_trade.risk.engine import PortfolioRiskEngine
engine = ...  # the running engine
engine.resume(operator="tdean")
```

This clears both `_halted` and the circuit breaker, and emits an
`INFO` alert to Slack recording the resume.

## Rotating credentials

1. Generate new venue key with `read + trade` scopes only (no withdrawal).
2. Update secrets manager.
3. Deploy `.env` change to the live host.
4. Restart the trade service.
5. Verify a full order + fill + reconciliation cycle on testnet before
   pointing at production.

## Deployment

```bash
# Build the image
make docker-build

# Run infra stack
make infra-up

# Run the trade service with paper trading
docker compose up -d trade
```

## Post-incident

1. Zip `./logs/events/*.jsonl` + Prometheus snapshot for the incident window.
2. Fill an incident doc: what tripped, what was open, when did it recover.
3. Add a regression test to `tests/unit/` or `tests/integration/` if the
   failure mode was not previously covered.
