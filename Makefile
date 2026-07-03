.PHONY: help install install-dev lint format typecheck test test-fast test-cov \
        audit backtest live flatten promote doctor \
        infra-up infra-down docker-build docker-run \
        docs docs-serve pre-commit-install clean

.DEFAULT_GOAL := help

PYTHON ?= python
PIP    ?= pip

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Install ──────────────────────────────────────────────────────────────────
install: ## Install runtime deps only
	$(PIP) install -e .

install-dev: ## Install runtime + dev deps
	$(PIP) install -e ".[dev]"

pre-commit-install: install-dev ## Install pre-commit hooks
	pre-commit install --install-hooks

# ── Quality ──────────────────────────────────────────────────────────────────
lint: ## Run ruff linter
	ruff check src tests scripts

format: ## Format code with ruff
	ruff format src tests scripts
	ruff check --fix src tests scripts

typecheck: ## Run mypy in strict mode
	mypy

test: ## Run all tests
	pytest

test-fast: ## Run only unit tests (no integration, no slow)
	pytest -m "not integration and not slow"

test-cov: ## Run tests with coverage report
	pytest --cov=src/nautilus_trade --cov-report=term-missing --cov-report=html

audit: ## Run dependency vulnerability audit
	pip-audit --strict

# ── Runtime ──────────────────────────────────────────────────────────────────
doctor: ## Verify environment configuration
	trade doctor

backtest: ## Run reference backtest
	trade backtest --strategy ema_cross

live: ## Run live TradingNode (respects TRADE_ENV)
	trade live --venue BINANCE --strategy ema_cross

flatten: ## Emergency flatten (production)
	trade flatten --env production

promote: ## Promote strategy (interactive)
	trade promote --strategy ema_cross --from research --to staging

# ── Infra ────────────────────────────────────────────────────────────────────
infra-up: ## Start Prometheus + Grafana + Alertmanager
	docker compose up -d prometheus grafana alertmanager

infra-down: ## Stop observability stack
	docker compose down

docker-build: ## Build the trade runtime image
	docker build -t nautilus-trade:local .

docker-run: ## Run the trade image (env=research)
	docker run --rm -it --env-file .env nautilus-trade:local trade info

# ── Docs ─────────────────────────────────────────────────────────────────────
docs: ## Build mkdocs site into ./site
	mkdocs build

docs-serve: ## Serve docs locally on :8001
	mkdocs serve -a localhost:8001

# ── Housekeeping ─────────────────────────────────────────────────────────────
clean: ## Remove build artifacts and caches
	rm -rf build dist *.egg-info htmlcov .coverage .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
