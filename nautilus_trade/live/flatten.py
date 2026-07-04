"""Emergency flatten strategy — closes all open positions on start."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nautilus_trader.config import StrategyConfig

from nautilus_trade.strategies.base import BaseStrategy

if TYPE_CHECKING:
    from nautilus_trade.live.runtime import LiveRuntime

log = logging.getLogger(__name__)

_FLATTEN_WAIT_TIMER = "flatten_wait"
_FLATTEN_TIMEOUT_TIMER = "flatten_timeout"


class FlattenConfig(StrategyConfig, frozen=True):
    """Configuration for one-shot flatten strategy."""

    timeout_seconds: int = 30
    poll_interval_seconds: int = 2


class FlattenOnStartStrategy(BaseStrategy):
    """Submit market closes for all open positions, wait for flat, then stop.

    Emergency flatten bypasses ExecutionGateway pre-flight by design.
    Market orders may incur slippage; fills are not awaited synchronously.
    """

    def __init__(self, config: FlattenConfig, runtime: LiveRuntime) -> None:
        super().__init__(config)
        self.cfg = config
        self._runtime = runtime
        self._submitted_closes = 0

    def strategy_name(self) -> str:
        return "FlattenOnStart"

    def on_start(self) -> None:
        super().on_start()
        self._runtime.event_store.record("flatten_started", {})
        log.critical("Emergency flatten: closing all open positions")

        for position in self.cache.positions_open():
            if position.is_open:
                self.close_position(position)
                self._submitted_closes += 1

        if self._submitted_closes == 0:
            self._complete_flatten(still_open=0)
            return

        self._runtime.event_store.record(
            "flatten_pending",
            {"positions_submitted": self._submitted_closes},
        )
        self.clock.set_timer(
            name=_FLATTEN_WAIT_TIMER,
            interval=self.cfg.poll_interval_seconds,
            callback=self._on_flatten_poll,
        )
        self.clock.set_timer(
            name=_FLATTEN_TIMEOUT_TIMER,
            interval=self.cfg.timeout_seconds,
            callback=self._on_flatten_timeout,
        )

    def _open_position_count(self) -> int:
        return sum(1 for p in self.cache.positions_open() if p.is_open)

    def _on_flatten_poll(self, _event: object) -> None:
        still_open = self._open_position_count()
        if still_open == 0:
            self._cancel_flatten_timers()
            self._complete_flatten(still_open=0)

    def _on_flatten_timeout(self, _event: object) -> None:
        still_open = self._open_position_count()
        log.critical(
            "Emergency flatten timeout: still_open=%d submitted=%d",
            still_open,
            self._submitted_closes,
        )
        self._cancel_flatten_timers()
        self._complete_flatten(still_open=still_open)

    def _cancel_flatten_timers(self) -> None:
        self.clock.cancel_timer(_FLATTEN_WAIT_TIMER)
        self.clock.cancel_timer(_FLATTEN_TIMEOUT_TIMER)

    def _complete_flatten(self, still_open: int) -> None:
        self._runtime.event_store.record(
            "flatten_complete",
            {
                "positions_submitted": self._submitted_closes,
                "still_open": still_open,
                "timed_out": still_open > 0,
            },
        )
        log.info(
            "Emergency flatten complete: submitted=%d still_open=%d",
            self._submitted_closes,
            still_open,
        )
        self.stop()
