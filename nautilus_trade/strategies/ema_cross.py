"""EMA Cross Strategy — reference implementation.

Logic:
- Go long when fast EMA crosses above slow EMA.
- Go flat when fast EMA crosses below slow EMA.
- Strategy-local risk: skip signal if position notional would exceed limit.

This strategy is intentionally simple. It exists to demonstrate the
correct NautilusTrader strategy lifecycle and event handling pattern.
"""

from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators.average.ema import ExponentialMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.objects import Quantity

from nautilus_trade.actors.regime_filter import RegimeSignal
from nautilus_trade.config import risk_cfg
from nautilus_trade.execution.gateway import ExecutionGateway, OrderIntent
from nautilus_trade.strategies.base import BaseStrategy


class EmaCrossConfig(StrategyConfig, frozen=True):
    instrument_id: str
    bar_type: str
    fast_period: int = 10
    slow_period: int = 30
    trade_size: str = "0.01"  # base quantity as string for precision
    max_position_notional_usd: float | None = None
    use_regime_filter: bool = True
    block_entries_until_regime: bool = False
    flatten_on_stop: bool = False


class EmaCrossStrategy(BaseStrategy):
    """EMA Cross — long only, strategy-local risk gated."""

    def __init__(
        self,
        config: EmaCrossConfig,
        gateway: ExecutionGateway | None = None,
    ) -> None:
        super().__init__(config)
        self.cfg = config
        self.gateway = gateway
        self.instrument_id = InstrumentId.from_str(config.instrument_id)
        self.bar_type = BarType.from_str(config.bar_type)
        self.fast_ema = ExponentialMovingAverage(config.fast_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_period)
        self._regime: RegimeSignal | None = None
        self._max_notional = (
            config.max_position_notional_usd
            if config.max_position_notional_usd is not None
            else risk_cfg.max_position_notional_usd
        )

    def _block_entries_until_regime(self) -> bool:
        from nautilus_trade.config import system_cfg

        if self.cfg.block_entries_until_regime:
            return True
        return system_cfg.block_entries_until_regime and not system_cfg.is_research

    def strategy_name(self) -> str:
        return f"EmaCross({self.cfg.fast_period}/{self.cfg.slow_period})"

    def on_start(self) -> None:
        super().on_start()
        self.log.info(
            "[%s] Resolved max position notional limit: %.2f USD",
            self.strategy_name(),
            self._max_notional,
        )
        if self.gateway is None:
            self.log.warning(
                "[%s] ExecutionGateway not wired — orders bypass portfolio-level risk checks",
                self.strategy_name(),
            )
        self.instrument = self.cache.instrument(self.instrument_id)
        if self.instrument is None:
            self.log.error("Instrument not found: %s", self.instrument_id)
            self.stop()
            return
        self.register_indicator_for_bars(self.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.bar_type, self.slow_ema)
        self.subscribe_bars(self.bar_type)
        if self.cfg.use_regime_filter:
            self.subscribe_data(RegimeSignal)

    def on_data(self, data: object) -> None:
        if isinstance(data, RegimeSignal) and data.instrument_id == str(self.instrument_id):
            self._regime = data

    def on_bar(self, bar: Bar) -> None:
        if not self.fast_ema.initialized or not self.slow_ema.initialized:
            return

        fast = self.fast_ema.value
        slow = self.slow_ema.value
        position = self.cache.position_for_instrument(self.instrument_id)
        is_long = position is not None and position.is_open and position.quantity > Decimal(0)
        is_flat = position is None or not position.is_open

        if fast > slow and is_flat:
            if self.cfg.use_regime_filter and self._block_entries_until_regime() and self._regime is None:
                self.log.debug("Signal suppressed: awaiting initial regime signal")
                return
            if (
                self.cfg.use_regime_filter
                and self._regime is not None
                and self._regime.is_trending is False
            ):
                self.log.debug("Signal suppressed: regime=ranging")
                return

            qty = Quantity.from_str(self.cfg.trade_size)
            approx_notional = float(qty) * float(bar.close)
            if approx_notional > self._max_notional:
                self.log.warning(
                    "Signal blocked by strategy risk limit: notional=%.2f limit=%.2f",
                    approx_notional,
                    self._max_notional,
                )
                return

            intent = OrderIntent(
                instrument_id=str(self.instrument_id),
                side="BUY",
                quantity=Decimal(str(qty)),
                price=None,
                strategy_id=self.strategy_name(),
                notional_usd=approx_notional,
            )

            def submit_entry() -> None:
                self.log_signal(OrderSide.BUY, self.instrument_id, qty, reason="ema_cross_up")
                order = self.order_factory.market(
                    instrument_id=self.instrument_id,
                    order_side=OrderSide.BUY,
                    quantity=qty,
                    time_in_force=TimeInForce.GTC,
                )
                self.submit_order(order)

            self.submit_order_guarded(self.gateway, intent, submit_entry)

        elif fast < slow and is_long:
            if self.trading_halted(self.gateway):
                self.log.warning(
                    "[%s] Exit suppressed: trading halted",
                    self.strategy_name(),
                )
                return

            exit_notional = float(self.position_notional(self.instrument_id))
            exit_qty = abs(position.quantity)
            intent = OrderIntent(
                instrument_id=str(self.instrument_id),
                side="SELL",
                quantity=Decimal(str(exit_qty)),
                price=None,
                strategy_id=self.strategy_name(),
                notional_usd=exit_notional if exit_notional > 0 else 0.0,
            )

            def submit_exit() -> None:
                self.log.info("[%s] Closing position: ema_cross_down", self.strategy_name())
                self.close_position(position)

            self.submit_exit_guarded(self.gateway, intent, submit_exit)

    def on_stop(self) -> None:
        super().on_stop()
        self.cancel_all_orders(self.instrument_id)
        if self.cfg.flatten_on_stop:
            self.log.warning(
                "[%s] flatten_on_stop enabled — closing all positions",
                self.strategy_name(),
            )
            self.close_all_positions(self.instrument_id)
