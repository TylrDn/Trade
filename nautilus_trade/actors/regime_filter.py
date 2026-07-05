"""Regime Filter Actor.

Publishes a regime flag to the message bus that strategies can subscribe
to for conditional signal gating. Default implementation: ATR-based
trend vs. ranging detection.

Strategies should consume the RegimeSignal from cache rather than
reimplementing regime logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from nautilus_trader.config import ActorConfig
from nautilus_trader.core.data import Data
from nautilus_trader.indicators.atr import AverageTrueRange
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.trading.actor import Actor

log = logging.getLogger(__name__)


@dataclass
class RegimeSignal(Data):
    """Published to MessageBus when regime changes."""

    instrument_id: str
    is_trending: bool
    atr: float
    ts_event: int
    ts_init: int


class RegimeFilterConfig(ActorConfig, frozen=True):
    bar_type: str
    atr_period: int = 14
    trend_atr_threshold: float = 0.005  # ATR as fraction of price


class RegimeFilterActor(Actor):
    """Publishes RegimeSignal based on ATR trend filter."""

    def __init__(self, config: RegimeFilterConfig) -> None:
        super().__init__(config)
        self.cfg = config
        self.bar_type = BarType.from_str(config.bar_type)
        self.atr = AverageTrueRange(config.atr_period)
        self._last_trending: bool | None = None
        self._initial_signal_published = False

    def on_start(self) -> None:
        self.register_indicator_for_bars(self.bar_type, self.atr)
        self.subscribe_bars(self.bar_type)
        log.info("RegimeFilterActor started for %s", self.bar_type)

    def on_bar(self, bar: Bar) -> None:
        if not self.atr.initialized:
            return
        close = float(bar.close)
        if close == 0:
            return
        atr_ratio = self.atr.value / close
        is_trending = atr_ratio >= self.cfg.trend_atr_threshold
        if not self._initial_signal_published:
            self._initial_signal_published = True
            self._last_trending = is_trending
            self._publish_signal(bar, is_trending)
            return
        if is_trending != self._last_trending:
            self._last_trending = is_trending
            self._publish_signal(bar, is_trending)

    def _publish_signal(self, bar: Bar, is_trending: bool) -> None:
        signal = RegimeSignal(
            instrument_id=str(self.bar_type.instrument_id),
            is_trending=is_trending,
            atr=self.atr.value,
            ts_event=bar.ts_event,
            ts_init=bar.ts_init,
        )
        self.publish_data(type(signal), signal)
        log.info(
            "Regime change: instrument=%s trending=%s atr=%.6f",
            self.bar_type.instrument_id,
            is_trending,
            self.atr.value,
        )
