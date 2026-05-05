from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import ROUND_DOWN, Decimal

from crypto_bot_cxc.events.models import OrderIntent
from crypto_bot_cxc.ledger.models import PortfolioState


@dataclass(frozen=True, slots=True)
class RiskConfig:
    risk_per_trade: Decimal
    max_open_positions: int
    min_order_notional: Decimal = Decimal("10")
    quantity_step: Decimal = Decimal("0.000001")


class RiskManager:
    """Minimal long-only risk manager for Spike C."""

    def __init__(self, config: RiskConfig) -> None:
        self._config = config

    def validate(
        self,
        intent: OrderIntent,
        portfolio_state: PortfolioState,
        current_price: Decimal,
    ) -> OrderIntent | None:
        if intent.side == "BUY":
            return self._approve_buy(intent, portfolio_state, current_price)
        return self._approve_sell(intent, portfolio_state)

    def _approve_buy(
        self,
        intent: OrderIntent,
        portfolio_state: PortfolioState,
        current_price: Decimal,
    ) -> OrderIntent | None:
        if intent.symbol in portfolio_state.positions:
            return None
        if len(portfolio_state.positions) >= self._config.max_open_positions:
            return None

        budget = portfolio_state.cash * self._config.risk_per_trade
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
