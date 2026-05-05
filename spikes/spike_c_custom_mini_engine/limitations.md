# Limitations

## Current Mini Engine Limitations

- `ExecutionPlanner` is configured for next-open market execution to match the Spike C common test spec.
- `BacktestBroker` currently supports full fills only.
- `BacktestBroker` does not yet simulate balance rejection; `PortfolioLedger` is the source of truth.
- Regime is injected into `BacktestEngine` through a `regime_provider`, but Spike C CLI still uses an explicit fixed-regime provider and emits a warning. Full feature-driven regime integration is next.
- Report writer produces required files, but `regime_performance.csv` is currently an insufficient-data placeholder.
- Full 2022-2024 Binance data requires explicit `gap_policy=forward_fill` because one Binance hourly candle is missing. Forward-fill is capped at 3 synthetic candles by default.
- Buy-and-hold benchmark starts at the first input candle close while the strategy waits for warmup. This gives the benchmark an intentional head start in Spike C, so use it as a framework-comparison baseline rather than strategy-quality proof.

## Known Design Notes

- Fee-aware realized P&L is implemented in the ledger by prorating entry fees on exit.
- Strategy emits `OrderIntent`; broker only receives `ConcreteOrder`.
- The engine executes pending broker orders before generating new signals on the current candle, preventing same-candle fills.
- OHLCV loader now rejects timestamp gaps rather than silently running on incomplete market data.
- Forward-fill gap policy creates zero-volume synthetic candles using previous close for OHLC. If a real crossover happened during a missing-data window, this policy can delay the signal; large gaps should be rejected or handled with a stricter data repair workflow.
