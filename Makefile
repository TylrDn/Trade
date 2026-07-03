.PHONY: install lint test backtest live flatten infra-up infra-down

install:
	pip install -e ".[dev]"

lint:
	ruff check nautilus_trade tests scripts
	mypy nautilus_trade

test:
	pytest tests/ -v --cov=nautilus_trade --cov-report=term-missing

backtest:
	python scripts/run_backtest.py

live:
	python scripts/run_live.py

flatten:
	python scripts/flatten_all.py --env production

infra-up:
	docker compose up -d prometheus grafana

infra-down:
	docker compose down

promote:
	python scripts/promote_strategy.py
