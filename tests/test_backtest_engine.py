from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from crypto_bot_cxc.broker import BacktestBroker, BacktestBrokerConfig
from crypto_bot_cxc.engine import BacktestEngine
from crypto_bot_cxc.events import MarketDataEvent
from crypto_bot_cxc.execution.planner import ExecutionPlanner
from crypto_bot_cxc.ledger import PortfolioLedger
from crypto_bot_cxc.regime import RegimeState
from crypto_bot_cxc.risk import RiskConfig, RiskManager
from crypto_bot_cxc.strategy import EMATrendConfig, EMATrendStrategy


def make_candles(closes: list[str], opens: list[str]) -> list[MarketDataEvent]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    candles: list[MarketDataEvent] = []
    for idx, (close, open_price) in enumerate(zip(closes, opens, strict=True)):
        event = MarketDataEvent(
            timestamp=start + timedelta(hours=idx),
            symbol="BTC/USDT",
            open=Decimal(open_price),
            high=max(Decimal(open_price), Decimal(close)) + Decimal("5"),
            low=min(Decimal(open_price), Decimal(close)) - Decimal("5"),
            close=Decimal(close),
            volume=Decimal("100"),
            timeframe="1h",
            is_closed=True,
        )
        candles.append(event)
    return candles


def test_engine_fills_after_signal_candle_not_on_signal_candle() -> None:
    candles = make_candles(
        closes=["100", "90", "80", "120", "130", "70", "60"],
        opens=["100", "90", "80", "120", "125", "70", "65"],
    )
    broker = BacktestBroker(
        BacktestBrokerConfig(fee_rate=Decimal("0.001"), slippage_rate=Decimal("0"))
    )
    ledger = PortfolioLedger(initial_cash=Decimal("10000"))
    engine = BacktestEngine(
        strategy=EMATrendStrategy(EMATrendConfig(fast_period=2, slow_period=4)),
        risk_manager=RiskManager(
            RiskConfig(
                risk_per_trade=Decimal("0.10"),
                max_open_positions=1,
                min_order_notional=Decimal("10"),
            )
        ),
        planner=ExecutionPlanner(),
        broker=broker,
        ledger=ledger,
        regime_provider=lambda _event: RegimeState.UPTREND_LOW_VOL,
        warmup_period=1,
    )

    result = engine.run(candles)

    assert len(result.trades) == 2
    assert result.trades[0].side == "BUY"
    assert result.trades[0].timestamp == candles[4].timestamp
    assert result.trades[0].price == Decimal("125")
    assert result.trades[1].side == "SELL"
    assert result.trades[1].timestamp == candles[6].timestamp
    assert result.trades[1].price == Decimal("65")
    assert len(result.feature_snapshots) == len(candles)
    assert len(result.regime_curve) == len(candles)
    assert result.trade_regimes[result.trades[0].intent_id] == RegimeState.UPTREND_LOW_VOL
    assert result.trade_regimes[result.trades[1].intent_id] == RegimeState.UPTREND_LOW_VOL


def test_engine_rejects_non_positive_warmup_period() -> None:
    with pytest.raises(ValueError, match="warmup_period"):
        BacktestEngine(
            strategy=EMATrendStrategy(EMATrendConfig(fast_period=2, slow_period=4)),
            risk_manager=RiskManager(
                RiskConfig(
                    risk_per_trade=Decimal("0.10"),
                    max_open_positions=1,
                    min_order_notional=Decimal("10"),
                )
            ),
            planner=ExecutionPlanner(),
            broker=BacktestBroker(
                BacktestBrokerConfig(fee_rate=Decimal("0.001"), slippage_rate=Decimal("0"))
            ),
            ledger=PortfolioLedger(initial_cash=Decimal("10000")),
            regime_provider=lambda _event: RegimeState.UPTREND_LOW_VOL,
            warmup_period=0,
        )


def test_engine_empty_candle_list_returns_initial_cash() -> None:
    ledger = PortfolioLedger(initial_cash=Decimal("10000"))
    engine = BacktestEngine(
        strategy=EMATrendStrategy(EMATrendConfig(fast_period=2, slow_period=4)),
        risk_manager=RiskManager(
            RiskConfig(
                risk_per_trade=Decimal("0.10"),
                max_open_positions=1,
                min_order_notional=Decimal("10"),
            )
        ),
        planner=ExecutionPlanner(),
        broker=BacktestBroker(
            BacktestBrokerConfig(fee_rate=Decimal("0.001"), slippage_rate=Decimal("0"))
        ),
        ledger=ledger,
        regime_provider=lambda _event: RegimeState.UPTREND_LOW_VOL,
        warmup_period=1,
    )

    result = engine.run([])

    assert result.trades == []
    assert result.equity_curve == []
    assert result.final_equity == Decimal("10000")


def test_engine_resets_risk_manager_between_runs() -> None:
    candles = make_candles(
        closes=["100", "90", "80", "120", "130", "70", "60"],
        opens=["100", "90", "80", "120", "125", "70", "65"],
    )
    risk_manager = RiskManager(
        RiskConfig(
            risk_per_trade=Decimal("0.10"),
            max_open_positions=1,
            daily_loss_limit=Decimal("0.02"),
            max_drawdown=Decimal("0.10"),
            min_order_notional=Decimal("10"),
        )
    )

    def build_engine() -> BacktestEngine:
        return BacktestEngine(
            strategy=EMATrendStrategy(EMATrendConfig(fast_period=2, slow_period=4)),
            risk_manager=risk_manager,
            planner=ExecutionPlanner(),
            broker=BacktestBroker(
                BacktestBrokerConfig(fee_rate=Decimal("0.001"), slippage_rate=Decimal("0"))
            ),
            ledger=PortfolioLedger(initial_cash=Decimal("10000")),
            regime_provider=lambda _event: RegimeState.UPTREND_LOW_VOL,
            warmup_period=1,
        )

    first_result = build_engine().run(candles)
    second_result = build_engine().run(candles)

    assert len(first_result.trades) == 2
    assert len(second_result.trades) == 2
