from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from crypto_bot_cxc.execution.models import Urgency
from crypto_bot_cxc.regime.models import RegimeState


@dataclass(frozen=True, slots=True)
class MarketDataEvent:
    timestamp: datetime
    symbol: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    timeframe: str
    is_closed: bool

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware UTC")
        if self.timestamp.utcoffset() != UTC.utcoffset(self.timestamp):
            raise ValueError("timestamp must be UTC")
        if not self.symbol:
            raise ValueError("symbol is required")
        if not self.timeframe:
            raise ValueError("timeframe is required")
        if self.high <= 0 or self.low <= 0 or self.open <= 0 or self.close <= 0:
            raise ValueError("OHLC prices must be positive")
        if self.volume < 0:
            raise ValueError("volume cannot be negative")
        if self.low > self.high:
            raise ValueError("low cannot exceed high")
        if not self.low <= self.open <= self.high:
            raise ValueError("open must be within [low, high]")
        if not self.low <= self.close <= self.high:
            raise ValueError("close must be within [low, high]")


@dataclass(frozen=True, slots=True)
class RegimeEvent:
    timestamp: datetime
    symbol: str
    state: RegimeState
    confidence: Decimal
    previous_state: RegimeState | None = None


@dataclass(frozen=True, slots=True)
class OrderIntent:
    strategy_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    urgency: Urgency
    reason: str
    quantity: Decimal | None
    limit_price: Decimal | None
    stop_price: Decimal | None
    deadline: datetime | None
    regime: RegimeState
    intent_id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("strategy_id is required")
        if not self.symbol:
            raise ValueError("symbol is required")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if not self.reason:
            raise ValueError("reason is required")


@dataclass(frozen=True, slots=True)
class FillEvent:
    order_id: UUID
    intent_id: UUID
    symbol: str
    side: Literal["BUY", "SELL"]
    quantity: Decimal
    price: Decimal
    fee: Decimal
    fee_currency: str
    filled_at: datetime
    is_partial: bool

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.price <= 0:
            raise ValueError("price must be positive")
        if self.fee < 0:
            raise ValueError("fee cannot be negative")
        if not self.fee_currency:
            raise ValueError("fee_currency is required")
