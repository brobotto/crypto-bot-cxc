from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_DOWN, Decimal

from crypto_bot_cxc.events.models import OrderIntent
from crypto_bot_cxc.ledger.models import PortfolioState
from crypto_bot_cxc.risk.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


@dataclass(frozen=True, slots=True)
class RiskConfig:
    """Risk settings enforced by the V1 baseline manager."""

    risk_per_trade: Decimal
    max_open_positions: int
    capital_reserve: Decimal = Decimal("0")
    daily_loss_limit: Decimal = Decimal("1")
    max_drawdown: Decimal = Decimal("1")
    max_consecutive_losses: int = 3
    min_order_notional: Decimal = Decimal("10")
    quantity_step: Decimal = Decimal("0.000001")

    def __post_init__(self) -> None:
        if self.risk_per_trade <= 0 or self.risk_per_trade > 1:
            raise ValueError("risk_per_trade must be within (0, 1]")
        if self.max_open_positions <= 0:
            raise ValueError("max_open_positions must be positive")
        if self.capital_reserve < 0 or self.capital_reserve >= 1:
            raise ValueError("capital_reserve must be within [0, 1)")
        if self.daily_loss_limit <= 0 or self.daily_loss_limit > 1:
            raise ValueError("daily_loss_limit must be within (0, 1]")
        if self.max_drawdown <= 0 or self.max_drawdown > 1:
            raise ValueError("max_drawdown must be within (0, 1]")
        if self.max_consecutive_losses <= 0:
            raise ValueError("max_consecutive_losses must be positive")
        if self.min_order_notional <= 0:
            raise ValueError("min_order_notional must be positive")
        if self.quantity_step <= 0:
            raise ValueError("quantity_step must be positive")


class RiskManager:
    """V1 baseline long-only risk manager."""

    def __init__(self, config: RiskConfig) -> None:
        self._config = config
        self._circuit_breaker = CircuitBreaker(
            CircuitBreakerConfig(
                daily_loss_limit=config.daily_loss_limit,
                max_drawdown=config.max_drawdown,
                max_consecutive_losses=config.max_consecutive_losses,
            )
        )

    def validate(
        self,
        intent: OrderIntent,
        portfolio_state: PortfolioState,
        current_price: Decimal,
        current_equity: Decimal | None = None,
        as_of: datetime | None = None,
    ) -> OrderIntent | None:
        if intent.side == "BUY":
            return self._approve_buy(
                intent,
                portfolio_state,
                current_price,
                current_equity=current_equity,
                as_of=as_of,
            )
        return self._approve_sell(intent, portfolio_state)

    def observe(
        self,
        *,
        portfolio_state: PortfolioState,
        current_equity: Decimal,
        as_of: datetime | None = None,
    ) -> None:
        self._circuit_breaker.check(
            portfolio_state=portfolio_state,
            current_equity=current_equity,
            as_of=as_of,
        )

    def _approve_buy(
        self,
        intent: OrderIntent,
        portfolio_state: PortfolioState,
        current_price: Decimal,
        current_equity: Decimal | None,
        as_of: datetime | None,
    ) -> OrderIntent | None:
        equity = (
            current_equity
            if current_equity is not None
            else self._approximate_equity(intent, portfolio_state, current_price)
        )
        if self._circuit_breaker.check(
            portfolio_state=portfolio_state,
            current_equity=equity,
            as_of=as_of,
        ).is_blocked:
            return None

        if intent.symbol in portfolio_state.positions:
            return None
        if len(portfolio_state.positions) >= self._config.max_open_positions:
            return None

        tradable_cash = portfolio_state.cash * (Decimal("1") - self._config.capital_reserve)
        budget = tradable_cash * self._config.risk_per_trade
        if budget < self._config.min_order_notional:
            return None

        quantity = self._round_quantity(budget / current_price)
        if quantity <= 0:
            return None
        return replace(intent, quantity=quantity)

    def _approve_sell(
        self,
        intent: OrderIntent,
        portfolio_state: PortfolioState,
    ) -> OrderIntent | None:
        position = portfolio_state.positions.get(intent.symbol)
        if position is None or position.quantity <= 0:
            return None
        quantity = intent.quantity or position.quantity
        if quantity > position.quantity:
            quantity = position.quantity
        return replace(intent, quantity=quantity)

    def _round_quantity(self, quantity: Decimal) -> Decimal:
        return quantity.quantize(self._config.quantity_step, rounding=ROUND_DOWN)

    def _approximate_equity(
        self,
        intent: OrderIntent,
        portfolio_state: PortfolioState,
        current_price: Decimal,
    ) -> Decimal:
        equity = portfolio_state.cash
        for symbol, position in portfolio_state.positions.items():
            if symbol == intent.symbol:
                equity += position.quantity * current_price
        return equity
