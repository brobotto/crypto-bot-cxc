# Decision Notes

## Summary

NautilusTrader can run the common EMA spike with excellent numerical alignment once execution is modeled carefully. The framework is powerful and event-driven, but the setup surface is significantly heavier than VectorBT/Freqtrade and much heavier than the custom mini engine.

Comparable no-slippage result:

- Orders: 320
- Final equity: 10080.381997 USDT
- Return: 0.803820%
- Max drawdown: 0.682187%
- Sharpe: 0.691513
- Difference vs Freqtrade no-slippage final equity: about 0.0002 USDT
- Difference vs Custom no-slippage final equity: about 0.0062 USDT

## Pros

- Strong event-driven model with explicit instruments, venues, orders, accounts, and portfolio state.
- Backtest/live parity is a first-class design goal.
- Python 3.13 Windows wheel installed successfully.
- Result aligns closely with Freqtrade/custom no-slippage once next-open execution is proxied.

## Cons

- Bar-only execution semantics are not the common next-open model by default; market orders from `on_bar()` fill at same-bar close.
- Correct setup requires understanding venue account type, instrument metadata, bar execution, trade execution, and timestamp ordering.
- Native accounting is powerful, but integrating our planned ledger/reconciliation design would require Nautilus-specific adapters or accepting Nautilus as the owner of those concerns.
- Rate-based slippage matching the custom spec was not implemented in this spike.

## Recommendation

Do not choose NautilusTrader as the primary V1 framework unless backtest/live parity becomes more important than keeping our custom broker, ledger, and reconciliation contracts as the core source of truth.

Keep Nautilus as a serious reference for event-driven architecture and live/backtest parity. For the current design, custom core plus VectorBT as the research accelerator still looks cleaner.

## Open Questions

- Would a deeper Nautilus adapter let us keep our Unified Broker contract without fighting the framework?
- Does Nautilus support a clean percentage slippage model through a custom fill model with acceptable effort?
- Is the operational complexity worth it before multi-venue or high-fidelity execution becomes a real requirement?
