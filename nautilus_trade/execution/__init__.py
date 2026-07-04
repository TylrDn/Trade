"""Execution gateway — the only path through which live orders are submitted."""

from nautilus_trade.execution.gateway import ExecutionGateway, OrderIntent

__all__ = ["ExecutionGateway", "OrderIntent"]
