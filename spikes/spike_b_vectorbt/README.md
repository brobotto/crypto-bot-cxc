# Spike B - VectorBT

Goal: evaluate research, parameter sweep, and Monte Carlo workflow.

Use the common test spec from `doc/design/implementation_plan.md`.

## Current Status

Started: 2026-05-06

Completed:

- Installed `vectorbt==1.0.0` in the project virtual environment.
- Added `run_vectorbt_spike.py` for the common EMA 20/100 BTC/USDT 1h spec.
- Uses the same project OHLCV loader and explicit `gap_policy=forward_fill`.
- Shifts signals by one bar and fills at next candle open through VectorBT.
- Writes the same report shape used by Spike C:
  - `trades.csv`
  - `equity_curve.csv`
  - `summary.json`
  - `benchmark_comparison.json`
  - `monthly_returns.csv`
  - `regime_performance.csv`
- Writes stable comparison files:
  - `backtest_summary.json`
  - `benchmark_comparison.json`
  - `parameter_sweep.csv`

## Common Spec Result

- Framework: VectorBT 1.0.0
- Pandas: 2.3.3
- Rows: 26,304
- Orders/fills: 320
- Final equity: 10064.123594877297
- Total return: 0.6412359487729669%
- Max drawdown: 0.7304503636210711%
- Sharpe ratio: 0.5529814986247046
- Buy-and-hold return: 100.56528477608411%
- Buy-and-hold Sharpe ratio: 0.7003678423393424

## Command

```powershell
.venv\Scripts\python.exe spikes\spike_b_vectorbt\run_vectorbt_spike.py --input data\ohlcv\BTC_USDT_1h_2022_2024.csv --output-dir spikes\spike_b_vectorbt\reports_full --fast-period 20 --slow-period 100 --initial-cash 10000 --risk-per-trade 0.01 --fee-rate 0.001 --slippage-rate 0.0005 --gap-policy forward_fill
```
