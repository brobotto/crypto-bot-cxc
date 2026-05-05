from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from crypto_bot_cxc.events.models import FillEvent
from crypto_bot_cxc.execution.models import ConcreteOrder


class OrderStatus(StrEnum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True, slots=True)
class Balance:
    asset: str
    free: Decimal
    locked: Decimal

    @property
    def total(self) -> Decimal:
        return self.free + self.locked


class BrokerInterface(ABC):
    """Stable boundary shared by backtest, paper, and live brokers."""

    @abstractmethod
    def submit_order(self, order: ConcreteOrder) -> UUID:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_order_status(self, order_id: UUID) -> OrderStatus:
        raise NotImplementedError

    @abstractmethod
    def get_balance(self) -> list[Balance]:
        raise NotImplementedError

    @abstractmethod
    def get_open_orders(self) -> list[ConcreteOrder]:
        raise NotImplementedError

    @abstractmethod
    def get_fills_since(self, timestamp: datetime) -> list[FillEvent]:
        raise NotImplementedError
