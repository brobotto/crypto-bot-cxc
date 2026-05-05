from decimal import Decimal

from crypto_bot_cxc.events import OrderIntent
from crypto_bot_cxc.execution import OrderType, Urgency
from crypto_bot_cxc.execution.planner import ExecutionPlanner
from crypto_bot_cxc.regime import RegimeState


def test_planner_turns_approved_intent_into_concrete_market_order() -> None:
    intent = OrderIntent(
        strategy_id="ema_trend",
        symbol="BTC/USDT",
        side="BUY",
        urgency=Urgency.NORMAL,
        reason="ema_cross_up",
        quantity=Decimal("0.1"),
        limit_price=None,
        stop_price=None,
        deadline=None,
        regime=RegimeState.UPTREND_LOW_VOL,
    )

    order = ExecutionPlanner().plan(intent, market_price=Decimal("100"))

    assert order.intent_id == intent.intent_id
    assert order.order_type == OrderType.MARKET
    assert order.quantity == Decimal("0.1")

