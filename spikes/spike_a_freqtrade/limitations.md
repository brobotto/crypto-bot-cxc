# Limitations

## Framework Constraints

- Freqtrade is a complete bot framework, but it expects to own config, strategy discovery, exchange metadata, backtest storage, and runtime lifecycle.
- Even in local-data backtesting, Freqtrade tries to load exchange market metadata. The spike uses an offline market patch to avoid network dependency.

## Backtest Model Gaps

- Native Freqtrade backtesting in this spike does not model the custom common-spec slippage rate of `0.0005`.
- Market orders require `entry_pricing.price_side = "other"` and `exit_pricing.price_side = "other"`.
- Freqtrade moves the backtest start by `startup_candle_count`, so reported backtest period starts at `2022-01-05 04:00:00`.
- Freqtrade reports closed trades, while the common report uses fill/order rows. This spike records both `closed_trades=160` and `trades=320`.

## Ledger / Reconciliation Gaps

- Freqtrade owns accounting and wallet history in its internal result export.
- It does not exercise our `PortfolioLedger`, `BrokerInterface`, startup reconciliation, or unified backtest/live broker contract.

## Execution / Urgency Gaps

- Freqtrade has its own order model and does not exercise our `ExecutionPlanner`.
- Urgency mapping, exchange capability fallback, DMS, software watchdog, and reconciliation policy would need adapters or custom integration if Freqtrade became the live runner.
