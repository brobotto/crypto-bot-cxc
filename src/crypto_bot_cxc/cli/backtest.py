from __future__ import annotations

import argparse
import warnings
from decimal import Decimal
from pathlib import Path

from crypto_bot_cxc.broker import BacktestBroker
from crypto_bot_cxc.config import StrategyConfig, load_strategy_config
from crypto_bot_cxc.data import GapPolicy, load_ohlcv_events
from crypto_bot_cxc.engine import BacktestEngine
from crypto_bot_cxc.execution.planner import ExecutionPlanner
from crypto_bot_cxc.ledger import PortfolioLedger
from crypto_bot_cxc.regime import RegimeState
from crypto_bot_cxc.reports import SummaryMetrics, write_backtest_report
from crypto_bot_cxc.risk import RiskManager
from crypto_bot_cxc.strategy import EMATrendStrategy


def main() -> None:
    args = parse_args()
    summary = run_backtest(
        input_path=args.input,
        output_dir=args.output_dir,
        config_path=args.config,
        initial_cash=args.initial_cash,
        symbol=args.symbol,
        timeframe=args.timeframe,
        gap_policy=GapPolicy(args.gap_policy),
        max_forward_fill_candles=args.max_forward_fill_candles,
        conservative_slippage=args.conservative_slippage,
    )
    print(
        " ".join(
            [
                f"trades={summary.trades}",
                f"final_equity={summary.final_equity}",
                f"return_pct={summary.total_return_pct}",
                f"sharpe={summary.sharpe_ratio}",
            ]
        )
    )


def run_backtest(
    *,
    input_path: Path,
    output_dir: Path,
    config_path: Path,
    initial_cash: Decimal,
    symbol: str | None = None,
    timeframe: str | None = None,
    gap_policy: GapPolicy = GapPolicy.STRICT,
    max_forward_fill_candles: int = 3,
    conservative_slippage: bool = False,
) -> SummaryMetrics:
    config = load_strategy_config(config_path)
    _validate_strategy(config)

    selected_symbol = symbol or config.strategy.symbols[0]
    selected_timeframe = timeframe or config.strategy.timeframe
    if selected_symbol not in config.strategy.symbols:
        warnings.warn(
            f"symbol={selected_symbol} is not listed in {config_path}; running explicit override",
            stacklevel=2,
        )
    if gap_policy == GapPolicy.FORWARD_FILL:
        warnings.warn(
            "Using gap_policy=forward_fill; missing candles will be synthetic zero-volume bars "
            f"up to max_forward_fill_candles={max_forward_fill_candles}",
            stacklevel=2,
        )

    candles = load_ohlcv_events(
        input_path,
        symbol=selected_symbol,
        timeframe=selected_timeframe,
        gap_policy=gap_policy,
        max_forward_fill_candles=max_forward_fill_candles,
    )

    ledger = PortfolioLedger(initial_cash=initial_cash)
    engine = BacktestEngine(
        strategy=EMATrendStrategy(config.strategy.to_ema_trend_config()),
        risk_manager=RiskManager(config.risk.to_risk_config()),
        planner=ExecutionPlanner(),
        broker=BacktestBroker(
            config.execution.to_backtest_broker_config(conservative=conservative_slippage)
        ),
        ledger=ledger,
        # Fallback only; V1 config-driven backtests use regime_config below.
        regime_provider=lambda _event: RegimeState.NO_TRADE,
        regime_config=config.regime,
        warmup_period=config.strategy.warmup_period,
    )
    result = engine.run(candles)
    return write_backtest_report(
        result,
        output_dir=output_dir,
        initial_cash=initial_cash,
        benchmark_events=candles,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run V1 custom-core backtest.")
    parser.add_argument("--input", type=Path, required=True, help="CSV or Parquet OHLCV file")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for report files")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/strategy_config.yaml"),
        help="Strategy config YAML path",
    )
    parser.add_argument("--symbol", default=None, help="Override config strategy.symbols[0]")
    parser.add_argument("--timeframe", default=None, help="Override config strategy.timeframe")
    parser.add_argument("--initial-cash", type=Decimal, default=Decimal("10000"))
    parser.add_argument(
        "--gap-policy",
        choices=[policy.value for policy in GapPolicy],
        default=GapPolicy.STRICT.value,
    )
    parser.add_argument("--max-forward-fill-candles", type=int, default=3)
    parser.add_argument(
        "--conservative-slippage",
        action="store_true",
        help="Use execution.conservative_slippage_rate instead of basic_slippage_rate",
    )
    return parser.parse_args()


def _validate_strategy(config: StrategyConfig) -> None:
    if config.strategy.primary != "ema_trend":
        raise ValueError(f"unsupported V1 strategy: {config.strategy.primary}")
    if not config.execution.next_candle_execution:
        raise ValueError("V1 backtest requires execution.next_candle_execution=true")


if __name__ == "__main__":
    main()
