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

Not done yet:

- Data gap policy for missing Binance candle: `2023-03-24T13:00:00Z`
- Run full 2022-2024 after explicit gap policy is chosen
- Compare results against Freqtrade/VectorBT/Nautilus
- Add partial fill by volume cap
- Add benchmark comparison vs buy-and-hold
