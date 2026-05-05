from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from crypto_bot_cxc.broker.base import Balance, BrokerInterface, OrderStatus
from crypto_bot_cxc.events.models import FillEvent, MarketDataEvent
from crypto_bot_cxc.execution.models import ConcreteOrder, OrderType


@dataclass(frozen=True, slots=True)
class BacktestBrokerConfig:
    fee_rate: Decimal
    slippage_rate: Decimal


@dataclass(frozen=True, slots=True)
class _OrderRecord:
    order_id: UUID
    order: ConcreteOrder


class BacktestBroker(BrokerInterface):
    """Minimal next-candle fill broker for Spike C.

    Orders submitted after candle N are evaluated when candle N+1 is advanced.
    This keeps the broker from filling on the signal candle.
    """

    def __init__(self, config: BacktestBrokerConfig) -> None:
        self._config = config
        self._pending: list[_OrderRecord] = []
        self._open_orders: dict[UUID, ConcreteOrder] = {}
        self._statuses: dict[UUID, OrderStatus] = {}
        self._fills: list[FillEvent] = []

    def submit_order(self, order: ConcreteOrder) -> UUID:
        order_id = uuid4()
        self._pending.append(_OrderRecord(order_id=order_id, order=order))
        self._open_orders[order_id] = order
        self._statuses[order_id] = OrderStatus.NEW
        return order_id

    def cancel_order(self, order_id: UUID) -> bool:
        if order_id not in self._open_orders:
            return False
        self._pending = [record for record in self._pending if record.order_id != order_id]
        del self._open_orders[order_id]
        self._statuses[order_id] = OrderStatus.CANCELED
        return True

    def get_order_status(self, order_id: UUID) -> OrderStatus:
        return self._statuses.get(order_id, OrderStatus.REJECTED)

    def get_balance(self) -> list[Balance]:
        # PortfolioLedger is the source of truth for Spike C balances.
        return []

    def get_open_orders(self) -> list[ConcreteOrder]:
        return list(self._open_orders.values())

    def get_fills_since(self, timestamp: datetime) -> list[FillEvent]:
        return [fill for fill in self._fills if fill.filled_at >= timestamp]

    @property
    def fills(self) -> list[FillEvent]:
        return list(self._fills)

    def advance_to_candle(self, candle: MarketDataEvent) -> list[FillEvent]:
        if not candle.is_closed:
            return []

        records = self._pending
        self._pending = []
        fills: list[FillEvent] = []

        for record in records:
            fill_price = self._fill_price(record.order, candle)
            if fill_price is None:
                self._pending.append(record)
                continue

            notional = record.order.quantity * fill_price
            fee = notional * self._config.fee_rate
            fill = FillEvent(
                order_id=record.order_id,
                intent_id=record.order.intent_id,
                symbol=record.order.symbol,
                side=record.order.side,
                quantity=record.order.quantity,
                price=fill_price,
                fee=fee,
                fee_currency="USDT",
                filled_at=candle.timestamp,
                is_partial=False,
            )
            fills.append(fill)
            self._fills.append(fill)
            self._statuses[record.order_id] = OrderStatus.FILLED
            self._open_orders.pop(record.order_id, None)

        return fills

    def _fill_price(self, order: ConcreteOrder, candle: MarketDataEvent) -> Decimal | None:
        if order.order_type == OrderType.MARKET:
            if order.side == "BUY":
                return candle.open * (Decimal("1") + self._config.slippage_rate)
            return candle.open * (Decimal("1") - self._config.slippage_rate)

        if order.limit_price is None:
            return None

        if order.side == "BUY" and candle.low <= order.limit_price:
            return min(order.limit_price, candle.open)
        if order.side == "SELL" and candle.high >= order.limit_price:
            return max(order.limit_price, candle.open)
        return None
