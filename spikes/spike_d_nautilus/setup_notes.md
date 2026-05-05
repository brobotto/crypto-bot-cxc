# Setup Notes

## Environment

- Python: 3.13.13 via project `.venv`
- Installed package: `nautilus_trader==1.226.0`
- Windows wheel was available for Python 3.13, so no local Rust build was required.

## Commands Run

```powershell
.venv\Scripts\python.exe -m pip install nautilus_trader
.venv\Scripts\python.exe spikes\spike_d_nautilus\run_nautilus_spike.py --input data\ohlcv\BTC_USDT_1h_2022_2024.csv --output-dir spikes\spike_d_nautilus\reports_full --fee-rate 0.001 --gap-policy forward_fill
```

## Notes

- `pyproject.toml` has optional extra `spike-d` for NautilusTrader.
- The spike uses Nautilus `BacktestEngine` directly, not `BacktestNode` or catalog-based configs.
- The runner uses `TestInstrumentProvider.btcusdt_binance()` to avoid live exchange metadata calls.

