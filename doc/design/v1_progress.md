# V1 Progress

Status: started

## 2026-05-07

Initial V1 slice focuses on hardening the Spike C custom core into a reusable
backtest foundation. No paper/live exchange path is in scope for this slice.

Completed in this slice:

- Added `config/strategy_config.yaml` strategy defaults for EMA Trend, symbols,
  timeframe, and warmup.
- Added `crypto_bot_cxc.config` loader that converts YAML into typed dataclasses
  and Decimal-based runtime configs.
- Expanded `feature_engine.py` beyond Spike C EMA state updates:
  - `calc_ema`
  - `calc_atr`
  - `calc_adx`
  - `calc_bb_width`
- Wired V1 risk config support for `capital_reserve`.
- Added unit tests for indicator behavior and config loading.

Next likely slice:

- Wire feature snapshots and regime tagging into `BacktestEngine`.
- Replace placeholder `regime_performance.csv` with trade attribution by regime.
- Add V1 report metrics beyond Sharpe where needed: Calmar and Sortino.
