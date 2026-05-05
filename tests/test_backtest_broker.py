from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from crypto_bot_cxc.broker import BacktestBroker, BacktestBrokerConfig, OrderStatus
from crypto_bot_cxc.events import MarketDataEvent
from crypto_bot_cxc.execution import ConcreteOrder, OrderType, TimeInForce


def candle(open_price: str = "100", *, is_closed: bool = True) -> MarketDataEvent:
    return MarketDataEvent(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        symbol="BTC/USDT",
        open=Decimal(open_price),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("100"),
        timeframe="1h",
        is_closed=is_closed,
    )


def order(
    side: Literal["BUY", "SELL"],
    order_type: OrderType = OrderType.MARKET,
    limit_price: Decimal | None = None,
) -> ConcreteOrder:
    return ConcreteOrder(
        intent_id=uuid4(),
        symbol="BTC/USDT",
        side=side,
        order_type=order_type,
        quantity=Decimal("1"),
        limit_price=limit_price,
        stop_price=None,
        time_in_force=TimeInForce.IOC,
        client_order_id=f"test-{side}",
        created_at=datetime.now(UTC),
    )


def test_market_buy_fill_applies_positive_slippage_and_fee() -> None:
    broker = BacktestBroker(
        BacktestBrokerConfig(fee_rate=Decimal("0.001"), slippage_rate=Decimal("0.001"))
    )
    order_id = broker.submit_order(order("BUY"))

    fills = broker.advance_to_candle(candle("100"))

    assert len(fills) == 1
    assert fills[0].price == Decimal("100.100")
    assert fills[0].fee == Decimal("0.100100")
    assert broker.get_order_status(order_id) == OrderStatus.FILLED


def test_market_sell_fill_applies_negative_slippage() -> None:
    broker = BacktestBroker(
        BacktestBrokerConfig(fee_rate=Decimal("0.001"), slippage_rate=Decimal("0.001"))
    )
    broker.submit_order(order("SELL"))

    fills = broker.advance_to_candle(candle("100"))

    assert fills[0].price == Decimal("99.900")


def test_limit_buy_gap_down_fills_at_better_open_price() -> None:
    broker = BacktestBroker(BacktestBrokerConfig(fee_rate=Decimal("0"), slippage_rate=Decimal("0")))
    broker.submit_order(order("BUY", OrderType.LIMIT, Decimal("100")))

    fills = broker.advance_to_candle(candle("95"))

    assert fills[0].price == Decimal("95")


def test_limit_sell_gap_up_fills_at_better_open_price() -> None:
    broker = BacktestBroker(BacktestBrokerConfig(fee_rate=Decimal("0"), slippage_rate=Decimal("0")))
    broker.submit_order(order("SELL", OrderType.LIMIT, Decimal("100")))

    fills = broker.advance_to_candle(candle("105"))

    assert fills[0].price == Decimal("105")


def test_cancel_pending_order_prevents_future_fill() -> None:
    broker = BacktestBroker(BacktestBrokerConfig(fee_rate=Decimal("0"), slippage_rate=Decimal("0")))
    order_id = broker.submit_order(order("BUY"))

    assert broker.cancel_order(order_id) is True
    assert broker.advance_to_candle(candle("100")) == []
    assert broker.get_order_status(order_id) == OrderStatus.CANCELED


def test_non_closed_candle_does_not_fill_pending_orders() -> None:
    broker = BacktestBroker(BacktestBrokerConfig(fee_rate=Decimal("0"), slippage_rate=Decimal("0")))
    broker.submit_order(order("BUY"))

    assert broker.advance_to_candle(candle("100", is_closed=False)) == []
    assert len(broker.get_open_orders()) == 1
