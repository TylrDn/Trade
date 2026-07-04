# Manual Testnet Smoke Checklist

This is **not CI**. Use it for operational validation before promotion gates (`scripts/promote_strategy.py` staging→production).

## Where to store evidence

Commit evidence under [`runs/testnet_smoke/`](../runs/testnet_smoke/):

1. Copy [`runs/testnet_smoke/evidence.template.md`](../runs/testnet_smoke/evidence.template.md) to `runs/testnet_smoke/evidence_YYYY-MM-DD_<run_id>.md`
2. Fill in log excerpts, EventStore lines, and metric snapshots from the run
3. If credentials are unavailable, leave [`evidence_BLOCKED.md`](../runs/testnet_smoke/evidence_BLOCKED.md) as the honest placeholder — do not fabricate PASS results

See [`runs/testnet_smoke/README.md`](../runs/testnet_smoke/README.md) for naming conventions.

## Prerequisites

- Binance testnet API keys in `.env`
- `BINANCE_TESTNET=true`
- `TRADE_ENV=staging`
- Dependencies installed: `pip install -e ".[dev]"`

## 1. Start the live node

```bash
TRADE_ENV=staging python3 scripts/run_live.py
```

Confirm in logs:

- `LiveRuntime created: run_id=...`
- `FeedHealthGuard started` with stale and startup grace values
- `FillTrackerActor subscribed to fills`
- `ReconciliationActor started`
- Prometheus metrics server on configured port (default 8000)

EventStore path: `./logs/events/events_<run_id>.jsonl`

## 2. Verify composition

Cross-check against automated smoke test [`tests/test_live_node.py`](../tests/test_live_node.py):

- One shared gateway/breaker across strategy and actors
- Four actors: regime filter, feed health, fill tracker, reconciliation
- EmaCross strategy factory injects shared gateway

Optional factory check:

```bash
python3 -m pytest tests/test_live_wiring.py tests/test_live_node.py -v
```

## 3. Verify reconciliation

With valid testnet credentials:

- Wait for startup reconciliation timer (default 15s)
- Inspect EventStore for `reconciliation_startup_timing` — records elapsed seconds from actor start to first startup reconciliation attempt (compare to configured `startup_delay_seconds`)
- Inspect EventStore for reconciliation pass or explicit failure type:
  - `reconciliation_failed` — true mismatch
  - `reconciliation_mapping_warning` — instrument mapping issue
  - `reconciliation_missing_credentials` / `reconciliation_fetch_failed`

Without credentials (negative test):

- Expect fail-closed trip in staging with `reconciliation_missing_credentials`

## 4. Controlled halt: stale feed or startup timeout

**Stale feed (after first bar):** stop or block market data briefly longer than `RISK_STALE_FEED_SECONDS`.

**Startup timeout (no bars):** restart node with wrong `bar_type` or disconnected data client; wait past `RISK_FEED_STARTUP_GRACE_SECONDS` (default 60s).

Expect:

- Breaker tripped
- `circuit_breaker_tripped` in EventStore with reason `stale_feed:...` or `feed_startup_timeout:...`
- `trade_feed_stale_total` increment in metrics

## 5. Emergency flatten

In a separate session (or after halt):

```bash
TRADE_ENV=staging python3 scripts/flatten_all.py --env staging
```

Expect EventStore events:

- `flatten_started`
- `flatten_pending` (if positions submitted)
- `flatten_complete`

Flatten intentionally bypasses the gateway.

## 6. Recovery

After manual review:

- Halt must be cleared via operator action (not automatic)
- In production, `resume()` / `reset_breaker()` require explicit operator ID
- Document operator name and reason in promotion manifest

## 7. Promotion attestation

Record results in promotion manifest via:

```bash
python3 scripts/promote_strategy.py --strategy ema_cross --from staging --to production --operator <name>
```

Gates reference (from promote script):

- Paper node ran ≥ 7 days without reconciliation failures
- Emergency flatten tested in staging
- Circuit breakers verified tripping correctly
- Feed-failure recovery tested
- Ops alerts verified firing correctly

## Explicitly out of scope

- Automated testnet CI (deferred — secrets, flake, market hours)
- OMS-level order blocking
- Multi-currency PnL validation
