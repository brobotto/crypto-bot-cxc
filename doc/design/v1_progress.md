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

## 2026-05-08

Continued V1 backtest/report foundation. Still no paper/live exchange path.

Completed in this slice:

- Added `FeatureSnapshot` and `build_feature_snapshots(...)`.
- Backtest engine now precomputes per-candle features once and records:
  - `feature_snapshots`
  - `regime_curve`
  - `trade_regimes`
- Engine can use rule-based `RegimeConfig` when provided, while keeping the
  fixed `regime_provider` fallback for spike/backward compatibility.
- Report output now writes real `regime_performance.csv` from closed trades when
  regime attribution exists.
- `trades.csv` now includes a `regime` column.
- Documented that backtest feature snapshots use `spread=0` until bid/ask data
  exists, and that ADX is most reliable after roughly `2 * period` samples.
- Renamed regime performance `sharpe` column to `trade_sharpe` to avoid
  confusion with annualized equity-curve Sharpe.

Next likely slice:

- Add a V1 backtest CLI that loads `config/strategy_config.yaml` directly.
- Add Calmar/Sortino benchmark metrics.
- Split V1 risk circuit breaker work into explicit `risk/circuit_breaker.py`.

## 2026-05-08 CLI Slice

Added the first V1 runner entrypoint:

- `cxc-backtest` now points to `crypto_bot_cxc.cli.backtest:main`.
- The runner loads `config/strategy_config.yaml` directly.
- It supports one-symbol V1 backtests from CSV/Parquet OHLCV.
- It uses the V1 regime detector path via `RegimeConfig`.
- It keeps Spike C runner intact as a reproducibility/reference command.
- `daily_loss_limit`, `max_drawdown`, and `atr_multiplier` are loaded and
  validated, but enforcement is explicitly deferred to the V1 risk/circuit
  breaker slice.

Example:

```powershell
cxc-backtest --input data/ohlcv/BTCUSDT_1h.parquet --output-dir reports/v1_btc
```

Next likely slice:

- Add Calmar/Sortino benchmark metrics.
- Split V1 risk circuit breaker work into explicit `risk/circuit_breaker.py`.
- Add a tiny smoke dataset/fixture or documented command for local V1 smoke runs.

## 2026-05-08 Report Metrics Slice

Expanded core report metrics beyond Sharpe:

- `summary.json` now includes `sortino_ratio` and `calmar_ratio`.
- Benchmark fields now include `benchmark_sortino_ratio` and
  `benchmark_calmar_ratio`.
- `benchmark_comparison.json` now includes Sharpe, Sortino, and Calmar for both
  strategy and buy-and-hold benchmark.

Notes:

- Calmar is currently `total_return_pct / max_drawdown_pct`.
- Sortino is annualized from period returns with downside deviation against a
  zero target return.

Next likely slice:

- Split V1 risk circuit breaker work into explicit `risk/circuit_breaker.py`.
- Add a tiny smoke dataset/fixture or documented command for local V1 smoke runs.

## 2026-05-08 Risk Circuit Breaker Slice

Added V1 entry-blocking circuit breaker:

- New `risk/circuit_breaker.py` module tracks:
  - daily loss limit
  - max drawdown
  - consecutive realized losses
- `RiskManager` now blocks new BUY intents when the breaker trips.
- SELL intents are still allowed so existing long positions can exit.
- `config/strategy_config.yaml` now includes `max_consecutive_losses`.
- Backtest engine observes current equity on every candle before strategy
  decisions, so daily loss and drawdown state do not depend on BUY signals
  appearing first.

Current scope:

- The breaker only blocks entries.
- It does not flatten positions, cancel orders, or force reduce-only mode yet.
- Engine passes candle timestamp and current equity into risk validation.

Next likely slice:

- Add a tiny smoke dataset/fixture or documented command for local V1 smoke runs.
- Add position sizing with ATR stop distance instead of simple cash fraction.
