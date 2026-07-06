# Phase 11 — Manual operator steps (LAST)

These steps require operator credentials and calendar time. They cannot be automated in CI.

## Prerequisites

- Phases 0–10 merged and verified (`python3 scripts/smoke_testnet.py --dry-run`)
- `bash scripts/setup_dev.sh` (installs `.[dev,kraken]`)
- Copy `.env.example` → `.env` with **Kraken Futures demo** keys (default) or Binance testnet keys
- Kraken: `TRADE_VENUE=kraken`, `KRAKEN_DEMO=true`, `KRAKEN_FUTURES_DEMO_*`, `RISK_FEED_STARTUP_GRACE_SECONDS=180`
- `TRADE_ENV=staging`

See [PREFLIGHT.md](PREFLIGHT.md) for instrument catalog check (`PF_XBTUSD`).

## 11a — Staging smoke run

```bash
TRADE_ENV=staging python3 scripts/run_live.py
# In another terminal after startup (~20s for reconciliation):
python3 scripts/smoke_testnet.py --events ./logs/events/events_<run_id>.jsonl
```

Copy `runs/testnet_smoke/evidence.template.md` → `runs/testnet_smoke/evidence_YYYY-MM-DD_<run_id>.md` and fill with real excerpts.

## 11b — Reconciliation delay tuning

Read `reconciliation_startup_timing.elapsed_seconds` from EventStore; set `RECON_STARTUP_DELAY_SECONDS=ceil(elapsed)+2` in `.env`.

## 11c — Seven-day cumulative clean soak

```bash
python3 scripts/soak_status.py --events ./logs/events/events_<run_id>.jsonl
```

Promote when `clean_day_streak=7`:

```bash
python3 scripts/promote_strategy.py --strategy ema_cross --from staging --to production \
  --operator <name> --evidence runs/testnet_smoke/evidence_YYYY-MM-DD_<run_id>.md
```
