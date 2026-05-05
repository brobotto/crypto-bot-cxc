from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class EmaState:
    fast: Decimal
    slow: Decimal
    previous_fast: Decimal | None
    previous_slow: Decimal | None
    samples: int


def update_ema(
    *,
    close: Decimal,
    previous_fast: Decimal | None,
    previous_slow: Decimal | None,
    fast_period: int,
    slow_period: int,
    samples: int,
) -> EmaState:
    fast = _next_ema(close=close, previous=previous_fast, period=fast_period)
    slow = _next_ema(close=close, previous=previous_slow, period=slow_period)
    return EmaState(
        fast=fast,
        slow=slow,
        previous_fast=previous_fast,
        previous_slow=previous_slow,
        samples=samples + 1,
    )


def _next_ema(*, close: Decimal, previous: Decimal | None, period: int) -> Decimal:
    if period <= 0:
        raise ValueError("period must be positive")
    if previous is None:
        return close

    alpha = Decimal("2") / Decimal(period + 1)
    return close * alpha + previous * (Decimal("1") - alpha)

