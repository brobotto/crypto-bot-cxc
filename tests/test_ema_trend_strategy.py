from datetime import UTC, datetime
from decimal import Decimal

from crypto_bot_cxc.events import MarketDataEvent
from crypto_bot_cxc.regime import RegimeState
from crypto_bot_cxc.strategy import EMATrendConfig, EMATrendStrategy


def event() -> MarketDataEvent:
    return MarketDataEvent(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        symbol="BTC/USDT",
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("100"),
        volume=Decimal("100"),
        timeframe="1h",
        is_closed=True,
    )


def test_reset_clears_previous_ema_state() -> None:
    strategy = EMATrendStrategy(EMATrendConfig(fast_period=2, slow_period=4))

    assert strategy.on_candle(
        event(),
        ema_fast=Decimal("90"),
        ema_slow=Decimal("100"),
        regime=RegimeState.UPTREND_LOW_VOL,
    ) == []
    assert len(
        strategy.on_candle(
            event(),
            ema_fast=Decimal("110"),
            ema_slow=Decimal("100"),
            regime=RegimeState.UPTREND_LOW_VOL,
        )
    ) == 1

    strategy.reset()

    assert strategy.on_candle(
        event(),
        ema_fast=Decimal("110"),
        ema_slow=Decimal("100"),
        regime=RegimeState.UPTREND_LOW_VOL,
    ) == []
