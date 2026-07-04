# Testnet smoke evidence

Manual operational proof from [docs/testnet_smoke.md](../../docs/testnet_smoke.md). **Not CI.**

## Purpose

Store dated evidence that staging testnet smoke was run (or honestly marked BLOCKED when credentials are unavailable).

## Naming convention

After a successful smoke run, copy [`evidence.template.md`](evidence.template.md) to:

```
evidence_YYYY-MM-DD_<run_id>.md
```

Use the `run_id` from live node logs (`LiveRuntime created: run_id=...`).

## Current status

- [`evidence_BLOCKED.md`](evidence_BLOCKED.md) — default placeholder when no testnet credentials were available at commit time
- Add new `evidence_*.md` files here after each manual smoke; do not overwrite BLOCKED unless replacing with real evidence

## Promotion

Staging→production promotion (`scripts/promote_strategy.py`) may reference the latest evidence file in this directory alongside the promotion manifest under `runs/promotions/` (gitignored).
