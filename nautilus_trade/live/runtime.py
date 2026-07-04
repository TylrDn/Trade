"""Live runtime composition root.

Creates and holds the shared safety envelope components used by all
live strategies and actors in a single TradingNode process.

Importable factories read the bound runtime only during ``node.build()``.
Constructed strategies and actors must capture references at ``__init__``.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass

from nautilus_trade.execution.gateway import ExecutionGateway
from nautilus_trade.live.reconciler import LiveReconciler
from nautilus_trade.ops.circuit_breaker import CircuitBreaker
from nautilus_trade.ops.event_store import EventStore
from nautilus_trade.risk.engine import PortfolioRiskEngine

log = logging.getLogger(__name__)

_RUNTIME: LiveRuntime | None = None


@dataclass
class LiveRuntime:
    """Shared live safety envelope for one TradingNode process."""

    run_id: str
    breaker: CircuitBreaker
    risk_engine: PortfolioRiskEngine
    gateway: ExecutionGateway
    reconciler: LiveReconciler
    event_store: EventStore

    def record_breaker_trip(self, reason: str) -> None:
        """Trip the circuit breaker and persist an audit event."""
        self.breaker.trip(reason)
        self.event_store.record(
            "circuit_breaker_tripped",
            {"reason": reason},
        )

    def close(self) -> None:
        """Release runtime resources."""
        self.event_store.close()


def create_live_runtime(run_id: str) -> LiveRuntime:
    """Construct a fresh live runtime with one shared circuit breaker."""
    breaker = CircuitBreaker()
    event_store = EventStore(run_id=run_id)

    def record_breaker_trip(reason: str) -> None:
        breaker.trip(reason)
        event_store.record("circuit_breaker_tripped", {"reason": reason})

    risk_engine = PortfolioRiskEngine(breaker=breaker, trip_fn=record_breaker_trip)
    gateway = ExecutionGateway(risk_engine=risk_engine, breaker=breaker)
    reconciler = LiveReconciler(breaker=breaker, trip_fn=record_breaker_trip)
    log.info("LiveRuntime created: run_id=%s", run_id)
    return LiveRuntime(
        run_id=run_id,
        breaker=breaker,
        risk_engine=risk_engine,
        gateway=gateway,
        reconciler=reconciler,
        event_store=event_store,
    )


def bind_live_runtime(runtime: LiveRuntime) -> None:
    """Bind runtime for importable factory functions during node.build()."""
    global _RUNTIME
    if _RUNTIME is not None:
        raise RuntimeError("Live runtime is already bound")
    _RUNTIME = runtime


def get_live_runtime() -> LiveRuntime:
    """Return the bound live runtime."""
    if _RUNTIME is None:
        raise RuntimeError("Live runtime is not bound")
    return _RUNTIME


def unbind_live_runtime() -> None:
    """Clear the bound live runtime."""
    global _RUNTIME
    _RUNTIME = None


@contextmanager
def bound_live_runtime(runtime: LiveRuntime) -> Generator[LiveRuntime, None, None]:
    """Bind runtime for the duration of the context; always unbinds on exit.

    Use in tests and other short-lived scopes. Live scripts bind before
    ``node.build()`` and unbind only after ``node.run()`` completes.
    """
    bind_live_runtime(runtime)
    try:
        yield runtime
    finally:
        unbind_live_runtime()
