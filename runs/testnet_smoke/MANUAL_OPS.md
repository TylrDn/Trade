# Phase 11 — Manual operator steps (LAST)

These steps require operator credentials and calendar time. They cannot be automated in CI.

## Prerequisites

- Phases 0–10 merged and verified (`python3 scripts/smoke_testnet.py --dry-run`)
- Copy `.env.example` → `.env` with Binance testnet keys
- `TRADE_ENV=staging`, `BINANCE_TESTNET=true`

## 11a — Testnet smoke run

```bash
TRADE_ENV=staging python3 scripts/run_live.py
# In another terminal after startup:
python3 scripts/smoke_testnet.py --events ./logs/events/events_<run_id>.jsonl
```

Copy `runs/testnet_smoke/evidence.template.md` → `runs/testnet_smoke/evidence_YYYY-MM-DD_<run_id>.md` and fill with real excerpts. Commit the evidence file (replaces or supplements `evidence_BLOCKED.md`).

## 11b — Reconciliation delay tuning

Read `reconciliation_startup_timing.elapsed_seconds` from EventStore; set `RECON_STARTUP_DELAY_SECONDS=ceil(elapsed)+2` in `.env` and document in evidence.

## 11c — Seven-day cumulative clean soak

Run staging node; track daily with:

```bash
python3 scripts/soak_status.py --events ./logs/events/events_<run_id>.jsonl
```

Requires **7 consecutive clean UTC days** without recon failure events. See [docs/testnet_smoke.md](../docs/testnet_smoke.md) §7 for failure runbook.

Promote when soak complete:

```bash
python3 scripts/promote_strategy.py --strategy ema_cross --from staging --to production \
  --operator <name> --evidence runs/testnet_smoke/evidence_YYYY-MM-DD_<run_id>.md
```
