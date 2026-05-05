from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from crypto_bot_cxc.events.models import MarketDataEvent, OrderIntent
from crypto_bot_cxc.execution.models import Urgency
from crypto_bot_cxc.regime.models import RegimeState
from crypto_bot_cxc.strategy.base import BaseStrategy


@dataclass(frozen=True, slots=True)
class EMATrendConfig:
    fast_period: int
    slow_period: int
    strategy_id: str = "ema_trend"

    def __post_init__(self) -> None:
        if self.fast_period <= 0 or self.slow_period <= 0:
            raise ValueError("EMA periods must be positive")
        if self.fast_period >= self.slow_period:
            raise ValueError("fast_period must be lower than slow_period")


class EMATrendStrategy(BaseStrategy):
    def __init__(self, config: EMATrendConfig) -> None:
        self.config = config
        self._previous_fast: Decimal | None = None
        self._previous_slow: Decimal | None = None

    def on_candle(
        self,
        event: MarketDataEvent,
        *,
        ema_fast: Decimal,
        ema_slow: Decimal,
        regime: RegimeState,
    ) -> list[OrderIntent]:
        if not event.is_closed:
            return []

        intents: list[OrderIntent] = []
        if self._previous_fast is not None and self._previous_slow is not None:
            crossed_up = self._previous_fast <= self._previous_slow and ema_fast > ema_slow
            crossed_down = self._previous_fast >= self._previous_slow and ema_fast < ema_slow

            if crossed_up:
                intents.append(
                    OrderIntent(
                        strategy_id=self.config.strategy_id,
                        symbol=event.symbol,
                        side="BUY",
                        urgency=Urgency.NORMAL,
                        reason="ema_cross_up",
                        quantity=None,
                        limit_price=None,
                        stop_price=None,
                        deadline=None,
                        regime=regime,
                    )
                )
            elif crossed_down:
                intents.append(
                    OrderIntent(
                        strategy_id=self.config.strategy_id,
                        symbol=event.symbol,
                        side="SELL",
                        urgency=Urgency.URGENT_EXIT,
                        reason="ema_cross_down",
                        quantity=None,
                        limit_price=None,
                        stop_price=None,
                        deadline=None,
                        regime=regime,
                    )
                )

        self._previous_fast = ema_fast
        self._previous_slow = ema_slow
        return intents

