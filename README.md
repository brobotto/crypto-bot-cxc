# Crypto Bot CXC

Backtest-first crypto trading bot research and implementation workspace.

Current phase: V1 backtest core.

Key references:

- `doc/design/design_overview.md`
- `doc/design/merged_design_spec.md`
- `doc/design/implementation_plan.md`

Core direction:

- Spot-only, long-only first
- Modular monolith
- Unified broker interface
- Risk-first and ledger-centric
- Backtest, paper, and live should share the same strategy/risk/execution contracts

V1 smoke backtest:

```bash
cxc-backtest --input tests/fixtures/ohlcv/BTC_USDT_1h_v1_smoke.csv --config config/v1_smoke_strategy_config.yaml --output-dir outputs/v1_smoke --initial-cash 10000
```

Source-tree fallback:

```bash
python -m crypto_bot_cxc.cli.backtest --input tests/fixtures/ohlcv/BTC_USDT_1h_v1_smoke.csv --config config/v1_smoke_strategy_config.yaml --output-dir outputs/v1_smoke --initial-cash 10000
```
