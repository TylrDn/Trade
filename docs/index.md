# nautilus-trade

Production NautilusTrader trading system: research → deterministic backtest
→ paper/staging → live execution, with full observability, layered risk
controls, and operational tooling.

- **[Architecture](ARCHITECTURE.md)** — layers, package layout, order lifecycle.
- **[Runbook](RUNBOOK.md)** — daily ops, alerts, emergency procedures.
- **[Promotion](PROMOTION.md)** — the gate-driven path from research to live.
- **[Security](../SECURITY.md)** — vulnerability reporting, secret handling.
- **[Contributing](../CONTRIBUTING.md)** — local dev, standards, review bar.

## Quick start

```bash
git clone https://github.com/TylrDn/Trade.git
cd Trade
make install-dev
cp .env.example .env
trade doctor
trade backtest --strategy ema_cross --tag first-run
```
