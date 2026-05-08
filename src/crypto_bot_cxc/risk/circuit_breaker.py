from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from crypto_bot_cxc.ledger.models import PortfolioState


class CircuitBreakerReason(StrEnum):
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    MAX_DRAWDOWN = "MAX_DRAWDOWN"
    CONSECUTIVE_LOSSES = "CONSECUTIVE_LOSSES"


@dataclass(frozen=True, slots=True)
class CircuitBreakerConfig:
    daily_loss_limit: Decimal
    max_drawdown: Decimal
    max_consecutive_losses: int

    def __post_init__(self) -> None:
        if self.daily_loss_limit <= 0 or self.daily_loss_limit > 1:
            raise ValueError("daily_loss_limit must be within (0, 1]")
        if self.max_drawdown <= 0 or self.max_drawdown > 1:
            raise ValueError("max_drawdown must be within (0, 1]")
        if self.max_consecutive_losses <= 0:
            raise ValueError("max_consecutive_losses must be positive")


@dataclass(frozen=True, slots=True)
class CircuitBreakerStatus:
    is_blocked: bool
    reason: CircuitBreakerReason | None


@dataclass(slots=True)
class _CircuitBreakerState:
    day: date | None = None
    day_start_equity: Decimal | None = None
    peak_equity: Decimal | None = None
    last_realized_pnl: Decimal = Decimal("0")
    consecutive_losses: int = 0


class CircuitBreaker:
    """Stateful V1 entry blocker.

    This module only blocks new entries. It does not flatten positions or reject
    exits; those policies belong to later live-risk work.
    """

    def __init__(self, config: CircuitBreakerConfig) -> None:
        self._config = config
        self._state = _CircuitBreakerState()

    def check(
        self,
        *,
        portfolio_state: PortfolioState,
        current_equity: Decimal,
        as_of: datetime | None,
    ) -> CircuitBreakerStatus:
        """Observe current state and return whether new entries should be blocked.

        This method has side effects: it updates day-start equity, peak equity,
        last realized PnL, and the consecutive-loss counter.
        """
        if current_equity <= 0:
            return CircuitBreakerStatus(
                is_blocked=True,
                reason=CircuitBreakerReason.MAX_DRAWDOWN,
            )

        self._observe_day(current_equity=current_equity, as_of=as_of)
        self._observe_peak(current_equity)
        self._observe_realized_pnl(portfolio_state.realized_pnl)

        reason = self._block_reason(current_equity)
        return CircuitBreakerStatus(is_blocked=reason is not None, reason=reason)

    @property
    def consecutive_losses(self) -> int:
        return self._state.consecutive_losses

    def reset(self) -> None:
        self._state = _CircuitBreakerState()

    def _observe_day(self, *, current_equity: Decimal, as_of: datetime | None) -> None:
        current_day = as_of.date() if as_of is not None else None
        if self._state.day != current_day:
            self._state.day = current_day
            self._state.day_start_equity = current_equity

    def _observe_peak(self, current_equity: Decimal) -> None:
        if self._state.peak_equity is None or current_equity > self._state.peak_equity:
            self._state.peak_equity = current_equity

    def _observe_realized_pnl(self, realized_pnl: Decimal) -> None:
        pnl_delta = realized_pnl - self._state.last_realized_pnl
        if pnl_delta < 0:
            self._state.consecutive_losses += 1
        elif pnl_delta > 0:
            self._state.consecutive_losses = 0
        self._state.last_realized_pnl = realized_pnl

    def _block_reason(self, current_equity: Decimal) -> CircuitBreakerReason | None:
        if self._daily_loss_fraction(current_equity) >= self._config.daily_loss_limit:
            return CircuitBreakerReason.DAILY_LOSS_LIMIT
        if self._drawdown_fraction(current_equity) >= self._config.max_drawdown:
            return CircuitBreakerReason.MAX_DRAWDOWN
        if self._state.consecutive_losses >= self._config.max_consecutive_losses:
            return CircuitBreakerReason.CONSECUTIVE_LOSSES
        return None

    def _daily_loss_fraction(self, current_equity: Decimal) -> Decimal:
        day_start = self._state.day_start_equity
        if day_start is None or day_start <= 0 or current_equity >= day_start:
            return Decimal("0")
        return (day_start - current_equity) / day_start

    def _drawdown_fraction(self, current_equity: Decimal) -> Decimal:
        peak = self._state.peak_equity
        if peak is None or peak <= 0 or current_equity >= peak:
            return Decimal("0")
        return (peak - current_equity) / peak
