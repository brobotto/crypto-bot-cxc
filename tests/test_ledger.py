from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

import pytest

from crypto_bot_cxc.events import FillEvent
from crypto_bot_cxc.ledger import PortfolioLedger


def fill(side: Literal["BUY", "SELL"], quantity: str, price: str, fee: str) -> FillEvent:
    return FillEvent(
        order_id=uuid4(),
        intent_id=uuid4(),
        symbol="BTC/USDT",
        side=side,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fee=Decimal(fee),
        fee_currency="USDT",
        filled_at=datetime(2024, 1, 1, tzinfo=UTC),
        is_partial=False,
    )


def test_round_trip_cash_and_realized_pnl_include_entry_and_exit_fees() -> None:
    ledger = PortfolioLedger(initial_cash=Decimal("1000"))

    ledger.on_fill(fill("BUY", "1", "100", "0.10"))
    buy_state = ledger.get_state()

    assert buy_state.cash == Decimal("899.90")
    assert buy_state.positions["BTC/USDT"].quantity == Decimal("1")
    assert buy_state.positions["BTC/USDT"].entry_fees_paid == Decimal("0.10")

    ledger.on_fill(fill("SELL", "1", "110", "0.11"))
    sell_state = ledger.get_state()

    assert sell_state.cash == Decimal("1009.79")
    assert sell_state.realized_pnl == Decimal("9.79")
    assert "BTC/USDT" not in sell_state.positions


def test_partial_sell_prorates_entry_fee_and_keeps_remaining_position() -> None:
    ledger = PortfolioLedger(initial_cash=Decimal("1000"))

    ledger.on_fill(fill("BUY", "3", "10", "0.03"))
    ledger.on_fill(fill("SELL", "1", "12", "0.01"))
    state = ledger.get_state()

    position = state.positions["BTC/USDT"]
    assert position.quantity == Decimal("2")
    assert position.avg_entry_price == Decimal("10")
    assert position.entry_fees_paid == Decimal("0.02")
    assert state.realized_pnl == Decimal("1.98")


def test_buy_rejects_negative_cash_state() -> None:
    ledger = PortfolioLedger(initial_cash=Decimal("100"))

    with pytest.raises(ValueError, match="cash went negative"):
        ledger.on_fill(fill("BUY", "2", "100", "0"))
