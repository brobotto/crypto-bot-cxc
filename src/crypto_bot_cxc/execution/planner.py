from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from crypto_bot_cxc.events.models import OrderIntent
from crypto_bot_cxc.execution.models import ConcreteOrder, OrderType, TimeInForce, Urgency


@dataclass(frozen=True, slots=True)
class ExecutionPlannerConfig:
    use_next_open_market_model: bool = True


class ExecutionPlanner:
    """Convert approved OrderIntent into broker-facing ConcreteOrder."""

    def __init__(self, config: ExecutionPlannerConfig | None = None) -> None:
        self._config = config or ExecutionPlannerConfig()

    def plan(self, intent: OrderIntent, market_price: Decimal) -> ConcreteOrder:
        if intent.quantity is None:
            raise ValueError("approved intent must include quantity")

        order_type = self._order_type_for(intent.urgency)
        limit_price = None
        if order_type != OrderType.MARKET:
            limit_price = market_price if intent.limit_price is None else intent.limit_price
        tif = TimeInForce.GTC if order_type != OrderType.MARKET else TimeInForce.IOC

        return ConcreteOrder(
            intent_id=intent.intent_id,
            symbol=intent.symbol,
            side=intent.side,
            order_type=order_type,
            quantity=intent.quantity,
            limit_price=limit_price,
            stop_price=intent.stop_price,
            time_in_force=tif,
            client_order_id=f"cxc-{intent.intent_id.hex[:20]}",
            created_at=datetime.now(UTC),
        )

    def _order_type_for(self, urgency: Urgency) -> OrderType:
        if self._config.use_next_open_market_model:
            return OrderType.MARKET
        if urgency == Urgency.PASSIVE:
            return OrderType.POST_ONLY_LIMIT
        if urgency in {Urgency.URGENT_EXIT, Urgency.EMERGENCY, Urgency.PROTECTIVE}:
            return OrderType.MARKET
        if urgency == Urgency.ATOMIC:
            return OrderType.LIMIT_FOK
        if urgency == Urgency.TIME_SENSITIVE:
            return OrderType.LIMIT_IOC
        return OrderType.LIMIT
