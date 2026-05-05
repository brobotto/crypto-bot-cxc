from __future__ import annotations

from decimal import Decimal

from nautilus_trader.config import PositiveInt, StrategyConfig
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.instruments import Instrument
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.trading.strategy import Strategy


class EmaCrossNextOpenConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    fast_period: PositiveInt = 20
    slow_period: PositiveInt = 100
    risk_fraction: float = 0.01


class EmaCrossNextOpen(Strategy):
    """
    EMA crossover strategy for the Nautilus spike.

    Nautilus bar-only market orders fill at the latest bar close. This strategy queues a
    signal for the next bar and the runner feeds trade ticks at candle opens, so the
    executable price proxy matches the common next-open spec.
    """

    def __init__(self, config: EmaCrossNextOpenConfig) -> None:
        super().__init__(config)
        self.instrument: Instrument | None = None
        self._fast_ema: float | None = None
        self._slow_ema: float | None = None
        self._samples = 0
        self._pending_action: str | None = None
        self._internal_long = False

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Could not find instrument {self.config.instrument_id}")
            self.stop()
            return
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar) -> None:
        self._execute_pending_action(bar)
        self._update_ema_and_signal(bar)

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        if self._internal_long:
            self.close_all_positions(self.config.instrument_id)
            self._internal_long = False
        self.unsubscribe_bars(self.config.bar_type)

    def on_reset(self) -> None:
        self._fast_ema = None
        self._slow_ema = None
        self._samples = 0
        self._pending_action = None
        self._internal_long = False

    def _execute_pending_action(self, bar: Bar) -> None:
        if self._pending_action == "buy" and not self._internal_long:
            self._buy(bar)
            self._internal_long = True
        elif self._pending_action == "sell" and self._internal_long:
            self.close_all_positions(self.config.instrument_id)
            self._internal_long = False
        self._pending_action = None

    def _update_ema_and_signal(self, bar: Bar) -> None:
        close = float(bar.close)
        previous_fast = self._fast_ema
        previous_slow = self._slow_ema
        fast_alpha = 2.0 / (self.config.fast_period + 1)
        slow_alpha = 2.0 / (self.config.slow_period + 1)
        self._fast_ema = (
            close
            if self._fast_ema is None
            else fast_alpha * close + (1.0 - fast_alpha) * self._fast_ema
        )
        self._slow_ema = (
            close
            if self._slow_ema is None
            else slow_alpha * close + (1.0 - slow_alpha) * self._slow_ema
        )
        self._samples += 1

        if (
            self._samples <= self.config.slow_period
            or previous_fast is None
            or previous_slow is None
        ):
            return

        crossed_up = previous_fast <= previous_slow and self._fast_ema > self._slow_ema
        crossed_down = previous_fast >= previous_slow and self._fast_ema < self._slow_ema
        if crossed_up and not self._internal_long:
            self._pending_action = "buy"
        elif crossed_down and self._internal_long:
            self._pending_action = "sell"

    def _buy(self, bar: Bar) -> None:
        if self.instrument is None:
            return
        account = self.cache.account_for_venue(self.config.instrument_id.venue)
        cash = float(account.balance_free(USDT)) if account is not None else 0.0
        quantity = Decimal(str(max(cash * self.config.risk_fraction / float(bar.open), 0.0)))
        if quantity <= 0:
            return
        order: MarketOrder = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(quantity),
            time_in_force=TimeInForce.IOC,
        )
        self.submit_order(order)
