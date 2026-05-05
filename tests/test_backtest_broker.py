from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from crypto_bot_cxc.broker import BacktestBroker, BacktestBrokerConfig, OrderStatus
from crypto_bot_cxc.events import MarketDataEvent
from crypto_bot_cxc.execution import ConcreteOrder, OrderType, TimeInForce


def candle(open_price: str = "100") -> MarketDataEvent:
    return MarketDataEvent(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        symbol="BTC/USDT",
        open=Decimal(open_price),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("100"),
        timeframe="1h",
        is_closed=True,
    )


def market_order(side: Literal["BUY", "SELL"]) -> ConcreteOrder:
    return ConcreteOrder(
        intent_id=uuid4(),
        symbol="BTC/USDT",
        side=side,
        order_type=OrderType.MARKET,
        quantity=Decimal("1"),
        limit_price=None,
        stop_price=None,
        time_in_force=TimeInForce.IOC,
        client_order_id=f"test-{side}",
        created_at=datetime.now(UTC),
    )


def test_market_buy_fill_applies_positive_slippage_and_fee() -> None:
    broker = BacktestBroker(
        BacktestBrokerConfig(fee_rate=Decimal("0.001"), slippage_rate=Decimal("0.001"))
    )
    order_id = broker.submit_order(market_order("BUY"))

    fills = broker.advance_to_candle(candle("100"))

    assert len(fills) == 1
    assert fills[0].price == Decimal("100.100")
    assert fills[0].fee == Decimal("0.100100")
    assert broker.get_order_status(order_id) == OrderStatus.FILLED


def test_market_sell_fill_applies_negative_slippage() -> None:
    broker = BacktestBroker(
        BacktestBrokerConfig(fee_rate=Decimal("0.001"), slippage_rate=Decimal("0.001"))
    )
    broker.submit_order(market_order("SELL"))

    fills = broker.advance_to_candle(candle("100"))

    assert fills[0].price == Decimal("99.900")
