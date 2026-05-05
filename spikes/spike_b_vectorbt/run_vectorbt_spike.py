from __future__ import annotations

import argparse
import csv
import json
import math
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd
import vectorbt as vbt

from crypto_bot_cxc.data import GapPolicy, load_ohlcv_events
from crypto_bot_cxc.events import MarketDataEvent


def main() -> None:
    args = parse_args()
    events = load_ohlcv_events(
        args.input,
        symbol=args.symbol,
        timeframe=args.timeframe,
        gap_policy=GapPolicy(args.gap_policy),
        max_forward_fill_candles=args.max_forward_fill_candles,
    )
    frame = _events_to_frame(events)
    portfolio = _run_portfolio(
        frame,
        fast_period=args.fast_period,
        slow_period=args.slow_period,
        initial_cash=args.initial_cash,
        fee_rate=args.fee_rate,
        slippage_rate=args.slippage_rate,
        risk_per_trade=args.risk_per_trade,
        timeframe=args.timeframe,
    )
    summary = _summary_payload(
        portfolio=portfolio,
        frame=frame,
        args=args,
        rows=len(events),
        framework="vectorbt",
    )
    benchmark = _benchmark_payload(summary)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_equity_curve(args.output_dir / "equity_curve.csv", portfolio.value())
    _write_trades(args.output_dir / "trades.csv", portfolio.orders.records_readable, args.symbol)
    _write_summary(args.output_dir / "summary.json", summary["metrics"])
    _write_json(args.output_dir / "benchmark_comparison.json", benchmark)
    _write_monthly_returns(args.output_dir / "monthly_returns.csv", portfolio.value())
    _write_regime_performance_placeholder(args.output_dir / "regime_performance.csv")

    sweep = _parameter_sweep(
        frame,
        initial_cash=args.initial_cash,
        fee_rate=args.fee_rate,
        slippage_rate=args.slippage_rate,
        risk_per_trade=args.risk_per_trade,
        timeframe=args.timeframe,
    )
    _write_parameter_sweep(args.parameter_sweep_path, sweep)
    _write_json(args.summary_path, summary)
    _write_json(args.benchmark_path, benchmark)

    metrics = summary["metrics"]
    print(
        "framework=vectorbt "
        f"orders={metrics['trades']} "
        f"final_equity={metrics['final_equity']} "
        f"sharpe={metrics['sharpe_ratio']}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Spike B VectorBT backtest.")
    parser.add_argument("--input", type=Path, required=True, help="CSV or Parquet OHLCV file")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for report files")
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=Path("spikes/spike_b_vectorbt/backtest_summary.json"),
    )
    parser.add_argument(
        "--benchmark-path",
        type=Path,
        default=Path("spikes/spike_b_vectorbt/benchmark_comparison.json"),
    )
    parser.add_argument(
        "--parameter-sweep-path",
        type=Path,
        default=Path("spikes/spike_b_vectorbt/parameter_sweep.csv"),
    )
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--initial-cash", type=float, default=10000.0)
    parser.add_argument("--fast-period", type=int, default=20)
    parser.add_argument("--slow-period", type=int, default=100)
    parser.add_argument("--fee-rate", type=float, default=0.001)
    parser.add_argument("--slippage-rate", type=float, default=0.0005)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument(
        "--gap-policy",
        choices=[policy.value for policy in GapPolicy],
        default=GapPolicy.STRICT.value,
    )
    parser.add_argument("--max-forward-fill-candles", type=int, default=3)
    return parser.parse_args()


def _events_to_frame(events: list[MarketDataEvent]) -> pd.DataFrame:
    rows = [
        {
            "timestamp": event.timestamp,
            "open": float(event.open),
            "high": float(event.high),
            "low": float(event.low),
            "close": float(event.close),
            "volume": float(event.volume),
        }
        for event in events
    ]
    frame = pd.DataFrame(rows).set_index("timestamp")
    frame.index = pd.DatetimeIndex(frame.index)
    return frame


def _run_portfolio(
    frame: pd.DataFrame,
    *,
    fast_period: int,
    slow_period: int,
    initial_cash: float,
    fee_rate: float,
    slippage_rate: float,
    risk_per_trade: float,
    timeframe: str,
) -> vbt.Portfolio:
    entries, exits = _ema_cross_signals(frame["close"], fast_period, slow_period)
    fill_entries = entries.shift(1, fill_value=False)
    fill_exits = exits.shift(1, fill_value=False)
    return vbt.Portfolio.from_signals(
        frame["close"],
        entries=fill_entries,
        exits=fill_exits,
        price=frame["open"],
        open=frame["open"],
        high=frame["high"],
        low=frame["low"],
        init_cash=initial_cash,
        size=risk_per_trade,
        size_type="percent",
        fees=fee_rate,
        slippage=slippage_rate,
        direction="longonly",
        accumulate=False,
        freq=timeframe,
    )


def _ema_cross_signals(
    close: pd.Series,
    fast_period: int,
    slow_period: int,
) -> tuple[pd.Series, pd.Series]:
    fast = close.ewm(span=fast_period, adjust=False).mean()
    slow = close.ewm(span=slow_period, adjust=False).mean()
    samples = pd.Series(range(1, len(close) + 1), index=close.index)
    ready = samples > slow_period
    crossed_up = (fast.shift(1) <= slow.shift(1)) & (fast > slow) & ready
    crossed_down = (fast.shift(1) >= slow.shift(1)) & (fast < slow) & ready
    return crossed_up.fillna(False), crossed_down.fillna(False)


def _summary_payload(
    *,
    portfolio: vbt.Portfolio,
    frame: pd.DataFrame,
    args: argparse.Namespace,
    rows: int,
    framework: str,
) -> dict[str, Any]:
    equity = portfolio.value()
    orders = portfolio.orders.records_readable
    trades = portfolio.trades.records_readable
    benchmark_equity = _buy_and_hold_equity(frame["close"], initial_cash=args.initial_cash)
    metrics = {
        "rows": str(rows),
        "trades": str(len(orders)),
        "final_equity": _fmt(equity.iloc[-1]),
        "total_return_pct": _fmt(_return_pct(equity, args.initial_cash)),
        "max_drawdown_pct": _fmt(_max_drawdown_pct(equity)),
        "sharpe_ratio": _fmt(_sharpe_ratio(equity)),
        "total_realized_pnl": _fmt(_sum_column(trades, "PnL")),
        "total_fees": _fmt(_sum_column(orders, "Fees")),
        "benchmark_final_equity": _fmt(benchmark_equity.iloc[-1]),
        "benchmark_return_pct": _fmt(_return_pct(benchmark_equity, args.initial_cash)),
        "benchmark_max_drawdown_pct": _fmt(_max_drawdown_pct(benchmark_equity)),
        "benchmark_sharpe_ratio": _fmt(_sharpe_ratio(benchmark_equity)),
        "excess_return_pct": _fmt(
            _return_pct(equity, args.initial_cash)
            - _return_pct(benchmark_equity, args.initial_cash)
        ),
    }
    return {
        "framework": framework,
        "vectorbt_version": getattr(vbt, "__version__", "unknown"),
        "pandas_version": pd.__version__,
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "period": f"{frame.index[0].isoformat()}/{frame.index[-1].isoformat()}",
        "strategy": f"EMA {args.fast_period}/{args.slow_period}",
        "capital": _fmt(args.initial_cash),
        "fee_rate": _fmt(args.fee_rate),
        "slippage": _fmt(args.slippage_rate),
        "risk_per_trade": _fmt(args.risk_per_trade),
        "execution": "signals shifted one bar; VectorBT fills at next candle open",
        "sizing": "VectorBT percent sizing; approximately 1% of cash/equity per entry",
        "gap_policy": args.gap_policy,
        "max_forward_fill_candles": str(args.max_forward_fill_candles),
        "metrics": metrics,
    }


def _benchmark_payload(summary: dict[str, Any]) -> dict[str, Any]:
    metrics = summary["metrics"]
    return {
        "benchmark": "buy_and_hold",
        "strategy": {
            "final_equity": metrics["final_equity"],
            "return_pct": metrics["total_return_pct"],
            "max_drawdown_pct": metrics["max_drawdown_pct"],
            "sharpe_ratio": metrics["sharpe_ratio"],
        },
        "benchmark_metrics": {
            "final_equity": metrics["benchmark_final_equity"],
            "return_pct": metrics["benchmark_return_pct"],
            "max_drawdown_pct": metrics["benchmark_max_drawdown_pct"],
            "sharpe_ratio": metrics["benchmark_sharpe_ratio"],
        },
        "excess_return_pct": metrics["excess_return_pct"],
    }


def _parameter_sweep(
    frame: pd.DataFrame,
    *,
    initial_cash: float,
    fee_rate: float,
    slippage_rate: float,
    risk_per_trade: float,
    timeframe: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for fast_period in (10, 20, 30):
        for slow_period in (50, 100, 200):
            if fast_period >= slow_period:
                continue
            portfolio = _run_portfolio(
                frame,
                fast_period=fast_period,
                slow_period=slow_period,
                initial_cash=initial_cash,
                fee_rate=fee_rate,
                slippage_rate=slippage_rate,
                risk_per_trade=risk_per_trade,
                timeframe=timeframe,
            )
            equity = portfolio.value()
            rows.append(
                {
                    "fast_period": str(fast_period),
                    "slow_period": str(slow_period),
                    "orders": str(len(portfolio.orders.records_readable)),
                    "final_equity": _fmt(equity.iloc[-1]),
                    "total_return_pct": _fmt(_return_pct(equity, initial_cash)),
                    "max_drawdown_pct": _fmt(_max_drawdown_pct(equity)),
                    "sharpe_ratio": _fmt(_sharpe_ratio(equity)),
                }
            )
    return rows


def _write_equity_curve(path: Path, equity: pd.Series) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "equity"])
        writer.writeheader()
        for timestamp, value in equity.items():
            writer.writerow({"timestamp": timestamp.isoformat(), "equity": _fmt(value)})


def _write_trades(path: Path, orders: pd.DataFrame, symbol: str) -> None:
    fieldnames = [
        "timestamp",
        "symbol",
        "side",
        "quantity",
        "price",
        "fee",
        "realized_pnl",
        "intent_id",
        "fill_id",
    ]
    position_qty = Decimal("0")
    avg_entry = Decimal("0")
    entry_fees = Decimal("0")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in orders.to_dict(orient="records"):
            side = str(row["Side"]).upper()
            quantity = Decimal(str(row["Size"]))
            price = Decimal(str(row["Price"]))
            fee = Decimal(str(row["Fees"]))
            realized_pnl = Decimal("0")
            if side == "BUY":
                notional = position_qty * avg_entry + quantity * price
                position_qty += quantity
                avg_entry = notional / position_qty if position_qty > 0 else Decimal("0")
                entry_fees += fee
            elif position_qty > 0:
                exit_quantity = min(quantity, position_qty)
                entry_fee_portion = (entry_fees * exit_quantity) / position_qty
                realized_pnl = (price - avg_entry) * exit_quantity - fee - entry_fee_portion
                position_qty -= exit_quantity
                entry_fees -= entry_fee_portion
                if position_qty <= 0:
                    avg_entry = Decimal("0")
                    entry_fees = Decimal("0")

            writer.writerow(
                {
                    "timestamp": row["Timestamp"].isoformat(),
                    "symbol": symbol,
                    "side": side,
                    "quantity": str(quantity),
                    "price": str(price),
                    "fee": str(fee),
                    "realized_pnl": str(realized_pnl),
                    "intent_id": "",
                    "fill_id": str(row["Order Id"]),
                }
            )


def _write_summary(path: Path, metrics: dict[str, str]) -> None:
    _write_json(path, metrics)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_monthly_returns(path: Path, equity: pd.Series) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["month", "return_pct"])
        writer.writeheader()
        for month, values in equity.groupby(equity.index.strftime("%Y-%m")):
            start = values.iloc[0]
            end = values.iloc[-1]
            return_pct = (end / start - 1.0) * 100.0 if start > 0 else 0.0
            writer.writerow({"month": month, "return_pct": _fmt(return_pct)})


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
                "notes": "Regime attribution not part of Spike B VectorBT comparison",
            }
        )


def _write_parameter_sweep(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "fast_period",
            "slow_period",
            "orders",
            "final_equity",
            "total_return_pct",
            "max_drawdown_pct",
            "sharpe_ratio",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _buy_and_hold_equity(close: pd.Series, *, initial_cash: float) -> pd.Series:
    units = initial_cash / close.iloc[0]
    return close * units


def _return_pct(equity: pd.Series, initial_cash: float) -> float:
    return (float(equity.iloc[-1]) / initial_cash - 1.0) * 100.0


def _max_drawdown_pct(equity: pd.Series) -> float:
    peak = equity.cummax()
    drawdown = (peak - equity) / peak * 100.0
    return float(drawdown.max())


def _sharpe_ratio(equity: pd.Series) -> float:
    returns = equity.pct_change().dropna()
    if returns.empty:
        return 0.0
    std = float(returns.std(ddof=0))
    if std == 0.0:
        return 0.0
    return float(returns.mean()) / std * math.sqrt(_periods_per_year(equity))


def _periods_per_year(equity: pd.Series) -> float:
    index = equity.index
    gaps: list[float] = []
    for previous, current in zip(index, index[1:], strict=False):
        seconds = (current - previous).total_seconds()
        if seconds > 0:
            gaps.append(float(seconds))
        if len(gaps) >= 100:
            break
    median_gap = _median(gaps)
    return 31_536_000 / median_gap if median_gap > 0 else 0.0


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _sum_column(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return 0.0
    return float(frame[column].sum())


def _fmt(value: float | int | str) -> str:
    if isinstance(value, str):
        return value
    decimal_value = Decimal(str(value))
    return format(decimal_value, "f")


if __name__ == "__main__":
    main()
