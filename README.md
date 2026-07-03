# nautilus-trade

[![CI](https://github.com/TylrDn/Trade/actions/workflows/ci.yml/badge.svg)](https://github.com/TylrDn/Trade/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A fully layered, production-grade algorithmic trading system built on
[NautilusTrader](https://nautilustrader.io). Covers research → deterministic
backtest → paper/staging → live execution, with full observability, risk
controls, and ops tooling.

---

## Layout

```
Trade/
├── src/nautilus_trade/       # Package source (installable)
│   ├── adapters/             # Binance, Kraken adapter factories
│   ├── actors/               # Regime / signal actors
│   ├── backtest/             # BacktestNode runner + reports
│   ├── cli/                  # `trade` Typer CLI
│   ├── data/                 # Historical loader + live feed monitor
│   ├── execution/            # ExecutionGateway (single choke point)
│   ├── live/                 # TradingNode + reconciler
│   ├── ops/                  # Metrics, alerts, event store, doctor, promotion
│   ├── risk/                 # Portfolio risk engine
│   ├── strategies/           # Strategy families
│   ├── catalog.py            # Parquet catalog access
│   ├── config.py             # Typed Pydantic settings
│   ├── config_loader.py      # YAML strategy/venue loaders
│   └── logging.py            # structlog setup
├── configs/                  # Version-controlled runtime configs
│   ├── strategies/           #   per-strategy YAMLs
│   └── venues/               #   per-venue YAMLs
├── docs/                     # Architecture, runbook, ADRs
├── infra/                    # Prometheus, Grafana, Alertmanager
├── scripts/                  # Legacy wrappers (delegate to `trade` CLI)
├── tests/
│   ├── unit/                 # Fast, deterministic
│   └── integration/          # Cross-module smoke tests
└── .github/                  # CI, dependabot, CODEOWNERS, templates
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full picture.

---

## Quick start

```bash
# 1. Clone + install
git clone https://github.com/TylrDn/Trade.git
cd Trade
make install-dev

# 2. Configure
cp .env.example .env      # fill in venue keys, alert webhooks, risk limits

# 3. Verify
trade doctor              # env + creds + risk sanity checks
trade info                # show config

# 4. Backtest
trade backtest --strategy ema_cross --tag first-run

# 5. Promote and paper trade
trade promote --strategy ema_cross --from research --to staging
TRADE_ENV=staging trade live --venue BINANCE --strategy ema_cross

# 6. Emergency stop
trade flatten --env production
```

---

## CLI

Single entrypoint. `trade --help` lists all commands.

| Command           | Purpose                                                      |
| ----------------- | ------------------------------------------------------------ |
| `trade info`      | Show version, env, catalog path, python version              |
| `trade doctor`    | Environment diagnostics: config, creds, catalog, risk limits |
| `trade backtest`  | Run a deterministic backtest via `BacktestNode`              |
| `trade live`      | Run the live `TradingNode` (respects `TRADE_ENV`)            |
| `trade flatten`   | Emergency: market-close every open position                  |
| `trade promote`   | Interactive promotion checklist + manifest                   |

---

## Environments

| Environment  | Node               | Credentials      | Purpose                                       |
| ------------ | ------------------ | ---------------- | --------------------------------------------- |
| `research`   | `BacktestNode`     | None             | Strategy development, sweeps, reports         |
| `staging`    | `TradingNode`      | Sandbox only     | Reconciliation, recovery, ops validation      |
| `production` | `TradingNode`      | Vault-managed    | Live execution, hard risk gates               |

---

## Non-negotiable controls

1. **Two-layer risk** — strategy-local + portfolio-global before any live order.
2. **Reconciliation loop** — orders, fills, balances continuously verified against the venue.
3. **Feed-health guardrails** — stale data, clock drift, crossed books halt trading.
4. **Circuit breakers** — max daily loss, max position, max notional, volatility spike.
5. **Deterministic replay** — every event durably captured, replayable.
6. **Promotion gates** — no strategy reaches live without a tracked manifest passing research + staging.

---

## Development

```bash
make install-dev         # editable install with dev extras
make pre-commit-install  # hooks: ruff, mypy, gitleaks
make lint                # ruff check
make format              # ruff format + auto-fix
make typecheck           # strict mypy
make test                # pytest
make test-cov            # pytest + coverage HTML report
make audit               # pip-audit for CVEs
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full workflow and the
review bar for risk-critical changes.

---

## Docker

```bash
make docker-build        # multi-stage runtime image (non-root, healthcheck)
make infra-up            # Prometheus + Grafana + Alertmanager
docker compose up -d     # trade + infra
```

---

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Runbook](docs/RUNBOOK.md)
- [Promotion process](docs/PROMOTION.md)
- [Security policy](SECURITY.md)
- [ADRs](docs/adr/)

---

## License

[MIT](LICENSE)
