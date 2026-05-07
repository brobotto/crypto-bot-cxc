# Limitations

## Execution Model

- Native Nautilus bar-only market orders submitted from `on_bar()` fill at the same bar close. That does not match the common test spec's next-candle open execution.
- This spike uses a proxy: bars drive signals, trade ticks at candle opens provide executable prices, and the strategy queues signals for the next bar. Report timestamps are normalized back to the candle-open proxy.
- The proxy is good for framework comparison, but it is not a clean production execution design by itself.
- The strategy uses an internal long/flat flag after submitting market orders. It is acceptable for this deterministic spike, where all 320 orders filled, but production code should update state from Nautilus order/position callbacks to avoid divergence if an order is rejected.

## Slippage

- Rate-based slippage (`0.0005`) is not modeled.
- Nautilus `FillModel` supports probabilistic one-tick slippage, which is not equivalent to the common percentage slippage model.

## Accounting

- Nautilus owns the matching/account model during the run.
- The report equity curve is reconstructed from Nautilus filled orders so output files match Spike A/B/C shape.
- Final equity is cross-checked against Nautilus engine PnL in `engine_final_equity`.

## Framework Fit

- Nautilus has strong event-driven architecture and closer backtest/live parity than research-only tools.
- The API surface is large: instruments, venues, account type, bar/tick execution, and timestamps must all be configured correctly.
- For this project, adopting Nautilus would shift a lot of our custom broker/ledger design into Nautilus-specific adapters.
