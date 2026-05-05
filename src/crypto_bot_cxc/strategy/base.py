from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from crypto_bot_cxc.events.models import MarketDataEvent, OrderIntent
from crypto_bot_cxc.regime.models import RegimeState


class BaseStrategy(ABC):
    @abstractmethod
    def on_candle(
        self,
        event: MarketDataEvent,
        *,
        ema_fast: Decimal,
        ema_slow: Decimal,
        regime: RegimeState,
    ) -> list[OrderIntent]:
        raise NotImplementedError

