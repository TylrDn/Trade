# Testnet smoke evidence

**Status:** PASS | FAIL | BLOCKED

## Run metadata

| Field | Value |
|-------|-------|
| Date (UTC) | YYYY-MM-DD |
| Operator | |
| run_id | |
| venue | kraken / binance |
| TRADE_ENV | staging |
| KRAKEN_DEMO | true (Kraken) |
| BINANCE_TESTNET | true (Binance) |
| Instrument | PF_XBTUSD.KRAKEN or BTCUSDT-PERP.BINANCE |
| Credential status | ok / missing / invalid |

## 1. Live node startup

- [ ] `LiveRuntime created: run_id=...` in logs
- [ ] `FeedHealthGuard started` (stale + startup grace values logged)
- [ ] `FillTrackerActor subscribed to fills`
- [ ] `ReconciliationActor started`
- [ ] Metrics server listening (default port 8000)

Log excerpt:

```
(paste relevant startup lines)
```

EventStore path: `./logs/events/events_<run_id>.jsonl`

## 2. Composition

- [ ] Shared gateway/breaker across strategy and actors
- [ ] Four actors: regime filter, feed health, fill tracker, reconciliation
- [ ] EmaCross factory injects shared gateway

Optional: `python3 -m pytest tests/test_live_wiring.py tests/test_live_node.py -v` — result:

```
(pass/fail/skip)
```

## 3. Reconciliation

- [ ] Startup reconciliation ran (default delay 15s)
- [ ] EventStore contains `reconciliation_startup_timing` with elapsed vs configured delay
- [ ] Open-order reconciliation checked (`reconciliation_ok` includes `open_orders: PASS`)
- [ ] Outcome event type:

```
reconciliation_ok | reconciliation_failed | reconciliation_mapping_warning |
reconciliation_open_orders_mismatch | reconciliation_missing_credentials | reconciliation_fetch_failed
```

Event excerpt:

```json
(paste reconciliation-related EventStore lines)
```

## 4. Controlled halt (breaker)

Test performed: stale feed | startup timeout | skipped

- [ ] Breaker tripped
- [ ] `circuit_breaker_tripped` in EventStore with expected reason
- [ ] `trade_feed_stale_total` incremented once per episode (not per poll)

## 5. Emergency flatten (optional separate session)

- [ ] `flatten_started` / `flatten_complete` in EventStore
- [ ] Documented as intentional gateway bypass

## 6. Metrics snapshot

At end of smoke (or after halt):

| Metric | Value |
|--------|-------|
| trade_portfolio_notional_usd | |
| trade_portfolio_notional_incomplete | |
| trade_daily_pnl_usd | |
| trade_circuit_breaker_tripped | |

## 7. Operator attestation

I confirm this smoke was executed per [docs/testnet_smoke.md](../../docs/testnet_smoke.md).

- Name:
- Date:
- Notes:
