# Spike C — Custom Mini Engine

Goal: prove the custom path and estimate real effort.

This spike owns the first working versions of event contracts, BrokerInterface, BacktestBroker, minimal risk, and minimal ledger.

## Current Status

Started: 2026-05-05

Completed in first setup pass:

- Event contracts: `MarketDataEvent`, `OrderIntent`, `FillEvent`, `RegimeEvent`
- Execution contract: `ConcreteOrder`, `Urgency`, `OrderType`
- `BrokerInterface`
- `BacktestBroker` with next-candle market fill, fee, and slippage
- Minimal EMA feature update
- EMA crossover strategy
- Minimal long-only risk manager
- Fee-aware portfolio ledger
- Minimal backtest engine
- Tests for broker fills, ledger P&L, planner, regime detector, and no-lookahead engine behavior
- Review hardening pass: gap-open limit fills, OHLC validation, cash guard, strategy reset, warmup guard, and explicit fixed-regime warning
- CSV/Parquet OHLCV loader
- CSV/JSON report writer for required Spike outputs
- CLI runner: `python -m crypto_bot_cxc.cli.spike_c_backtest`
- Public OHLCV downloader CLI: `python -m crypto_bot_cxc.cli.download_ohlcv`

Completed in data/report pass:

- Sample CSV end-to-end run produced 2 trades and 5 report files
- BTC/USDT 1h 2024 Binance run produced 8,784 candles, 92 trades, and 5 report files
- Full BTC/USDT 1h 2022-2024 Binance download produced 26,303 rows and revealed one missing hourly candle
- Explicit gap policy added:
  - default: `strict`
  - optional: `forward_fill` synthetic zero-volume candles
- Full BTC/USDT 1h 2022-2024 run completed with `--gap-policy forward_fill`
- Buy-and-hold benchmark comparison added

Not done yet:

- Compare results against Freqtrade/VectorBT/Nautilus
- Add partial fill by volume cap
- Add real regime attribution to `regime_performance.csv`

Generated report folders such as `reports/`, `reports_2024/`, and `reports_full/` are ignored by git to avoid UUID/diff noise. Keep stable summary metrics in `backtest_summary.json`.
