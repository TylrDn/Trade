# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] — 2026-07-03

### Added

- `src/` package layout (installable via `pip install -e .`).
- Unified `trade` CLI (`trade backtest | live | flatten | promote | doctor | info`)
  backed by Typer + Rich.
- YAML runtime configs under `configs/strategies/` and `configs/venues/`.
- `configs`-driven strategy loading (`config_loader.py`).
- Environment diagnostics via `trade doctor` (`ops/doctor.py`).
- Testable promotion runner (`ops/promotion.py`) split from the CLI script.
- Structured logging setup (`nautilus_trade.logging`) via structlog.
- Multi-stage `Dockerfile` (builder + slim runtime, non-root user, healthcheck).
- `docker-compose.yml` now includes the `trade` runtime service.
- Full mkdocs-material documentation scaffold (`docs/`).
- Pre-commit config (ruff, mypy, gitleaks, hygiene hooks).
- Dependabot config (pip / actions / docker weekly cadence).
- CODEOWNERS, PR template, bug + feature issue templates.
- CI matrix (Python 3.11 + 3.12) with lint, typecheck, tests, build, security jobs.
- `py.typed` marker (declares typed package).

### Changed

- Package moved from `nautilus_trade/` to `src/nautilus_trade/`.
- Tests split into `tests/unit/` and `tests/integration/` with a shared
  `conftest.py` that isolates the environment.
- Legacy `scripts/*.py` now delegate to the new CLI (fully backward compatible).
- `pyproject.toml` upgraded: strict ruff ruleset, strict mypy, richer coverage
  config, expanded classifiers, `[project.scripts]` entrypoint.
- `Makefile` rewritten with self-documenting `help` target.

### Security

- `.dockerignore` excludes `.env`, secrets, and runtime artifacts.
- `pre-commit` runs `gitleaks` on every commit.
- CI runs `pip-audit` + `trivy fs` on every push.

## [0.1.0] — 2026-07-03

Initial release: NautilusTrader-based backtest → paper → live pipeline with
layered risk engine, reconciliation, circuit breaker, and Prometheus metrics.
