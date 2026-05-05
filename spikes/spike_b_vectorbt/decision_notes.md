# Decision Notes

## Summary

VectorBT is viable as a research and parameter-sweep companion. It reproduced the custom Spike C common spec very closely when using shifted signals and next-open execution.

## Result Comparison

- Spike C custom final equity: 10064.214042562556305
- Spike B VectorBT final equity: 10064.123594877297
- Difference: about 0.09 USDT over 3 years
- Order/fill count: 320 in both runs
- Sharpe ratio: 0.5530 custom vs 0.5530 VectorBT

The remaining difference is expected because VectorBT percent sizing is not exactly the same as custom quantity sizing and Decimal rounding.

## Pros

- Very fast to create parameter sweeps.
- Produces credible research metrics quickly.
- Useful for hypothesis testing before implementing a strategy in the custom engine.
- Can act as an independent check against custom backtest math.

## Cons

- Not a live-trading architecture.
- Does not exercise our ledger, broker contract, execution planner, risk gates, reconciliation, or security requirements.
- Dependency stack is heavier than core and currently pins pandas below 3.0.
- Precise execution parity requires care: signal shift, execution price, sizing semantics, fees, and slippage must all be made explicit.

## Recommendation

Keep VectorBT as a research accelerator and comparison tool, not the primary engine. Continue the framework decision with Freqtrade and Nautilus/Jesse only if we still need stronger evidence after this and Spike C.

## Open Questions

- Should VectorBT parameter sweeps become part of V1 validation tooling?
- Do we need a custom adapter that exports strategy signals from the core engine into VectorBT for faster research?
- Should the common spec use exact custom quantity replay for framework parity, or native framework sizing for ecosystem realism?
