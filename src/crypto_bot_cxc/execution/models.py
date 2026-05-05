from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import UUID


class Urgency(StrEnum):
    PASSIVE = "PASSIVE"
    NORMAL = "NORMAL"
    TIME_SENSITIVE = "TIME_SENSITIVE"
    URGENT_EXIT = "URGENT_EXIT"
    EMERGENCY = "EMERGENCY"
    ATOMIC = "ATOMIC"
    PROTECTIVE = "PROTECTIVE"


class OrderType(StrEnum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    LIMIT_IOC = "LIMIT_IOC"
    LIMIT_FOK = "LIMIT_FOK"
    POST_ONLY_LIMIT = "POST_ONLY_LIMIT"


class TimeInForce(StrEnum):
    GTC = "GTC"
    IOC = "IOC"
    FOK = "FOK"
    POST_ONLY = "POST_ONLY"


@dataclass(frozen=True, slots=True)
class ConcreteOrder:
    intent_id: UUID
    symbol: str
    side: Literal["BUY", "SELL"]
    order_type: OrderType
    quantity: Decimal
    limit_price: Decimal | None
    stop_price: Decimal | None
    time_in_force: TimeInForce
    client_order_id: str
    created_at: datetime

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type != OrderType.MARKET and self.limit_price is None:
            raise ValueError("non-market orders require limit_price")
        if not self.client_order_id:
            raise ValueError("client_order_id is required")

