from datetime import UTC, datetime, timedelta
from decimal import Decimal

from crypto_bot_cxc.ledger.models import PortfolioState
from crypto_bot_cxc.risk import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerReason


def test_circuit_breaker_blocks_after_daily_loss_limit() -> None:
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            daily_loss_limit=Decimal("0.02"),
            max_drawdown=Decimal("0.50"),
            max_consecutive_losses=3,
        )
    )
    state = portfolio_state(realized_pnl=Decimal("0"))
    as_of = datetime(2024, 1, 1, 12, tzinfo=UTC)

    initial_status = breaker.check(
        portfolio_state=state,
        current_equity=Decimal("1000"),
        as_of=as_of,
    )
    assert not initial_status.is_blocked
    status = breaker.check(
        portfolio_state=state,
        current_equity=Decimal("980"),
        as_of=as_of + timedelta(hours=1),
    )

    assert status.is_blocked
    assert status.reason == CircuitBreakerReason.DAILY_LOSS_LIMIT


def test_circuit_breaker_resets_daily_loss_on_new_day() -> None:
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            daily_loss_limit=Decimal("0.02"),
            max_drawdown=Decimal("0.50"),
            max_consecutive_losses=3,
        )
    )
    state = portfolio_state(realized_pnl=Decimal("0"))

    assert not breaker.check(
        portfolio_state=state,
        current_equity=Decimal("1000"),
        as_of=datetime(2024, 1, 1, 22, tzinfo=UTC),
    ).is_blocked
    assert breaker.check(
        portfolio_state=state,
        current_equity=Decimal("980"),
        as_of=datetime(2024, 1, 1, 23, tzinfo=UTC),
    ).is_blocked
    status = breaker.check(
        portfolio_state=state,
        current_equity=Decimal("980"),
        as_of=datetime(2024, 1, 2, tzinfo=UTC),
    )

    assert not status.is_blocked


def test_circuit_breaker_blocks_after_max_drawdown() -> None:
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            daily_loss_limit=Decimal("0.50"),
            max_drawdown=Decimal("0.10"),
            max_consecutive_losses=3,
        )
    )
    state = portfolio_state(realized_pnl=Decimal("0"))

    assert not breaker.check(
        portfolio_state=state,
        current_equity=Decimal("1200"),
        as_of=datetime(2024, 1, 1, tzinfo=UTC),
    ).is_blocked
    status = breaker.check(
        portfolio_state=state,
        current_equity=Decimal("1080"),
        as_of=datetime(2024, 1, 2, tzinfo=UTC),
    )

    assert status.is_blocked
    assert status.reason == CircuitBreakerReason.MAX_DRAWDOWN


def test_circuit_breaker_blocks_after_consecutive_realized_losses() -> None:
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            daily_loss_limit=Decimal("0.50"),
            max_drawdown=Decimal("0.50"),
            max_consecutive_losses=2,
        )
    )
    as_of = datetime(2024, 1, 1, tzinfo=UTC)

    assert not breaker.check(
        portfolio_state=portfolio_state(realized_pnl=Decimal("-1")),
        current_equity=Decimal("1000"),
        as_of=as_of,
    ).is_blocked
    status = breaker.check(
        portfolio_state=portfolio_state(realized_pnl=Decimal("-2")),
        current_equity=Decimal("1000"),
        as_of=as_of + timedelta(hours=1),
    )

    assert status.is_blocked
    assert status.reason == CircuitBreakerReason.CONSECUTIVE_LOSSES


def test_circuit_breaker_resets_consecutive_losses_after_profit() -> None:
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            daily_loss_limit=Decimal("0.50"),
            max_drawdown=Decimal("0.50"),
            max_consecutive_losses=3,
        )
    )
    as_of = datetime(2024, 1, 1, tzinfo=UTC)

    breaker.check(
        portfolio_state=portfolio_state(realized_pnl=Decimal("-1")),
        current_equity=Decimal("1000"),
        as_of=as_of,
    )
    breaker.check(
        portfolio_state=portfolio_state(realized_pnl=Decimal("-2")),
        current_equity=Decimal("1000"),
        as_of=as_of + timedelta(hours=1),
    )
    breaker.check(
        portfolio_state=portfolio_state(realized_pnl=Decimal("5")),
        current_equity=Decimal("1000"),
        as_of=as_of + timedelta(hours=2),
    )
    status = breaker.check(
        portfolio_state=portfolio_state(realized_pnl=Decimal("4")),
        current_equity=Decimal("1000"),
        as_of=as_of + timedelta(hours=3),
    )

    assert breaker.consecutive_losses == 1
    assert not status.is_blocked


def test_circuit_breaker_reset_clears_state() -> None:
    breaker = CircuitBreaker(
        CircuitBreakerConfig(
            daily_loss_limit=Decimal("0.02"),
            max_drawdown=Decimal("0.10"),
            max_consecutive_losses=1,
        )
    )

    assert breaker.check(
        portfolio_state=portfolio_state(realized_pnl=Decimal("-1")),
        current_equity=Decimal("1000"),
        as_of=datetime(2024, 1, 1, tzinfo=UTC),
    ).is_blocked

    breaker.reset()

    assert not breaker.check(
        portfolio_state=portfolio_state(realized_pnl=Decimal("0")),
        current_equity=Decimal("1000"),
        as_of=datetime(2024, 1, 1, tzinfo=UTC),
    ).is_blocked


def portfolio_state(*, realized_pnl: Decimal) -> PortfolioState:
    return PortfolioState(
        cash=Decimal("1000"),
        positions={},
        realized_pnl=realized_pnl,
        fees_paid=Decimal("0"),
    )
