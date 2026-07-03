# Strategy Promotion

A strategy moves through three environments. No strategy reaches live without
passing every gate for each step.

```
research  ──►  staging  ──►  production
(backtest)     (paper)       (live capital)
```

## Command

```bash
trade promote --strategy ema_cross --from research --to staging --operator tdean
trade promote --strategy ema_cross --from staging  --to production --operator tdean
```

Each answered gate is recorded to `runs/promotions/promo_<id>.json` with a
timestamp and operator ID. Missing gates block the promotion.

## research → staging

- Backtest manifest exists with reproducible output.
- Parameter sensitivity analysis completed.
- Strategy-local risk limits verified in backtest.
- No open TODO/FIXME in strategy module.

## staging → production

- Paper node ran for ≥ 7 days with no reconciliation failures.
- Emergency flatten tested in staging.
- All circuit breakers verified tripping correctly.
- Feed-failure recovery test passed.
- Ops alerts verified firing correctly.
- Position sizing reviewed at target capital level.

## Why gates matter

A strategy that trades well in backtest but has never been reconciled against
a real venue is unsafe. Staging exists to prove the operational path: fills
match, balances match, restarts recover cleanly, and the safety envelope trips
under stress.
