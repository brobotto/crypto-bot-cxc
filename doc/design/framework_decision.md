# Framework Decision

Date: 2026-05-07

Status: Accepted for V1 planning

## Decision

Use the custom core as the primary V1 engine.

Use VectorBT as the research and parameter-sweep companion.

Keep Freqtrade as an operational reference and possible emergency MVP runner.

Keep NautilusTrader as an architecture reference for event-driven design and backtest/live parity.

Defer Jesse. It is optional and should not block V1 unless we specifically need to compare Monte Carlo UX later.

## Why

The V1 goal is not to get a bot live as quickly as possible. The goal is to build a backtest-first engine whose accounting, broker boundary, risk controls, execution planning, and later reconciliation can be trusted.

The custom Spike C proved the most important project-specific boundary:

```text
Strategy -> OrderIntent -> RiskManager -> ExecutionPlanner -> ConcreteOrder
-> BacktestBroker -> FillEvent -> PortfolioLedger
```

That boundary is harder to preserve if Freqtrade or Nautilus owns the runtime, broker, wallet, and accounting model. VectorBT is excellent for research, but it is not a live runtime and does not exercise our broker or ledger.

## Evidence

All required V0 framework spikes were completed:

- Spike A: Freqtrade
- Spike B: VectorBT
- Spike C: Custom mini engine
- Spike D: NautilusTrader

Common test spec:

- Symbol: BTC/USDT
- Timeframe: 1h
- Period: 2022-01-01 through 2024-12-31
- Capital: 10,000 USDT
- Strategy: EMA 20/100 long-only crossover
- Fee: 0.1%
- Execution: next candle open
- Sizing: about 1% allocation per entry

## Slippage-Aware Comparison

Custom and VectorBT both modeled the common `0.0005` slippage rate.

| Framework | Slippage | Orders | Final Equity | Return % | Max DD % | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| Custom mini engine | 0.0005 | 320 | 10064.214043 | 0.642140 | 0.731433 | 0.553034 |
| VectorBT | 0.0005 | 320 | 10064.123595 | 0.641236 | 0.730450 | 0.552981 |

Difference: about 0.09 USDT over 3 years. This is acceptable and mostly explained by native framework sizing and rounding differences.

## No-Slippage Comparison

Freqtrade and Nautilus did not model the common percentage slippage rate in these spikes. They should be compared against the custom no-slippage reference.

| Framework | Slippage | Orders | Final Equity | Return % | Max DD % | Sharpe |
|---|---:|---:|---:|---:|---:|---:|
| Custom mini engine | 0 | 320 | 10080.388167 | 0.803882 | 0.682027 | 0.691694 |
| Freqtrade | native none | 320 | 10080.382191 | 0.803822 | 0.681990 | 0.692913 |
| NautilusTrader | native none | 320 | 10080.381997 | 0.803820 | 0.682187 | 0.691513 |

Difference vs custom no-slippage:

- Freqtrade: about 0.0060 USDT
- NautilusTrader: about 0.0062 USDT

This gives strong confidence that EMA semantics, signal timing, next-open execution, fees, and core accounting are aligned across independent implementations.

## Framework Roles

| Framework | V1 Role | Strength | Main Limitation |
|---|---|---|---|
| Custom core | Primary engine | Preserves our broker, ledger, risk, and reconciliation design | We own implementation quality and live adapters |
| VectorBT | Research companion | Fast sweeps and independent research validation | Not a live architecture; does not exercise ledger/broker |
| Freqtrade | Operational reference | Mature bot lifecycle, dry-run/live ops, exchange integration patterns | Wants to own runtime and wallet/accounting |
| NautilusTrader | Architecture reference | Strong event model and backtest/live parity | Heavy setup; accounting/runtime ownership conflicts with custom ledger |
| Jesse | Deferred optional | Potentially useful Monte Carlo UX and strategy syntax | Free tier does not answer V1 broker/ledger/live path |

## Important Non-Decision

The EMA 20/100 strategy itself is not proven as a profitable production strategy.

Buy-and-hold returned about 100.565% over the same period, while the EMA spike returned about 0.64% with slippage or about 0.80% without slippage. That is expected because the spike used about 1% allocation per entry and was designed to validate infrastructure, not to optimize strategy performance.

Do not treat the V0 strategy result as approval to trade this strategy live.

## V1 Implementation Implications

Build V1 on the custom core under `src/crypto_bot_cxc`.

Preserve these contracts:

- Strategy emits `OrderIntent`; it must not submit orders directly.
- Risk manager approves, sizes, or rejects intents.
- ExecutionPlanner transforms approved intents into `ConcreteOrder`.
- BrokerInterface receives `ConcreteOrder`.
- Fill events update the portfolio ledger.
- Ledger remains the source of truth for realized PnL, fees, positions, and equity.

Use VectorBT for:

- Parameter sweeps.
- Sensitivity checks.
- Quick research validation.
- Independent cross-checks against custom backtest outputs.

Use Freqtrade references for:

- Operational config layout.
- Dry-run/live lifecycle ideas.
- Telegram/API/status reporting ideas.
- Exchange integration edge cases.

Use Nautilus references for:

- Event-driven architecture.
- Venue/account/instrument modeling.
- Backtest/live parity concepts.
- Execution model warnings, especially bar vs tick semantics.

## V0 Gate Status

V0 required evidence is complete enough to start V1:

- Spike A-D completed.
- Decision notes exist for each required spike.
- Framework decision written.
- Event contracts and BrokerInterface draft exist from Spike C.
- Data spec and gap policy exist.
- Cross-framework parity has been verified.

## Next Step

Start V1 Backtest Core using the existing custom mini engine as the seed, then harden it into production-quality modules rather than replacing it with an external framework.

