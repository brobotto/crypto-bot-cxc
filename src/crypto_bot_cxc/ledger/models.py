from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Position:
    symbol: str
    quantity: Decimal
    avg_entry_price: Decimal
    entry_fees_paid: Decimal


@dataclass(frozen=True, slots=True)
class Trade:
    fill_id: UUID
    intent_id: UUID
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    price: Decimal
    fee: Decimal
    realized_pnl: Decimal
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class PortfolioState:
    cash: Decimal
    positions: dict[str, Position]
    realized_pnl: Decimal
    fees_paid: Decimal
