# Setup Notes

## Environment

- Python: 3.13.13 via project `.venv`
- Installed package: `freqtrade==2026.4`
- TA-Lib wheel installed successfully on Windows/Python 3.13

## Commands Run

```powershell
.venv\Scripts\python.exe -m pip install freqtrade
.venv\Scripts\python.exe spikes\spike_a_freqtrade\run_freqtrade_spike.py --input data\ohlcv\BTC_USDT_1h_2022_2024.csv --output-dir spikes\spike_a_freqtrade\reports_full --fee-rate 0.001 --gap-policy forward_fill
.venv\Scripts\python.exe -m crypto_bot_cxc.cli.spike_c_backtest --input data\ohlcv\BTC_USDT_1h_2022_2024.csv --output-dir spikes\spike_c_custom_mini_engine\reports_full_no_slippage --fast-period 20 --slow-period 100 --initial-cash 10000 --risk-per-trade 0.01 --fee-rate 0.001 --slippage-rate 0 --gap-policy forward_fill
```

## Notes

- `pyproject.toml` now has optional extra `spike-a` for Freqtrade.
- Generated `user_data/` and report folders are ignored by git.
- Freqtrade backtesting attempted to load Binance markets from `api.binance.com` even with local OHLCV data. The runner patches market metadata in-process to keep the spike deterministic/offline.
