from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from crypto_bot_cxc.engine import BacktestResult, EquityPoint
from crypto_bot_cxc.events import MarketDataEvent
from crypto_bot_cxc.ledger.models import Trade
from crypto_bot_cxc.regime.models import RegimeState


@dataclass(frozen=True, slots=True)
class SummaryMetrics:
    trades: int
    final_equity: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal
    sharpe_ratio: Decimal
    total_realized_pnl: Decimal
    total_fees: Decimal
    benchmark_final_equity: Decimal | None = None
    benchmark_return_pct: Decimal | None = None
    benchmark_max_drawdown_pct: Decimal | None = None
    benchmark_sharpe_ratio: Decimal | None = None
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

    _write_trades(output_dir / "trades.csv", result.trades, result.trade_regimes)
    _write_equity_curve(output_dir / "equity_curve.csv", result.equity_curve)
    _write_summary(output_dir / "summary.json", summary)
    _write_benchmark_comparison(output_dir / "benchmark_comparison.json", summary)
    _write_monthly_returns(output_dir / "monthly_returns.csv", result.equity_curve)
    _write_regime_performance(
        output_dir / "regime_performance.csv",
        result.trades,
        result.trade_regimes,
    )
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
    benchmark_sharpe_ratio = None
    excess_return_pct = None
    if benchmark_final_equity is not None:
        benchmark_return_pct = (
            benchmark_final_equity / initial_cash - Decimal("1")
        ) * Decimal("100")
        benchmark_max_drawdown_pct = _max_drawdown_pct(benchmark_curve or [])
        benchmark_sharpe_ratio = _sharpe_ratio(benchmark_curve or [])
        excess_return_pct = total_return_pct - benchmark_return_pct

    return SummaryMetrics(
        trades=len(result.trades),
        final_equity=result.final_equity,
        total_return_pct=total_return_pct,
        max_drawdown_pct=_max_drawdown_pct(result.equity_curve),
        sharpe_ratio=_sharpe_ratio(result.equity_curve),
        total_realized_pnl=realized,
        total_fees=fees,
        benchmark_final_equity=benchmark_final_equity,
        benchmark_return_pct=benchmark_return_pct,
        benchmark_max_drawdown_pct=benchmark_max_drawdown_pct,
        benchmark_sharpe_ratio=benchmark_sharpe_ratio,
        excess_return_pct=excess_return_pct,
    )


def _write_trades(
    path: Path,
    trades: list[Trade],
    trade_regimes: dict[UUID, RegimeState],
) -> None:
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
                "regime",
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
                    "regime": _regime_to_csv(trade_regimes.get(trade.intent_id)),
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
            "sharpe_ratio": str(summary.sharpe_ratio),
        },
        "benchmark_metrics": {
            "final_equity": _optional_decimal_to_json(summary.benchmark_final_equity),
            "return_pct": _optional_decimal_to_json(summary.benchmark_return_pct),
            "max_drawdown_pct": _optional_decimal_to_json(summary.benchmark_max_drawdown_pct),
            "sharpe_ratio": _optional_decimal_to_json(summary.benchmark_sharpe_ratio),
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
            return_pct = (
                (end / start - Decimal("1")) * Decimal("100") if start > 0 else Decimal("0")
            )
            writer.writerow({"month": month, "return_pct": str(return_pct)})


def _write_regime_performance(
    path: Path,
    trades: list[Trade],
    trade_regimes: dict[UUID, RegimeState],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "regime",
                "trades",
                "win_rate",
                "avg_pnl",
                "profit_factor",
                "trade_sharpe",
                "notes",
            ],
        )
        writer.writeheader()
        groups = _closed_trade_pnls_by_regime(trades, trade_regimes)
        if not groups:
            writer.writerow(
                {
                    "regime": "INSUFFICIENT_DATA",
                    "trades": "0",
                    "win_rate": "",
                    "avg_pnl": "",
                    "profit_factor": "",
                    "trade_sharpe": "",
                    "notes": "No closed trades with regime attribution yet",
                }
            )
            return

        for regime in sorted(groups):
            pnls = groups[regime]
            writer.writerow(
                {
                    "regime": regime,
                    "trades": str(len(pnls)),
                    "win_rate": str(_win_rate_pct(pnls)),
                    "avg_pnl": str(_average_pnl(pnls)),
                    "profit_factor": _profit_factor_to_csv(pnls),
                    "trade_sharpe": str(_trade_pnl_sharpe(pnls)),
                    "notes": "insufficient_sample" if len(pnls) < 20 else "",
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


def _sharpe_ratio(equity_curve: list[EquityPoint]) -> Decimal:
    if len(equity_curve) < 2:
        return Decimal("0")

    returns: list[Decimal] = []
    for previous, current in zip(equity_curve, equity_curve[1:], strict=False):
        if previous.equity <= 0:
            return Decimal("0")
        returns.append(current.equity / previous.equity - Decimal("1"))

    if not returns:
        return Decimal("0")
    mean_return = sum(returns, start=Decimal("0")) / Decimal(len(returns))
    variance = (
        sum(((period_return - mean_return) ** 2 for period_return in returns), start=Decimal("0"))
        / Decimal(len(returns))
    )
    if variance == 0:
        return Decimal("0")
    periods_per_year = _periods_per_year(equity_curve)
    if periods_per_year <= 0:
        return Decimal("0")
    return mean_return / variance.sqrt() * periods_per_year.sqrt()


def _periods_per_year(equity_curve: list[EquityPoint]) -> Decimal:
    seconds_per_year = Decimal("31536000")
    gaps: list[Decimal] = []
    for previous, current in zip(equity_curve, equity_curve[1:], strict=False):
        period_seconds = (current.timestamp - previous.timestamp).total_seconds()
        if period_seconds > 0:
            gaps.append(Decimal(str(period_seconds)))
        if len(gaps) >= 100:
            break
    median_gap = _median(gaps)
    return seconds_per_year / median_gap if median_gap > 0 else Decimal("0")


def _median(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal("2")


def _closed_trade_pnls_by_regime(
    trades: list[Trade],
    trade_regimes: dict[UUID, RegimeState],
) -> dict[str, list[Decimal]]:
    groups: dict[str, list[Decimal]] = {}
    for trade in trades:
        if trade.side != "SELL":
            continue
        regime = trade_regimes.get(trade.intent_id)
        if regime is None:
            continue
        groups.setdefault(regime.value, []).append(trade.realized_pnl)
    return groups


def _win_rate_pct(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    wins = sum(1 for value in values if value > 0)
    return Decimal(wins) / Decimal(len(values)) * Decimal("100")


def _average_pnl(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, start=Decimal("0")) / Decimal(len(values))


def _profit_factor_to_csv(values: list[Decimal]) -> str:
    gross_profit = sum((value for value in values if value > 0), start=Decimal("0"))
    gross_loss = abs(sum((value for value in values if value < 0), start=Decimal("0")))
    if gross_loss == 0:
        return "inf" if gross_profit > 0 else "0"
    return str(gross_profit / gross_loss)


def _trade_pnl_sharpe(values: list[Decimal]) -> Decimal:
    if len(values) < 2:
        return Decimal("0")
    mean_value = _average_pnl(values)
    variance = (
        sum(((value - mean_value) ** 2 for value in values), start=Decimal("0"))
        / Decimal(len(values))
    )
    if variance == 0:
        return Decimal("0")
    return mean_value / variance.sqrt()


def _regime_to_csv(regime: RegimeState | None) -> str:
    return "" if regime is None else regime.value


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
