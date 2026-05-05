from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from crypto_bot_cxc.events.models import FillEvent
from crypto_bot_cxc.ledger.models import PortfolioState, Position, Trade


class PortfolioLedger:
    """Append-only fill consumer and current portfolio state for Spike C."""

    def __init__(self, initial_cash: Decimal) -> None:
        if initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        self._state = PortfolioState(
            cash=initial_cash,
            positions={},
            realized_pnl=Decimal("0"),
            fees_paid=Decimal("0"),
        )
        self._trades: list[Trade] = []

    @property
    def trades(self) -> list[Trade]:
        return list(self._trades)

    def get_state(self) -> PortfolioState:
        return replace(self._state, positions=dict(self._state.positions))

    def position_quantity(self, symbol: str) -> Decimal:
        position = self._state.positions.get(symbol)
        return position.quantity if position else Decimal("0")

    def on_fill(self, fill: FillEvent) -> PortfolioState:
        if fill.side == "BUY":
            trade = self._apply_buy(fill)
        else:
            trade = self._apply_sell(fill)

        self._trades.append(trade)
        return self.get_state()

    def equity(self, prices: dict[str, Decimal]) -> Decimal:
        equity = self._state.cash
        for symbol, position in self._state.positions.items():
            equity += position.quantity * prices[symbol]
        return equity

    def _apply_buy(self, fill: FillEvent) -> Trade:
        notional = fill.quantity * fill.price
        current = self._state.positions.get(fill.symbol)
        if current is None:
            position = Position(
                symbol=fill.symbol,
                quantity=fill.quantity,
                avg_entry_price=fill.price,
                entry_fees_paid=fill.fee,
            )
        else:
            new_qty = current.quantity + fill.quantity
            avg_entry = (
                current.avg_entry_price * current.quantity + fill.price * fill.quantity
            ) / new_qty
            position = Position(
                symbol=fill.symbol,
                quantity=new_qty,
                avg_entry_price=avg_entry,
                entry_fees_paid=current.entry_fees_paid + fill.fee,
            )

        positions = dict(self._state.positions)
        positions[fill.symbol] = position
        self._state = PortfolioState(
            cash=self._state.cash - notional - fill.fee,
            positions=positions,
            realized_pnl=self._state.realized_pnl,
            fees_paid=self._state.fees_paid + fill.fee,
        )
        return Trade(
            fill_id=fill.order_id,
            intent_id=fill.intent_id,
            symbol=fill.symbol,
            side=fill.side,
            quantity=fill.quantity,
            price=fill.price,
            fee=fill.fee,
            realized_pnl=Decimal("0"),
            timestamp=fill.filled_at,
        )

    def _apply_sell(self, fill: FillEvent) -> Trade:
        current = self._state.positions.get(fill.symbol)
        if current is None or current.quantity < fill.quantity:
            raise ValueError("cannot sell more than current long-only position")

        notional = fill.quantity * fill.price
        entry_fee_portion = current.entry_fees_paid * (fill.quantity / current.quantity)
        realized_pnl = (fill.price - current.avg_entry_price) * fill.quantity
        realized_pnl -= fill.fee + entry_fee_portion
        remaining_qty = current.quantity - fill.quantity
        positions = dict(self._state.positions)
        if remaining_qty == 0:
            del positions[fill.symbol]
        else:
            positions[fill.symbol] = Position(
                symbol=fill.symbol,
                quantity=remaining_qty,
                avg_entry_price=current.avg_entry_price,
                entry_fees_paid=current.entry_fees_paid - entry_fee_portion,
            )

        self._state = PortfolioState(
            cash=self._state.cash + notional - fill.fee,
            positions=positions,
            realized_pnl=self._state.realized_pnl + realized_pnl,
            fees_paid=self._state.fees_paid + fill.fee,
        )
        return Trade(
            fill_id=fill.order_id,
            intent_id=fill.intent_id,
            symbol=fill.symbol,
            side=fill.side,
            quantity=fill.quantity,
            price=fill.price,
            fee=fill.fee,
            realized_pnl=realized_pnl,
            timestamp=fill.filled_at,
        )
