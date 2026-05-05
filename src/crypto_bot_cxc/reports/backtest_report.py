from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

from crypto_bot_cxc.engine import BacktestResult, EquityPoint
from crypto_bot_cxc.events import MarketDataEvent
from crypto_bot_cxc.ledger.models import Trade


@dataclass(frozen=True, slots=True)
class SummaryMetrics:
    trades: int
    final_equity: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal
    total_realized_pnl: Decimal
    total_fees: Decimal
    benchmark_final_equity: Decimal | None = None
    benchmark_return_pct: Decimal | None = None
    benchmark_max_drawdown_pct: Decimal | None = None
    excess_return_pct: Decimal | None = None


def write_backtest_report(
    result: BacktestResult,
    *,
    output_dir: Path,
    initial_cash: Decimal,
    benchmark_events: list[MarketDataEvent] | None = None,
) -> SummaryMetrics:
    output_dir.mkdir(parents=True, exist_ok=True)
    benchmark_curve = _buy_and_hold_curve(benchmark_events, initial_cash=initial_cash)
    summary = summarize(
        result=result,
        initial_cash=initial_cash,
        benchmark_curve=benchmark_curve,
    )

    _write_trades(output_dir / "trades.csv", result.trades)
    _write_equity_curve(output_dir / "equity_curve.csv", result.equity_curve)
    _write_summary(output_dir / "summary.json", summary)
    _write_benchmark_comparison(output_dir / "benchmark_comparison.json", summary)
    _write_monthly_returns(output_dir / "monthly_returns.csv", result.equity_curve)
    _write_regime_performance_placeholder(output_dir / "regime_performance.csv")
    return summary


def summarize(
    result: BacktestResult,
    *,
    initial_cash: Decimal,
    benchmark_curve: list[EquityPoint] | None = None,
) -> SummaryMetrics:
    fees = sum((trade.fee for trade in result.trades), start=Decimal("0"))
    realized = sum((trade.realized_pnl for trade in result.trades), start=Decimal("0"))
    total_return_pct = (result.final_equity / initial_cash - Decimal("1")) * Decimal("100")
    benchmark_final_equity = benchmark_curve[-1].equity if benchmark_curve else None
    benchmark_return_pct = None
    benchmark_max_drawdown_pct = None
    excess_return_pct = None
    if benchmark_final_equity is not None:
        benchmark_return_pct = (
            benchmark_final_equity / initial_cash - Decimal("1")
        ) * Decimal("100")
        benchmark_max_drawdown_pct = _max_drawdown_pct(benchmark_curve or [])
        excess_return_pct = total_return_pct - benchmark_return_pct

    return SummaryMetrics(
        trades=len(result.trades),
        final_equity=result.final_equity,
        total_return_pct=total_return_pct,
        max_drawdown_pct=_max_drawdown_pct(result.equity_curve),
        total_realized_pnl=realized,
        total_fees=fees,
        benchmark_final_equity=benchmark_final_equity,
        benchmark_return_pct=benchmark_return_pct,
        benchmark_max_drawdown_pct=benchmark_max_drawdown_pct,
        excess_return_pct=excess_return_pct,
    )


def _write_trades(path: Path, trades: list[Trade]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "timestamp",
                "symbol",
                "side",
                "quantity",
                "price",
                "fee",
                "realized_pnl",
                "intent_id",
                "fill_id",
            ],
        )
        writer.writeheader()
        for trade in trades:
            writer.writerow(
                {
                    "timestamp": trade.timestamp.isoformat(),
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": str(trade.quantity),
                    "price": str(trade.price),
                    "fee": str(trade.fee),
                    "realized_pnl": str(trade.realized_pnl),
                    "intent_id": str(trade.intent_id),
                    "fill_id": str(trade.fill_id),
                }
            )


def _write_equity_curve(path: Path, equity_curve: list[EquityPoint]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "equity"])
        writer.writeheader()
        for point in equity_curve:
            writer.writerow({"timestamp": point.timestamp.isoformat(), "equity": str(point.equity)})


def _write_summary(path: Path, summary: SummaryMetrics) -> None:
    payload = {key: None if value is None else str(value) for key, value in asdict(summary).items()}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_benchmark_comparison(path: Path, summary: SummaryMetrics) -> None:
    payload = {
        "benchmark": "buy_and_hold",
        "strategy": {
            "final_equity": str(summary.final_equity),
            "return_pct": str(summary.total_return_pct),
            "max_drawdown_pct": str(summary.max_drawdown_pct),
        },
        "benchmark_metrics": {
            "final_equity": _optional_decimal_to_json(summary.benchmark_final_equity),
            "return_pct": _optional_decimal_to_json(summary.benchmark_return_pct),
            "max_drawdown_pct": _optional_decimal_to_json(summary.benchmark_max_drawdown_pct),
        },
        "excess_return_pct": _optional_decimal_to_json(summary.excess_return_pct),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_monthly_returns(path: Path, equity_curve: list[EquityPoint]) -> None:
    if not equity_curve:
        path.write_text("month,return_pct\n", encoding="utf-8")
        return

    first_by_month: dict[str, Decimal] = {}
    last_by_month: dict[str, Decimal] = {}
    for point in equity_curve:
        month = point.timestamp.strftime("%Y-%m")
        first_by_month.setdefault(month, point.equity)
        last_by_month[month] = point.equity

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["month", "return_pct"])
        writer.writeheader()
        for month in sorted(first_by_month):
            start = first_by_month[month]
            end = last_by_month[month]
            return_pct = (end / start - Decimal("1")) * Decimal("100") if start else Decimal("0")
            writer.writerow({"month": month, "return_pct": str(return_pct)})


def _write_regime_performance_placeholder(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "regime",
                "trades",
                "win_rate",
                "avg_pnl",
                "profit_factor",
                "sharpe",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "regime": "INSUFFICIENT_DATA",
                "trades": "0",
                "win_rate": "",
                "avg_pnl": "",
                "profit_factor": "",
                "sharpe": "",
                "notes": "Regime attribution not wired in Spike C pass 2",
            }
        )


def _max_drawdown_pct(equity_curve: list[EquityPoint]) -> Decimal:
    peak: Decimal | None = None
    max_drawdown = Decimal("0")
    for point in equity_curve:
        if peak is None or point.equity > peak:
            peak = point.equity
        if peak and peak > 0:
            drawdown = (peak - point.equity) / peak * Decimal("100")
            max_drawdown = max(max_drawdown, drawdown)
    return max_drawdown


def _buy_and_hold_curve(
    events: list[MarketDataEvent] | None,
    *,
    initial_cash: Decimal,
) -> list[EquityPoint] | None:
    if not events:
        return None
    first_close = events[0].close
    if first_close <= 0:
        return None
    units = initial_cash / first_close
    return [
        EquityPoint(timestamp=event.timestamp, equity=units * event.close)
        for event in events
    ]


def _optional_decimal_to_json(value: Decimal | None) -> str | None:
    return None if value is None else str(value)
