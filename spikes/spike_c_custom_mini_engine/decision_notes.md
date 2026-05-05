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
- EMA 20/100 with 1% allocation/risk sizing underperformed buy-and-hold heavily in 2022-2024. This is expected for a tiny-risk infrastructure spike, but it means strategy quality is not proven.

## BTC/USDT 2024 Sanity Result

- Rows: 8,784
- Trades: 92
- Final equity: 10078.675091426681485
- Total return: 0.7867509142668148500%
- Max drawdown: 0.2513729498623731906536073251%
- Total realized P&L: 78.675091426681485
- Total fees: 9.326185584813515

## BTC/USDT 2022-2024 Common Spec Result

Run used explicit `--gap-policy forward_fill` for missing candle `2023-03-24T13:00:00Z`.

- Rows after policy: 26,304
- Trades: 320
- Final equity: 10064.214042562556305
- Total return: 0.6421404256255630500%
- Max drawdown: 0.7314326859083853413459678443%
- Sharpe ratio: 0.5530336892640073162211567991
- Total realized P&L: 64.214042562556305
- Total fees: 32.056701315108695
- Buy-and-hold final equity: 20056.52847760840858425248730
- Buy-and-hold return: 100.5652847760840858425248730%
- Buy-and-hold Sharpe ratio: 0.7003678423393491376027869511
- Excess return vs buy-and-hold: -99.9231443504585227925248730%

## Recommendation

Continue Spike C by comparing this same spec against Freqtrade/VectorBT/Nautilus before making any framework decision.
