from __future__ import annotations

import argparse
import csv
import io
import json
import math
import shutil
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import freqtrade
import pandas as pd

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
    paths = _prepare_workspace(args=args, events=events)
    _run_freqtrade(args=args, paths=paths)
    exported, equity = _load_latest_backtest(paths["backtest_dir"])
    benchmark_equity = _buy_and_hold_equity(frame["close"], initial_cash=args.initial_cash)
    summary = _summary_payload(
        args=args,
        frame=frame,
        rows=len(events),
        exported=exported,
        equity=equity,
        benchmark_equity=benchmark_equity,
    )
    benchmark = _benchmark_payload(summary)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_equity_curve(args.output_dir / "equity_curve.csv", equity)
    _write_trades(
        args.output_dir / "trades.csv",
        exported["strategy"]["SpikeAEMATrendStrategy"]["trades"],
        args.symbol,
    )
    _write_json(args.output_dir / "summary.json", summary["metrics"])
    _write_json(args.output_dir / "benchmark_comparison.json", benchmark)
    _write_monthly_returns(args.output_dir / "monthly_returns.csv", equity)
    _write_regime_performance_placeholder(args.output_dir / "regime_performance.csv")

    _write_json(args.summary_path, summary)
    _write_json(args.benchmark_path, benchmark)
    print(
        "framework=freqtrade "
        f"trades={summary['metrics']['trades']} "
        f"final_equity={summary['metrics']['final_equity']} "
        f"sharpe={summary['metrics']['sharpe_ratio']}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Spike A Freqtrade backtest.")
    parser.add_argument("--input", type=Path, required=True, help="CSV or Parquet OHLCV file")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for report files")
    parser.add_argument(
        "--summary-path",
        type=Path,
        default=Path("spikes/spike_a_freqtrade/backtest_summary.json"),
    )
    parser.add_argument(
        "--benchmark-path",
        type=Path,
        default=Path("spikes/spike_a_freqtrade/benchmark_comparison.json"),
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=Path("spikes/spike_a_freqtrade/user_data"),
    )
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--initial-cash", type=float, default=10000.0)
    parser.add_argument("--fee-rate", type=float, default=0.001)
    parser.add_argument(
        "--gap-policy",
        choices=[policy.value for policy in GapPolicy],
        default="strict",
    )
    parser.add_argument("--max-forward-fill-candles", type=int, default=3)
    return parser.parse_args()


def _prepare_workspace(
    *,
    args: argparse.Namespace,
    events: list[MarketDataEvent],
) -> dict[str, Path]:
    userdir = args.workdir
    datadir = userdir / "data" / args.exchange
    backtest_dir = userdir / "backtest_results"
    config_path = userdir / "config.json"
    if backtest_dir.exists():
        shutil.rmtree(backtest_dir)
    datadir.mkdir(parents=True, exist_ok=True)
    backtest_dir.mkdir(parents=True, exist_ok=True)

    _write_freqtrade_ohlcv(
        datadir / f"{args.symbol.replace('/', '_')}-{args.timeframe}.json",
        events,
    )
    _write_freqtrade_config(config_path, args)
    return {
        "userdir": userdir,
        "datadir": datadir,
        "backtest_dir": backtest_dir,
        "config": config_path,
    }


def _write_freqtrade_ohlcv(path: Path, events: list[MarketDataEvent]) -> None:
    rows = [
        [
            int(event.timestamp.timestamp() * 1000),
            float(event.open),
            float(event.high),
            float(event.low),
            float(event.close),
            float(event.volume),
        ]
        for event in events
    ]
    path.write_text(json.dumps(rows), encoding="utf-8")


def _write_freqtrade_config(path: Path, args: argparse.Namespace) -> None:
    config = {
        "$schema": "https://schema.freqtrade.io/schema.json",
        "max_open_trades": 1,
        "stake_currency": "USDT",
        "stake_amount": "unlimited",
        "tradable_balance_ratio": 1.0,
        "fiat_display_currency": "USD",
        "timeframe": args.timeframe,
        "dry_run": True,
        "dry_run_wallet": args.initial_cash,
        "cancel_open_orders_on_exit": False,
        "trading_mode": "spot",
        "margin_mode": "",
        "use_exit_signal": True,
        "exit_profit_only": False,
        "ignore_roi_if_entry_signal": False,
        "unfilledtimeout": {
            "entry": 10,
            "exit": 10,
            "exit_timeout_count": 0,
            "unit": "minutes",
        },
        "entry_pricing": {
            "price_side": "other",
            "use_order_book": False,
            "price_last_balance": 0.0,
        },
        "exit_pricing": {
            "price_side": "other",
            "use_order_book": False,
            "price_last_balance": 0.0,
        },
        "exchange": {
            "name": args.exchange,
            "key": "",
            "secret": "",
            "ccxt_config": {},
            "ccxt_async_config": {},
            "pair_whitelist": [args.symbol],
            "pair_blacklist": [],
        },
        "pairlists": [{"method": "StaticPairList"}],
        "telegram": {"enabled": False, "token": "", "chat_id": ""},
        "api_server": {
            "enabled": False,
            "listen_ip_address": "127.0.0.1",
            "listen_port": 8080,
            "verbosity": "error",
            "enable_openapi": False,
            "jwt_secret_key": "spike-a-jwt",
            "ws_token": "spike-a-ws",
            "CORS_origins": [],
            "username": "spike",
            "password": "spike",
        },
        "bot_name": "spike-a-freqtrade",
        "initial_state": "running",
        "force_entry_enable": False,
        "internals": {"process_throttle_secs": 5},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _run_freqtrade(*, args: argparse.Namespace, paths: dict[str, Path]) -> None:
    from freqtrade.commands import Arguments
    from freqtrade.exchange.exchange import Exchange

    command = [
        "backtesting",
        "--config",
        str(paths["config"]),
        "--userdir",
        str(paths["userdir"]),
        "--strategy",
        "SpikeAEMATrendStrategy",
        "--strategy-path",
        str(Path("spikes/spike_a_freqtrade/strategies")),
        "--datadir",
        str(paths["datadir"]),
        "--timeframe",
        args.timeframe,
        "--data-format-ohlcv",
        "json",
        "--fee",
        str(args.fee_rate),
        "--dry-run-wallet",
        str(args.initial_cash),
        "--max-open-trades",
        "1",
        "--cache",
        "none",
        "--export",
        "trades",
        "--backtest-directory",
        str(paths["backtest_dir"]),
    ]
    original_reload_markets = Exchange.reload_markets
    Exchange.reload_markets = _offline_reload_markets(args)  # type: ignore[method-assign]
    try:
        parsed_args = Arguments(command).get_parsed_arg()
        return_code = parsed_args["func"](parsed_args)
        if return_code not in (None, 0):
            raise RuntimeError(f"freqtrade backtesting failed with return code {return_code}")
    finally:
        Exchange.reload_markets = original_reload_markets  # type: ignore[method-assign]


def _offline_reload_markets(args: argparse.Namespace):
    def reload_markets(
        self: Any,
        force: bool = False,
        *,
        load_leverage_tiers: bool = True,
    ) -> None:
        del force, load_leverage_tiers
        base, quote = args.symbol.split("/")
        market = {
            "id": f"{base}{quote}",
            "symbol": args.symbol,
            "base": base,
            "quote": quote,
            "type": "spot",
            "spot": True,
            "margin": False,
            "future": False,
            "swap": False,
            "active": True,
            "precision": {"amount": 0.000001, "price": 0.01, "cost": 0.01},
            "limits": {
                "amount": {"min": 0.000001, "max": None},
                "price": {"min": 0.01, "max": None},
                "cost": {"min": 10.0, "max": None},
                "leverage": {"min": None, "max": None},
            },
            "maker": args.fee_rate,
            "taker": args.fee_rate,
        }
        markets = {args.symbol: market}
        self._markets = markets
        self._api.markets = markets
        self._api_async.markets = markets
        self._api.markets_by_id = {market["id"]: [market]}
        self._api_async.markets_by_id = {market["id"]: [market]}

    return reload_markets


def _load_latest_backtest(backtest_dir: Path) -> tuple[dict[str, Any], pd.Series]:
    meta_path = backtest_dir / ".last_result.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    latest = backtest_dir / meta["latest_backtest"]
    if latest.suffix == ".zip":
        with ZipFile(latest) as archive:
            result_name = next(
                name
                for name in archive.namelist()
                if name.endswith(".json") and not name.endswith("_config.json")
            )
            wallet_name = next(
                name for name in archive.namelist() if name.endswith("_wallet.feather")
            )
            result = json.loads(archive.read(result_name).decode("utf-8"))
            wallet = pd.read_feather(io.BytesIO(archive.read(wallet_name)))
            equity = wallet.groupby("date")["total_quote"].sum()
            equity.index = pd.DatetimeIndex(equity.index)
            return result, equity
    return json.loads(latest.read_text(encoding="utf-8")), pd.Series(dtype="float64")


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


def _equity_from_trades(
    *,
    frame: pd.DataFrame,
    trades: list[dict[str, Any]],
    initial_cash: float,
) -> pd.Series:
    trade_events: dict[pd.Timestamp, list[dict[str, Any]]] = {}
    for trade in trades:
        open_time = pd.Timestamp(trade["open_date"]).tz_convert("UTC")
        close_time = pd.Timestamp(trade["close_date"]).tz_convert("UTC")
        trade_events.setdefault(open_time, []).append({"kind": "open", "trade": trade})
        trade_events.setdefault(close_time, []).append({"kind": "close", "trade": trade})

    cash = initial_cash
    positions: list[dict[str, float]] = []
    values: list[float] = []
    for timestamp, row in frame.iterrows():
        for event in trade_events.get(timestamp, []):
            trade = event["trade"]
            if event["kind"] == "open":
                amount = float(trade["amount"])
                open_rate = float(trade["open_rate"])
                open_fee = float(trade.get("fee_open_cost", 0.0))
                cash -= amount * open_rate + open_fee
                positions.append({"amount": amount, "open_rate": open_rate, "open_fee": open_fee})
            else:
                amount = float(trade["amount"])
                close_rate = float(trade["close_rate"])
                close_fee = float(trade.get("fee_close_cost", 0.0))
                cash += amount * close_rate - close_fee
                positions = positions[1:]
        close = float(row["close"])
        position_value = sum(position["amount"] * close for position in positions)
        values.append(cash + position_value)
    return pd.Series(values, index=frame.index)


def _summary_payload(
    *,
    args: argparse.Namespace,
    frame: pd.DataFrame,
    rows: int,
    exported: dict[str, Any],
    equity: pd.Series,
    benchmark_equity: pd.Series,
) -> dict[str, Any]:
    strategy = exported["strategy"]["SpikeAEMATrendStrategy"]
    trades = strategy["trades"]
    total_realized_pnl = float(strategy["profit_total_abs"])
    total_fees = sum(_trade_fee_total(trade) for trade in trades)
    metrics = {
        "rows": str(rows),
        "trades": str(len(trades) * 2),
        "closed_trades": str(len(trades)),
        "final_equity": _fmt(equity.iloc[-1]),
        "total_return_pct": _fmt(_return_pct(equity, args.initial_cash)),
        "max_drawdown_pct": _fmt(_max_drawdown_pct(equity)),
        "sharpe_ratio": _fmt(_sharpe_ratio(equity)),
        "total_realized_pnl": _fmt(total_realized_pnl),
        "total_fees": _fmt(total_fees),
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
        "framework": "freqtrade",
        "freqtrade_version": freqtrade.__version__,
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "period": f"{frame.index[0].isoformat()}/{frame.index[-1].isoformat()}",
        "freqtrade_backtest_period": f"{strategy['backtest_start']}/{strategy['backtest_end']}",
        "strategy": "EMA 20/100",
        "capital": _fmt(args.initial_cash),
        "fee_rate": _fmt(args.fee_rate),
        "slippage": "not modeled by native Freqtrade backtesting in this spike",
        "execution": "Freqtrade backtesting with market orders on next candle",
        "sizing": "custom_stake_amount returns about 1% of available stake",
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


def _write_equity_curve(path: Path, equity: pd.Series) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "equity"])
        writer.writeheader()
        for timestamp, value in equity.items():
            writer.writerow({"timestamp": timestamp.isoformat(), "equity": _fmt(value)})


def _write_trades(path: Path, trades: list[dict[str, Any]], symbol: str) -> None:
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
        for index, trade in enumerate(trades):
            open_order = trade["orders"][0]
            close_order = trade["orders"][-1]
            writer.writerow(
                {
                    "timestamp": trade["open_date"],
                    "symbol": symbol,
                    "side": "BUY",
                    "quantity": str(trade["amount"]),
                    "price": str(trade["open_rate"]),
                    "fee": str(_order_fee(open_order)),
                    "realized_pnl": "0",
                    "intent_id": "",
                    "fill_id": f"{index}-open",
                }
            )
            writer.writerow(
                {
                    "timestamp": trade["close_date"],
                    "symbol": symbol,
                    "side": "SELL",
                    "quantity": str(trade["amount"]),
                    "price": str(trade["close_rate"]),
                    "fee": str(_order_fee(close_order)),
                    "realized_pnl": str(trade.get("profit_abs", 0.0)),
                    "intent_id": "",
                    "fill_id": f"{index}-close",
                }
            )


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
                "notes": "Regime attribution not part of Spike A Freqtrade comparison",
            }
        )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _trade_fee_total(trade: dict[str, Any]) -> float:
    return sum(_order_fee(order) for order in trade.get("orders", []))


def _order_fee(order: dict[str, Any]) -> float:
    notional = float(order["amount"]) * float(order["safe_price"])
    return abs(float(order["cost"]) - notional)


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


def _fmt(value: float | int | str) -> str:
    if isinstance(value, str):
        return value
    return format(value, "f")


if __name__ == "__main__":
    main()
