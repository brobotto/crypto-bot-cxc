from datetime import UTC, datetime
from decimal import Decimal

from crypto_bot_cxc.events import OrderIntent
from crypto_bot_cxc.execution.models import Urgency
from crypto_bot_cxc.ledger.models import PortfolioState, Position
from crypto_bot_cxc.regime import RegimeState
from crypto_bot_cxc.risk import RiskConfig, RiskManager


def test_risk_manager_blocks_buy_when_daily_loss_limit_trips() -> None:
    manager = RiskManager(
        RiskConfig(
            risk_per_trade=Decimal("0.10"),
            max_open_positions=1,
            daily_loss_limit=Decimal("0.02"),
            max_drawdown=Decimal("0.50"),
        )
    )
    state = portfolio_state(cash=Decimal("1000"))
    as_of = datetime(2024, 1, 1, tzinfo=UTC)

    assert manager.validate(
        intent=buy_intent(),
        portfolio_state=state,
        current_price=Decimal("100"),
        current_equity=Decimal("1000"),
        as_of=as_of,
    ) is not None

    assert manager.validate(
        intent=buy_intent(),
        portfolio_state=state,
        current_price=Decimal("100"),
        current_equity=Decimal("980"),
        as_of=as_of,
    ) is None


def test_risk_manager_observe_updates_breaker_without_buy_signal() -> None:
    manager = RiskManager(
        RiskConfig(
            risk_per_trade=Decimal("0.10"),
            max_open_positions=1,
            daily_loss_limit=Decimal("0.02"),
            max_drawdown=Decimal("0.50"),
        )
    )
    state = portfolio_state(cash=Decimal("1000"))
    as_of = datetime(2024, 1, 1, tzinfo=UTC)

    manager.observe(portfolio_state=state, current_equity=Decimal("1000"), as_of=as_of)

    assert manager.validate(
        intent=buy_intent(),
        portfolio_state=state,
        current_price=Decimal("100"),
        current_equity=Decimal("980"),
        as_of=as_of,
    ) is None


def test_risk_manager_reset_clears_circuit_breaker_state() -> None:
    manager = RiskManager(
        RiskConfig(
            risk_per_trade=Decimal("0.10"),
            max_open_positions=1,
            daily_loss_limit=Decimal("0.02"),
            max_drawdown=Decimal("0.50"),
        )
    )
    state = portfolio_state(cash=Decimal("1000"))
    as_of = datetime(2024, 1, 1, tzinfo=UTC)

    manager.observe(portfolio_state=state, current_equity=Decimal("1000"), as_of=as_of)
    assert manager.validate(
        intent=buy_intent(),
        portfolio_state=state,
        current_price=Decimal("100"),
        current_equity=Decimal("980"),
        as_of=as_of,
    ) is None

    manager.reset()

    assert manager.validate(
        intent=buy_intent(),
        portfolio_state=state,
        current_price=Decimal("100"),
        current_equity=Decimal("980"),
        as_of=as_of,
    ) is not None


def test_risk_manager_blocks_buy_after_consecutive_losses_but_allows_sell() -> None:
    manager = RiskManager(
        RiskConfig(
            risk_per_trade=Decimal("0.10"),
            max_open_positions=2,
            daily_loss_limit=Decimal("0.50"),
            max_drawdown=Decimal("0.50"),
            max_consecutive_losses=2,
        )
    )
    as_of = datetime(2024, 1, 1, tzinfo=UTC)

    assert manager.validate(
        intent=buy_intent(symbol="ETH/USDT"),
        portfolio_state=portfolio_state(cash=Decimal("1000"), realized_pnl=Decimal("-1")),
        current_price=Decimal("100"),
        current_equity=Decimal("1000"),
        as_of=as_of,
    ) is not None
    assert manager.validate(
        intent=buy_intent(symbol="ETH/USDT"),
        portfolio_state=portfolio_state(cash=Decimal("1000"), realized_pnl=Decimal("-2")),
        current_price=Decimal("100"),
        current_equity=Decimal("1000"),
        as_of=as_of,
    ) is None

    approved_sell = manager.validate(
        intent=sell_intent(),
        portfolio_state=portfolio_state(
            cash=Decimal("1000"),
            realized_pnl=Decimal("-2"),
            position=Position(
                symbol="BTC/USDT",
                quantity=Decimal("0.5"),
                avg_entry_price=Decimal("100"),
                entry_fees_paid=Decimal("0.05"),
            ),
        ),
        current_price=Decimal("100"),
        current_equity=Decimal("1000"),
        as_of=as_of,
    )

    assert approved_sell is not None
    assert approved_sell.quantity == Decimal("0.5")


def test_risk_manager_applies_capital_reserve_to_position_budget() -> None:
    manager = RiskManager(
        RiskConfig(
            risk_per_trade=Decimal("0.10"),
            max_open_positions=1,
            capital_reserve=Decimal("0.40"),
        )
    )

    approved = manager.validate(
        intent=buy_intent(),
        portfolio_state=portfolio_state(cash=Decimal("1000")),
        current_price=Decimal("10"),
        current_equity=Decimal("1000"),
        as_of=datetime(2024, 1, 1, tzinfo=UTC),
    )

    assert approved is not None
    assert approved.quantity == Decimal("6.000000")


def buy_intent(*, symbol: str = "BTC/USDT") -> OrderIntent:
    return OrderIntent(
        strategy_id="test",
        symbol=symbol,
        side="BUY",
        urgency=Urgency.NORMAL,
        reason="test_buy",
        quantity=None,
        limit_price=None,
        stop_price=None,
        deadline=None,
        regime=RegimeState.UPTREND_LOW_VOL,
    )


def sell_intent() -> OrderIntent:
    return OrderIntent(
        strategy_id="test",
        symbol="BTC/USDT",
        side="SELL",
        urgency=Urgency.URGENT_EXIT,
        reason="test_sell",
        quantity=None,
        limit_price=None,
        stop_price=None,
        deadline=None,
        regime=RegimeState.UPTREND_LOW_VOL,
    )


def portfolio_state(
    *,
    cash: Decimal,
    realized_pnl: Decimal = Decimal("0"),
    position: Position | None = None,
) -> PortfolioState:
    positions = {} if position is None else {position.symbol: position}
    return PortfolioState(
        cash=cash,
        positions=positions,
        realized_pnl=realized_pnl,
        fees_paid=Decimal("0"),
    )
