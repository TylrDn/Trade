"""Importable factories for live runtime dependency injection.

These functions are referenced by ImportableStrategyConfig / ImportableActorConfig
and read the bound LiveRuntime during node.build().
"""

from __future__ import annotations

from nautilus_trade.actors.feed_health import FeedHealthGuard, FeedHealthGuardConfig
from nautilus_trade.adapters.venue_snapshot import create_venue_snapshot_provider
from nautilus_trade.live.actors.fill_tracker import FillTrackerActor, FillTrackerConfig
from nautilus_trade.live.actors.reconciliation import (
    ReconciliationActor,
    ReconciliationActorConfig,
)
from nautilus_trade.live.flatten import FlattenConfig, FlattenOnStartStrategy
from nautilus_trade.live.runtime import get_live_runtime
from nautilus_trade.strategies.ema_cross import EmaCrossConfig, EmaCrossStrategy


def create_ema_cross_strategy(config: EmaCrossConfig) -> EmaCrossStrategy:
    runtime = get_live_runtime()
    strategy = EmaCrossStrategy(config, gateway=runtime.gateway)
    strategy.bind_execution_gateway(
        runtime.gateway,
        event_store=runtime.event_store,
        order_timing_tracker=runtime.order_timing,
    )
    return strategy


def create_feed_health_guard(config: FeedHealthGuardConfig) -> FeedHealthGuard:
    runtime = get_live_runtime()
    return FeedHealthGuard(
        config,
        breaker=runtime.breaker,
        trip_fn=runtime.record_breaker_trip,
    )


def create_fill_tracker(config: FillTrackerConfig) -> FillTrackerActor:
    runtime = get_live_runtime()
    return FillTrackerActor(config, runtime=runtime)


def create_reconciliation_actor(config: ReconciliationActorConfig) -> ReconciliationActor:
    runtime = get_live_runtime()
    venue_provider = create_venue_snapshot_provider(config.venue)
    return ReconciliationActor(config, runtime=runtime, venue_provider=venue_provider)


def create_flatten_strategy(config: FlattenConfig) -> FlattenOnStartStrategy:
    runtime = get_live_runtime()
    return FlattenOnStartStrategy(config, runtime=runtime)
