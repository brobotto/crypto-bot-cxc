# Decision Notes

## Interim Summary

The custom path is viable enough to continue Spike C. The mini engine now proves the core boundary:

```text
Strategy -> OrderIntent -> RiskManager -> ExecutionPlanner -> ConcreteOrder
-> BacktestBroker -> FillEvent -> PortfolioLedger
```

It also proves:

```text
CSV OHLCV -> MarketDataEvent -> BacktestEngine -> trades/equity/summary reports
```

## Pros Seen So Far

- The unified broker boundary is practical.
- No-lookahead sequencing is straightforward to test.
- Fee-aware accounting can stay local to the ledger.
- The strategy can remain exchange-agnostic.
- Review hardening confirmed the engine can take an explicit `regime_provider` instead of hiding a hardcoded regime.

## Cons / Risks

- The custom engine still needs benchmark comparison before it can be compared to Freqtrade/VectorBT.
- Fill realism is still basic.
- Python 3.13 may not be suitable for all external framework spikes.
- Binance public BTC/USDT 1h data for 2022-2024 contains one missing hourly candle, so V1 needs a documented gap policy.

## BTC/USDT 2024 Sanity Result

- Rows: 8,784
- Trades: 92
- Final equity: 10078.675091426681485
- Total return: 0.7867509142668148500%
- Max drawdown: 0.2513729498623731906536073251%
- Total realized P&L: 78.675091426681485
- Total fees: 9.326185584813515

## Recommendation

Continue Spike C by adding explicit gap policy and benchmark comparison before making any framework decision.
