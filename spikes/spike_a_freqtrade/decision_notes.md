# Decision Notes

## Summary

Freqtrade is viable to run an MVP-style bot and backtest a simple strategy, but it is much less aligned with the planned custom architecture than VectorBT is as a research companion.

## Result Comparison

- Spike C custom with common slippage: 10064.214042562556305
- Spike B VectorBT with common slippage: 10064.123594877297
- Spike A Freqtrade native no-slippage: 10080.382191
- Spike C custom no-slippage reference: 10080.38816748003

The Freqtrade result matches the custom no-slippage reference within about `0.006 USDT`, so signal timing and fee handling are aligned. The difference from the common slippage run is expected because Freqtrade did not model slippage in this spike.

## Pros

- Production-minded bot framework with config, strategy loading, backtesting, reporting, dry-run/live lifecycle, API server, Telegram integration, and exchange support.
- Freqtrade 2026.4 installed successfully on Python 3.13 in this environment.
- Backtest output is rich and includes wallet history, trade stats, drawdown, Sharpe/Sortino/Calmar, and tag breakdowns.
- Useful as a reference implementation for bot operations and exchange integration concepts.

## Cons

- It wants to own the runtime architecture, which conflicts with our ledger-centric unified broker design.
- Local backtesting still tries to load exchange markets unless patched or network is available.
- Native backtesting did not match the common slippage model.
- Adapting Freqtrade to our `OrderIntent -> Risk -> ExecutionPlanner -> BrokerInterface -> Ledger` path would be non-trivial.
- Its internal wallet/accounting would duplicate or bypass our portfolio ledger.

## Recommendation

Do not choose Freqtrade as the primary core engine for V1 if the design goal remains a custom unified broker and ledger. Keep it as a reference for operational features and a possible emergency MVP runner, but treat custom core plus VectorBT research support as the stronger fit so far.

## Open Questions

- Is a Freqtrade paper/live spike still useful after we build our own paper broker?
- Should we borrow operational patterns from Freqtrade, such as config layout, Telegram/API server, or pairlist handling?
- Is slippage parity worth pursuing with custom price hooks, or is documenting the native limitation enough for V0?
