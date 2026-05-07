from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import nautilus_trader
import pandas as pd
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.backtest.models import FillModel
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import Bar, BarType, TradeTick
from nautilus_trader.model.enums import AccountType, AggressorSide, OmsType, OrderSide
from nautilus_trader.model.identifiers import TradeId, Venue
from nautilus_trader.model.objects import Money, Price, Quantity
from nautilus_trader.test_kit.providers import TestInstrumentProvider
from strategies.ema_cross_next_open import EmaCrossNextOpen, EmaCrossNextOpenConfig

from crypto_bot_cxc.data import GapPolicy, load_ohlcv_events
from crypto_bot_cxc.events import MarketDataEvent

HOUR_NANOS = 3_600_000_000_000
VENUE = Venue("BINANCE")


@dataclass(frozen=True, slots=True)
class FillRow:
    timestamp: pd.Timestamp
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    fee: Decimal
    realized_pnl: Decimal
    fill_id: str


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
    engine = _run_nautilus(events=events, args=args)
    orders = list(engine.cache.orders())
    fills = _fills_from_orders(
        orders=orders,
        symbol=args.symbol,
        fee_rate=args.fee_rate,
        # Assumes queued orders are submitted exactly on the synthetic bar ts_event
        # at candle_open + HOUR - 1; this normalizes report time back to candle open.
        execution_timestamp_offset_ns=-HOUR_NANOS + 1,
    )
    equity = _equity_from_fills(
        events=events,
        fills=fills,
        initial_cash=args.initial_cash,
    )
    benchmark_equity = _buy_and_hold_equity(frame["close"], initial_cash=args.initial_cash)
    summary = _summary_payload(
        args=args,
        frame=frame,
        rows=len(events),
        engine=engine,
        fills=fills,
        equity=equity,
        benchmark_equity=benchmark_equity,
    )
    benchmark = _benchmark_payload(summary)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_equity_curve(args.output_dir / "equity_curve.csv", equity)
    _write_trades(args.output_dir / "trades.csv", fills)
    _write_summary(args.output_dir / "summary.json", summary["metrics"])
    _write_json(args.output_dir / "benchmark_comparison.json", benchmark)
    _write_monthly_returns(args.output_dir / "monthly_returns.csv", equity)
    _write_regime_performance_placeholder(args.output_dir / "regime_performance.csv")

    _write_json(args.summary_path, summary)
    _write_json(args.benchmark_path, benchmark)
    metrics = summary["metrics"]
    print(
        "framework=nautilus "
        f"orders={metrics['trades']} "
        f"final_equity={metrics['final_equity']} "
        f"sharpe={metrics['sharpe_ratio']}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Spike D NautilusTrader backtest.")
    parser.add_argument("--input", type=Path, required=True, help="CSV or Parquet OHLCV file")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for report files")
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=Path("spikes/spike_d_nautilus/backtest_summary.json"),
    )
    parser.add_argument(
        "--benchmark-path",
        type=Path,
        default=Path("spikes/spike_d_nautilus/benchmark_comparison.json"),
    )
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--initial-cash", type=float, default=10000.0)
    parser.add_argument("--fast-period", type=int, default=20)
    parser.add_argument("--slow-period", type=int, default=100)
    parser.add_argument("--fee-rate", type=float, default=0.001)
    parser.add_argument("--risk-per-trade", type=float, default=0.01)
    parser.add_argument(
        "--gap-policy",
        choices=[policy.value for policy in GapPolicy],
        default=GapPolicy.STRICT.value,
    )
    parser.add_argument("--max-forward-fill-candles", type=int, default=3)
    return parser.parse_args()


def _run_nautilus(*, events: list[MarketDataEvent], args: argparse.Namespace) -> BacktestEngine:
    instrument = TestInstrumentProvider.btcusdt_binance()
    bar_type = BarType.from_str(f"{instrument.id}-1-HOUR-LAST-EXTERNAL")
    data = _events_to_nautilus_data(events=events, bar_type=bar_type)
    engine = BacktestEngine(
        config=BacktestEngineConfig(
            logging=LoggingConfig(log_level="ERROR", bypass_logging=True),
        ),
    )
    engine.add_venue(
        venue=VENUE,
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        starting_balances=[Money(args.initial_cash, USDT)],
        base_currency=None,
        fill_model=FillModel(),
        bar_execution=False,
        trade_execution=True,
    )
    engine.add_instrument(instrument)
    engine.add_strategy(
        EmaCrossNextOpen(
            EmaCrossNextOpenConfig(
                instrument_id=instrument.id,
                bar_type=bar_type,
                fast_period=args.fast_period,
                slow_period=args.slow_period,
                risk_fraction=args.risk_per_trade,
            ),
        ),
    )
    engine.add_data(data)
    engine.run()
    return engine


def _events_to_nautilus_data(
    *,
    events: list[MarketDataEvent],
    bar_type: BarType,
) -> list[Any]:
    data: list[Any] = []
    instrument_id = bar_type.instrument_id
    for index, event in enumerate(events):
        open_ns = _timestamp_to_ns(event.timestamp)
        data.append(
            TradeTick(
                instrument_id=instrument_id,
                price=Price(float(event.open), precision=2),
                size=Quantity(max(float(event.volume), 0.000001), precision=6),
                aggressor_side=AggressorSide.NO_AGGRESSOR,
                trade_id=TradeId(f"T-{index:06d}"),
                ts_event=open_ns,
                ts_init=open_ns,
            ),
        )
        bar_ns = open_ns + HOUR_NANOS - 1
        data.append(
            Bar(
                bar_type=bar_type,
                open=Price(float(event.open), precision=2),
                high=Price(float(event.high), precision=2),
                low=Price(float(event.low), precision=2),
                close=Price(float(event.close), precision=2),
                volume=Quantity(float(event.volume), precision=6),
                ts_event=bar_ns,
                ts_init=bar_ns,
            ),
        )
    return data


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


def _fills_from_orders(
    *,
    orders: list[Any],
    symbol: str,
    fee_rate: float,
    execution_timestamp_offset_ns: int,
) -> list[FillRow]:
    rows: list[FillRow] = []
    position_qty = Decimal("0")
    avg_entry = Decimal("0")
    entry_fees = Decimal("0")
    for order in orders:
        quantity = Decimal(str(float(order.filled_qty)))
        price = Decimal(str(float(order.avg_px)))
        fee = quantity * price * Decimal(str(fee_rate))
        side = "BUY" if order.side == OrderSide.BUY else "SELL"
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

        rows.append(
            FillRow(
                timestamp=pd.Timestamp(
                    order.ts_init + execution_timestamp_offset_ns,
                    unit="ns",
                    tz="UTC",
                ),
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                fee=fee,
                realized_pnl=realized_pnl,
                fill_id=str(order.client_order_id),
            ),
        )
    return rows


def _equity_from_fills(
    *,
    events: list[MarketDataEvent],
    fills: list[FillRow],
    initial_cash: float,
) -> pd.Series:
    cash = Decimal(str(initial_cash))
    position_qty = Decimal("0")
    values: list[float] = []
    index: list[pd.Timestamp] = []
    sorted_fills = sorted(fills, key=lambda fill: fill.timestamp)
    fill_index = 0
    for event in events:
        timestamp = pd.Timestamp(event.timestamp)
        while fill_index < len(sorted_fills) and sorted_fills[fill_index].timestamp <= timestamp:
            fill = sorted_fills[fill_index]
            notional = fill.quantity * fill.price
            if fill.side == "BUY":
                cash -= notional + fill.fee
                position_qty += fill.quantity
            else:
                sell_quantity = min(fill.quantity, position_qty)
                cash += sell_quantity * fill.price - fill.fee
                position_qty -= sell_quantity
            fill_index += 1
        equity = cash + position_qty * event.close
        values.append(float(equity))
        index.append(timestamp)
    return pd.Series(values, index=pd.DatetimeIndex(index))


def _summary_payload(
    *,
    args: argparse.Namespace,
    frame: pd.DataFrame,
    rows: int,
    engine: BacktestEngine,
    fills: list[FillRow],
    equity: pd.Series,
    benchmark_equity: pd.Series,
) -> dict[str, Any]:
    result = engine.get_result()
    metrics = {
        "rows": str(rows),
        "trades": str(len(fills)),
        "closed_trades": str(len(fills) // 2),
        "final_equity": _fmt(equity.iloc[-1]),
        "engine_final_equity": _fmt(args.initial_cash + _engine_total_pnl(result)),
        "total_return_pct": _fmt(_return_pct(equity, args.initial_cash)),
        "max_drawdown_pct": _fmt(_max_drawdown_pct(equity)),
        "sharpe_ratio": _fmt(_sharpe_ratio(equity)),
        "total_realized_pnl": _fmt(sum((float(fill.realized_pnl) for fill in fills), 0.0)),
        "total_fees": _fmt(sum((float(fill.fee) for fill in fills), 0.0)),
        "benchmark_final_equity": _fmt(benchmark_equity.iloc[-1]),
        "benchmark_return_pct": _fmt(_return_pct(benchmark_equity, args.initial_cash)),
        "benchmark_max_drawdown_pct": _fmt(_max_drawdown_pct(benchmark_equity)),
        "benchmark_sharpe_ratio": _fmt(_sharpe_ratio(benchmark_equity)),
        "excess_return_pct": _fmt(
            _return_pct(equity, args.initial_cash)
            - _return_pct(benchmark_equity, args.initial_cash),
        ),
    }
    return {
        "framework": "nautilus_trader",
        "nautilus_trader_version": nautilus_trader.__version__,
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "period": f"{frame.index[0].isoformat()}/{frame.index[-1].isoformat()}",
        "strategy": f"EMA {args.fast_period}/{args.slow_period}",
        "capital": _fmt(args.initial_cash),
        "fee_rate": _fmt(args.fee_rate),
        "slippage": "not modeled; Nautilus FillModel does not provide rate slippage here",
        "risk_per_trade": _fmt(args.risk_per_trade),
        "execution": (
            "Strategy queues bar-close signals for the next bar; runner feeds trade ticks at "
            "candle opens, so report prices match common next-open execution."
        ),
        "native_bar_execution_note": (
            "Nautilus bar-only market orders fill at same-bar close; this spike does not use "
            "that mode for the comparable summary."
        ),
        "timestamp_note": (
            "Nautilus order timestamps occur on the queued bar event; report timestamps are "
            "normalized back to the corresponding candle-open proxy."
        ),
        "gap_policy": args.gap_policy,
        "max_forward_fill_candles": str(args.max_forward_fill_candles),
        "engine_total_orders": str(result.total_orders),
        "engine_total_positions": str(result.total_positions),
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


def _write_trades(path: Path, fills: list[FillRow]) -> None:
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
        for fill in fills:
            writer.writerow(
                {
                    "timestamp": fill.timestamp.isoformat(),
                    "symbol": fill.symbol,
                    "side": fill.side,
                    "quantity": str(fill.quantity),
                    "price": str(fill.price),
                    "fee": str(fill.fee),
                    "realized_pnl": str(fill.realized_pnl),
                    "intent_id": "",
                    "fill_id": fill.fill_id,
                },
            )


def _write_equity_curve(path: Path, equity: pd.Series) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "equity"])
        writer.writeheader()
        for timestamp, value in equity.items():
            writer.writerow({"timestamp": timestamp.isoformat(), "equity": _fmt(value)})


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
                "notes": "Regime attribution not part of Spike D Nautilus comparison",
            },
        )


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
    gaps: list[float] = []
    for previous, current in zip(equity.index, equity.index[1:], strict=False):
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


def _engine_total_pnl(result: Any) -> float:
    return float(result.stats_pnls.get("USDT", {}).get("PnL (total)", 0.0))


def _timestamp_to_ns(timestamp: pd.Timestamp) -> int:
    return int(timestamp.timestamp() * 1_000_000_000)


def _fmt(value: float | int | str) -> str:
    if isinstance(value, str):
        return value
    decimal_value = Decimal(str(value))
    return format(decimal_value, "f")


if __name__ == "__main__":
    main()
