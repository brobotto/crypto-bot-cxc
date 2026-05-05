# Limitations

## Framework Constraints

- VectorBT is excellent for research speed and parameter sweeps, but it is not a live-trading engine.
- VectorBT 1.0.0 requires `pandas<3.0`, so the project environment must remain compatible with pandas 2.x while this spike is active.

## Backtest Model Gaps

- The spike shifts signals by one candle and fills at next candle open to approximate the custom broker.
- Sizing uses VectorBT native percent sizing, approximately 1% of cash/equity per entry. This is slightly different from Spike C, which sizes quantity from cash at signal-candle close and rounds to `0.000001`.
- Reported order count is fill/order count, not closed trade count.
- Fill model does not pass through our `BrokerInterface`, `ExecutionPlanner`, or ledger.

## Ledger / Reconciliation Gaps

- VectorBT owns accounting inside the portfolio object for this spike.
- It does not test our portfolio ledger, reconciliation, or startup recovery requirements.

## Execution / Urgency Gaps

- No urgency mapping, order type fallback, exchange capability flags, DMS, or software watchdog behavior is exercised here.
- This spike should inform research/backtest tooling, not live architecture.
