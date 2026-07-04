"""Fill tracking actor — wires OrderFilled events to portfolio risk and metrics."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from nautilus_trader.config import ActorConfig
from nautilus_trader.model.events import OrderFilled
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.actor import Actor

from nautilus_trade.ops.metrics import DAILY_PNL_USD, PORTFOLIO_NOTIONAL_USD
from nautilus_trade.portfolio.pnl import realized_pnl_delta_usd
from nautilus_trade.portfolio.stats import portfolio_notional_usd

if TYPE_CHECKING:
    from nautilus_trade.live.runtime import LiveRuntime

log = logging.getLogger(__name__)


class FillTrackerConfig(ActorConfig, frozen=True):
    instrument_id: str


class FillTrackerActor(Actor):
    """Records fills into the portfolio risk engine and Prometheus gauges."""

    def __init__(self, config: FillTrackerConfig, runtime: LiveRuntime) -> None:
        super().__init__(config)
        self.cfg = config
        self._runtime = runtime
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self._last_realized_pnl: dict[str, Decimal] = {}
        self._pnl_tracking_date: date = datetime.now(UTC).date()

    def on_start(self) -> None:
        self.subscribe_order_fills(self.instrument_id)
        log.info("FillTrackerActor subscribed to fills for %s", self.instrument_id)

    def on_order_filled(self, event: OrderFilled) -> None:
        self._reset_pnl_state_if_new_day()
        realized_pnl, pnl_source = realized_pnl_delta_usd(
            self.cache,
            event,
            self._last_realized_pnl,
        )
        if pnl_source == "unavailable":
            log.warning(
                "Fill PnL unavailable for %s; recording zero delta for daily halt",
                event.instrument_id,
            )

        self._runtime.risk_engine.record_fill(realized_pnl)
        daily_pnl = float(self._runtime.risk_engine.daily.realized_pnl_usd)
        DAILY_PNL_USD.set(daily_pnl)
        PORTFOLIO_NOTIONAL_USD.set(portfolio_notional_usd(self.cache, self.portfolio))
        self._runtime.event_store.record(
            "fill",
            {
                "instrument_id": str(event.instrument_id),
                "order_id": str(event.client_order_id),
                "side": event.order_side.name,
                "last_qty": str(event.last_qty),
                "last_px": str(event.last_px),
                "realized_pnl_usd": realized_pnl,
                "pnl_source": pnl_source,
                "daily_pnl_usd": daily_pnl,
            },
        )
        if self._runtime.risk_engine.is_halted:
            log.critical(
                "Portfolio risk halted after fill: daily_pnl=%.2f source=%s",
                daily_pnl,
                pnl_source,
            )

    def _reset_pnl_state_if_new_day(self) -> None:
        today = datetime.now(UTC).date()
        if today != self._pnl_tracking_date:
            self._pnl_tracking_date = today
            self._last_realized_pnl.clear()
