# Testnet smoke evidence

**Status:** BLOCKED

## Why blocked

No Binance testnet credentials were available in the execution environment at the time this artifact was committed.

Required to unblock:

- Copy `.env.example` to `.env`
- Set valid Binance testnet API keys
- Set `BINANCE_TESTNET=true` and `TRADE_ENV=staging`
- Run the checklist in [docs/testnet_smoke.md](../../docs/testnet_smoke.md)
- Copy [evidence.template.md](evidence.template.md) to `evidence_YYYY-MM-DD_<run_id>.md` with real log and EventStore excerpts

## Run metadata

| Field | Value |
|-------|-------|
| Date (UTC) | (not run) |
| Operator | n/a |
| run_id | n/a |
| TRADE_ENV | staging (expected) |
| BINANCE_TESTNET | true (expected) |
| Credential status | **missing** — no `.env` with keys in repo |

## Checklist

All sections in [evidence.template.md](evidence.template.md) remain unchecked until a manual smoke run completes.

## Next steps

1. `pip install -e ".[dev]"`
2. Configure `.env` with testnet keys
3. `TRADE_ENV=staging python3 scripts/run_live.py`
4. Complete [docs/testnet_smoke.md](../../docs/testnet_smoke.md)
5. Add `evidence_<date>_<run_id>.md` to this directory (keep this BLOCKED file for history or remove after first successful evidence is committed)
