# Setup Notes

## Environment

- Python: 3.13.13 via `py`
- Virtual environment: project `.venv`
- Package install: editable install with dev extras

## Commands Run

```powershell
git init
py -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -B -m pytest -q -p no:cacheprovider
.venv\Scripts\python -m ruff check --no-cache .
.venv\Scripts\python -m mypy --no-incremental src tests
.venv\Scripts\python -m crypto_bot_cxc.cli.download_ohlcv --exchange binance --symbol BTC/USDT --timeframe 1h --start 2024-01-01 --end 2025-01-01 --output data\ohlcv\BTC_USDT_1h_2024.csv
.venv\Scripts\python -m crypto_bot_cxc.cli.spike_c_backtest --input data\ohlcv\BTC_USDT_1h_2024.csv --output-dir spikes\spike_c_custom_mini_engine\reports_2024 --fast-period 20 --slow-period 100 --initial-cash 10000 --risk-per-trade 0.01 --fee-rate 0.001 --slippage-rate 0.0005
.venv\Scripts\python -m crypto_bot_cxc.cli.spike_c_backtest --input data\ohlcv\BTC_USDT_1h_2022_2024.csv --output-dir spikes\spike_c_custom_mini_engine\reports_full --fast-period 20 --slow-period 100 --initial-cash 10000 --risk-per-trade 0.01 --fee-rate 0.001 --slippage-rate 0.0005 --gap-policy forward_fill
```

## Notes

- Python 3.13 works for the custom engine skeleton and installed current `ccxt`, `pandas`, and `pyarrow`.
- Framework spikes may still require older Python depending on framework support, especially Freqtrade or NautilusTrader.
- Binance BTC/USDT 1h full 2022-2024 has one missing hourly candle in downloaded public data:
  `2023-03-24T13:00:00Z`.
- The loader defaults to `gap_policy=strict`. Full 2022-2024 run requires explicit `--gap-policy forward_fill`.
- `forward_fill` is capped at 3 synthetic candles by default; larger gaps should fail until a stricter repair policy is chosen.
