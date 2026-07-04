.PHONY: install lint test backtest live flatten infra-up infra-down

install:
	pip install -e ".[dev]"

lint:
	ruff check nautilus_trade tests scripts
	mypy nautilus_trade

test:
	python3 -m pytest tests/ -v --cov=nautilus_trade --cov-report=term-missing

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
