import csv
from decimal import Decimal
from pathlib import Path

import pytest

from crypto_bot_cxc.cli.backtest import run_backtest
from crypto_bot_cxc.data import GapPolicy


def test_run_backtest_loads_strategy_config_and_writes_reports(tmp_path: Path) -> None:
    input_path = tmp_path / "ohlcv.csv"
    _write_ohlcv_csv(input_path, closes=["100", "101", "102", "103", "104", "105"])
    output_dir = tmp_path / "reports"

    summary = run_backtest(
        input_path=input_path,
        output_dir=output_dir,
        config_path=_write_test_config(tmp_path, fast_period=2, slow_period=3, warmup_period=3),
        initial_cash=Decimal("1000"),
        symbol=None,
        timeframe=None,
        gap_policy=GapPolicy.STRICT,
        max_forward_fill_candles=3,
        conservative_slippage=False,
    )

    assert summary.final_equity == Decimal("1000")
    for report_file in [
        "trades.csv",
        "equity_curve.csv",
        "summary.json",
        "benchmark_comparison.json",
        "monthly_returns.csv",
        "regime_performance.csv",
    ]:
        assert (output_dir / report_file).exists()
    with (output_dir / "trades.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert "regime" in (reader.fieldnames or [])


def test_run_backtest_rejects_unsupported_strategy(tmp_path: Path) -> None:
    input_path = tmp_path / "ohlcv.csv"
    _write_ohlcv_csv(input_path, closes=["100", "101", "102"])
    config_path = _write_test_config(tmp_path, primary="grid", fast_period=2, slow_period=3)

    with pytest.raises(ValueError, match="unsupported V1 strategy"):
        run_backtest(
            input_path=input_path,
            output_dir=tmp_path / "reports",
            config_path=config_path,
            initial_cash=Decimal("1000"),
        )


def test_run_backtest_rejects_disabled_next_candle_execution(tmp_path: Path) -> None:
    input_path = tmp_path / "ohlcv.csv"
    _write_ohlcv_csv(input_path, closes=["100", "101", "102"])
    config_path = _write_test_config(
        tmp_path,
        fast_period=2,
        slow_period=3,
        next_candle_execution=False,
    )

    with pytest.raises(ValueError, match="next_candle_execution=true"):
        run_backtest(
            input_path=input_path,
            output_dir=tmp_path / "reports",
            config_path=config_path,
            initial_cash=Decimal("1000"),
        )


def test_run_backtest_warns_when_symbol_overrides_config(tmp_path: Path) -> None:
    input_path = tmp_path / "ohlcv.csv"
    _write_ohlcv_csv(input_path, closes=["100", "101", "102"])

    with pytest.warns(UserWarning, match="not listed"):
        run_backtest(
            input_path=input_path,
            output_dir=tmp_path / "reports",
            config_path=_write_test_config(tmp_path, fast_period=2, slow_period=3),
            initial_cash=Decimal("1000"),
            symbol="SOL/USDT",
        )


def test_run_backtest_warns_when_forward_fill_is_enabled(tmp_path: Path) -> None:
    input_path = tmp_path / "ohlcv.csv"
    _write_ohlcv_csv(input_path, closes=["100", "101", "102"])

    with pytest.warns(UserWarning, match="forward_fill"):
        run_backtest(
            input_path=input_path,
            output_dir=tmp_path / "reports",
            config_path=_write_test_config(tmp_path, fast_period=2, slow_period=3),
            initial_cash=Decimal("1000"),
            gap_policy=GapPolicy.FORWARD_FILL,
        )


def _write_ohlcv_csv(path: Path, *, closes: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp", "open", "high", "low", "close", "volume"],
        )
        writer.writeheader()
        for index, close in enumerate(closes):
            writer.writerow(
                {
                    "timestamp": f"2024-01-01T{index:02d}:00:00+00:00",
                    "open": close,
                    "high": str(Decimal(close) + Decimal("1")),
                    "low": str(Decimal(close) - Decimal("1")),
                    "close": close,
                    "volume": "100",
                }
            )


def _write_test_config(
    tmp_path: Path,
    *,
    primary: str = "ema_trend",
    fast_period: int = 2,
    slow_period: int = 4,
    warmup_period: int = 4,
    next_candle_execution: bool = True,
) -> Path:
    path = tmp_path / "strategy_config.yaml"
    path.write_text(
        f"""
strategy:
  primary: {primary}
  symbols:
    - BTC/USDT
  timeframe: 1h
  fast_period: {fast_period}
  slow_period: {slow_period}
  warmup_period: {warmup_period}

regime:
  adx_trend_threshold: 25
  adx_sideways_threshold: 20
  high_vol_multiplier: 1.5
  squeeze_multiplier: 0.5
  min_volume_ratio: 0.3
  max_spread_bps: 50

risk:
  risk_per_trade: 0.01
  atr_multiplier: 2.0
  daily_loss_limit: 0.02
  max_drawdown: 0.10
  max_open_positions: 1
  capital_reserve: 0.40

execution:
  default_fee_rate: 0.001
  basic_slippage_rate: 0.0005
  conservative_slippage_rate: 0.001
  next_candle_execution: {str(next_candle_execution).lower()}
""".lstrip(),
        encoding="utf-8",
    )
    return path
