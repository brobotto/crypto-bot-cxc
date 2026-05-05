from __future__ import annotations

import argparse
from decimal import Decimal
from pathlib import Path

from crypto_bot_cxc.broker import BacktestBroker, BacktestBrokerConfig
from crypto_bot_cxc.data import load_ohlcv_events
from crypto_bot_cxc.engine import BacktestEngine
from crypto_bot_cxc.execution.planner import ExecutionPlanner
from crypto_bot_cxc.ledger import PortfolioLedger
from crypto_bot_cxc.reports import write_backtest_report
from crypto_bot_cxc.risk import RiskConfig, RiskManager
from crypto_bot_cxc.strategy import EMATrendConfig, EMATrendStrategy


def main() -> None:
    args = parse_args()
    initial_cash = Decimal(str(args.initial_cash))
    candles = load_ohlcv_events(args.input, symbol=args.symbol, timeframe=args.timeframe)

    strategy_config = EMATrendConfig(fast_period=args.fast_period, slow_period=args.slow_period)
    broker = BacktestBroker(
        BacktestBrokerConfig(
            fee_rate=Decimal(str(args.fee_rate)),
            slippage_rate=Decimal(str(args.slippage_rate)),
        )
    )
    ledger = PortfolioLedger(initial_cash=initial_cash)
    engine = BacktestEngine(
        strategy=EMATrendStrategy(strategy_config),
        risk_manager=RiskManager(
            RiskConfig(
                risk_per_trade=Decimal(str(args.risk_per_trade)),
                max_open_positions=args.max_open_positions,
                min_order_notional=Decimal(str(args.min_order_notional)),
            )
        ),
        planner=ExecutionPlanner(),
        broker=broker,
        ledger=ledger,
        warmup_period=args.slow_period,
    )
    result = engine.run(candles)
    summary = write_backtest_report(result, output_dir=args.output_dir, initial_cash=initial_cash)
    print(f"trades={summary.trades} final_equity={summary.final_equity}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Spike C custom mini-engine backtest.")
    parser.add_argument("--input", type=Path, required=True, help="CSV or Parquet OHLCV file")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for report files")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--initial-cash", type=Decimal, default=Decimal("10000"))
    parser.add_argument("--fast-period", type=int, default=20)
    parser.add_argument("--slow-period", type=int, default=100)
    parser.add_argument("--fee-rate", type=Decimal, default=Decimal("0.001"))
    parser.add_argument("--slippage-rate", type=Decimal, default=Decimal("0.0005"))
    parser.add_argument("--risk-per-trade", type=Decimal, default=Decimal("0.01"))
    parser.add_argument("--max-open-positions", type=int, default=1)
    parser.add_argument("--min-order-notional", type=Decimal, default=Decimal("10"))
    return parser.parse_args()


if __name__ == "__main__":
    main()

