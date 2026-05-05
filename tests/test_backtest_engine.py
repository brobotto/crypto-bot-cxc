from datetime import UTC, datetime, timedelta
from decimal import Decimal

from crypto_bot_cxc.broker import BacktestBroker, BacktestBrokerConfig
from crypto_bot_cxc.engine import BacktestEngine
from crypto_bot_cxc.events import MarketDataEvent
from crypto_bot_cxc.execution.planner import ExecutionPlanner
from crypto_bot_cxc.ledger import PortfolioLedger
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

