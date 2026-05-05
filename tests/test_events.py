from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from crypto_bot_cxc.events import FillEvent, MarketDataEvent, OrderIntent
from crypto_bot_cxc.execution import Urgency
from crypto_bot_cxc.regime import RegimeState


def test_market_data_event_requires_utc_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        MarketDataEvent(
            timestamp=datetime(2024, 1, 1),
            symbol="BTC/USDT",
            open=Decimal("1"),
            high=Decimal("1"),
            low=Decimal("1"),
            close=Decimal("1"),
            volume=Decimal("1"),
            timeframe="1h",
            is_closed=True,
        )


def test_market_data_event_rejects_inconsistent_ohlc() -> None:
    with pytest.raises(ValueError, match="open must be within"):
        MarketDataEvent(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            symbol="BTC/USDT",
            open=Decimal("120"),
            high=Decimal("110"),
            low=Decimal("90"),
            close=Decimal("100"),
            volume=Decimal("1"),
            timeframe="1h",
            is_closed=True,
        )


def test_order_intent_contract() -> None:
    intent = OrderIntent(
        strategy_id="ema_trend",
        symbol="BTC/USDT",
        side="BUY",
        urgency=Urgency.NORMAL,
        reason="ema_crossover",
        quantity=Decimal("0.01"),
        limit_price=None,
        stop_price=None,
        deadline=None,
        regime=RegimeState.UPTREND_LOW_VOL,
    )

    assert intent.strategy_id == "ema_trend"
    assert intent.urgency == Urgency.NORMAL


def test_fill_event_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValueError, match="quantity"):
        FillEvent(
            order_id=uuid4(),
            intent_id=uuid4(),
            symbol="BTC/USDT",
            side="BUY",
            quantity=Decimal("0"),
            price=Decimal("100"),
            fee=Decimal("0"),
            fee_currency="USDT",
            filled_at=datetime.now(UTC),
            is_partial=False,
        )
