import csv
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from crypto_bot_cxc.engine import BacktestResult, EquityPoint
from crypto_bot_cxc.events import MarketDataEvent
from crypto_bot_cxc.ledger.models import Trade
from crypto_bot_cxc.reports import write_backtest_report
from crypto_bot_cxc.reports.backtest_report import _periods_per_year, summarize


def test_write_backtest_report_creates_required_files(tmp_path: Path) -> None:
    trade = Trade(
        fill_id=uuid4(),
        intent_id=uuid4(),
        symbol="BTC/USDT",
        side="SELL",
        quantity=Decimal("1"),
        price=Decimal("110"),
        fee=Decimal("0.11"),
        realized_pnl=Decimal("9.79"),
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
    )
    equity_curve = [
        EquityPoint(timestamp=datetime(2024, 1, 1, tzinfo=UTC), equity=Decimal("1000")),
        EquityPoint(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=1),
            equity=Decimal("1010"),
        ),
    ]
    result = BacktestResult(trades=[trade], equity_curve=equity_curve, final_equity=Decimal("1010"))
    benchmark_events = [
        MarketDataEvent(
            timestamp=equity_curve[0].timestamp,
            symbol="BTC/USDT",
            open=Decimal("100"),
            high=Decimal("100"),
            low=Decimal("100"),
            close=Decimal("100"),
            volume=Decimal("1"),
            timeframe="1h",
            is_closed=True,
        ),
        MarketDataEvent(
            timestamp=equity_curve[1].timestamp,
            symbol="BTC/USDT",
            open=Decimal("120"),
            high=Decimal("120"),
            low=Decimal("120"),
            close=Decimal("120"),
            volume=Decimal("1"),
            timeframe="1h",
            is_closed=True,
        ),
    ]

    summary = write_backtest_report(
        result,
        output_dir=tmp_path,
        initial_cash=Decimal("1000"),
        benchmark_events=benchmark_events,
    )

    assert summary.trades == 1
    assert summary.benchmark_return_pct == Decimal("20.0")
    assert summary.excess_return_pct == Decimal("-19.00")
    assert (tmp_path / "trades.csv").exists()
    assert (tmp_path / "equity_curve.csv").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "benchmark_comparison.json").exists()
    assert (tmp_path / "monthly_returns.csv").exists()
    assert (tmp_path / "regime_performance.csv").exists()

    payload = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert payload["final_equity"] == "1010"
    assert payload["benchmark_return_pct"] == "20.0"
    assert "sharpe_ratio" in payload
    assert "benchmark_sharpe_ratio" in payload

    benchmark_payload = json.loads(
        (tmp_path / "benchmark_comparison.json").read_text(encoding="utf-8")
    )
    assert benchmark_payload["benchmark"] == "buy_and_hold"
    assert benchmark_payload["benchmark_metrics"]["return_pct"] == "20.0"
    assert "sharpe_ratio" in benchmark_payload["strategy"]
    assert "sharpe_ratio" in benchmark_payload["benchmark_metrics"]

    with (tmp_path / "trades.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["realized_pnl"] == "9.79"


def test_summarize_adds_annualized_sharpe_ratio() -> None:
    equity_curve = [
        EquityPoint(timestamp=datetime(2024, 1, 1, tzinfo=UTC), equity=Decimal("1000")),
        EquityPoint(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=1),
            equity=Decimal("1010"),
        ),
        EquityPoint(
            timestamp=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=2),
            equity=Decimal("1005"),
        ),
    ]
    benchmark_curve = [
        EquityPoint(timestamp=equity_curve[0].timestamp, equity=Decimal("1000")),
        EquityPoint(timestamp=equity_curve[1].timestamp, equity=Decimal("990")),
        EquityPoint(timestamp=equity_curve[2].timestamp, equity=Decimal("1015")),
    ]
    result = BacktestResult(trades=[], equity_curve=equity_curve, final_equity=Decimal("1005"))

    summary = summarize(
        result,
        initial_cash=Decimal("1000"),
        benchmark_curve=benchmark_curve,
    )

    assert summary.sharpe_ratio != Decimal("0")
    assert summary.benchmark_sharpe_ratio is not None
    assert summary.benchmark_sharpe_ratio != Decimal("0")


def test_periods_per_year_uses_median_gap() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    equity_curve = [
        EquityPoint(timestamp=start, equity=Decimal("1000")),
        EquityPoint(timestamp=start + timedelta(hours=2), equity=Decimal("1001")),
        EquityPoint(timestamp=start + timedelta(hours=3), equity=Decimal("1002")),
        EquityPoint(timestamp=start + timedelta(hours=4), equity=Decimal("1003")),
    ]

    assert _periods_per_year(equity_curve) == Decimal("8760")
