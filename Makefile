.PHONY: install lint test test-integration test-staging backtest live flatten infra-up infra-down

install:
	pip install -e ".[dev]"

lint:
	ruff check nautilus_trade tests scripts
	mypy nautilus_trade

test:
	python3 -m pytest tests/ -v --cov=nautilus_trade --cov-report=term-missing

test-integration:
	python3 -m pytest tests/ -v -m integration

test-staging:
	TRADE_ENV=staging python3 -m pytest tests/test_risk.py tests/test_fill_tracker_actor.py tests/test_reconciliation_actor.py tests/test_feed_health.py tests/test_exit_guarded.py tests/test_staging_env.py -v

backtest:
	python3 scripts/run_backtest.py

live:
	python3 scripts/run_live.py

flatten:
	python3 scripts/flatten_all.py --env production

infra-up:
	docker compose up -d prometheus grafana alertmanager

infra-down:
	docker compose down

promote:
	python3 scripts/promote_strategy.py --strategy ema_cross --from research --to staging
