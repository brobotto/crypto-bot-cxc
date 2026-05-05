# Spike A - Freqtrade

Goal: evaluate whether Freqtrade is a practical MVP runner.

Use the common test spec from `doc/design/implementation_plan.md`.

## Current Status

Started: 2026-05-06

Completed:

- Installed `freqtrade==2026.4` in the project virtual environment.
- Added a Freqtrade strategy for EMA 20/100:
  - `strategies/SpikeAEMATrendStrategy.py`
- Added `run_freqtrade_spike.py` to:
  - convert project OHLCV into Freqtrade JSON data
  - generate a temporary Freqtrade config under ignored `user_data/`
  - run Freqtrade backtesting
  - export stable comparison reports
- Added an offline market metadata patch because Freqtrade tries to load exchange markets even for local-data backtests.

## Common Spec Result

- Framework: Freqtrade 2026.4
- Rows loaded from project data: 26,304
- Freqtrade backtest period after startup: 2022-01-05 04:00:00 to 2024-12-31 23:00:00
- Closed trades: 160
- Fill rows/orders: 320
- Final equity: 10080.382191
- Total return: 0.803822%
- Max drawdown: 0.681990%
- Sharpe ratio from exported wallet equity: 0.692913
- Total fees: 32.081764

## Alignment Note

Freqtrade native backtesting did not model the `0.0005` slippage used in the common custom/VectorBT run. A custom-engine no-slippage run produced final equity `10080.38816748003`, only about `0.006 USDT` away from Freqtrade. So execution/signal timing is aligned, but slippage parity is not.

## Command

```powershell
.venv\Scripts\python.exe spikes\spike_a_freqtrade\run_freqtrade_spike.py --input data\ohlcv\BTC_USDT_1h_2022_2024.csv --output-dir spikes\spike_a_freqtrade\reports_full --fee-rate 0.001 --gap-policy forward_fill
```
