# Setup Notes

## Environment

- Python: 3.13.13 via project `.venv`
- Installed package: `vectorbt==1.0.0`
- VectorBT dependency constraint downgraded pandas from `3.0.2` to `2.3.3`

## Commands Run

```powershell
.venv\Scripts\python.exe -m pip install vectorbt
.venv\Scripts\python.exe spikes\spike_b_vectorbt\run_vectorbt_spike.py --input data\ohlcv\BTC_USDT_1h_2022_2024.csv --output-dir spikes\spike_b_vectorbt\reports_full --fast-period 20 --slow-period 100 --initial-cash 10000 --risk-per-trade 0.01 --fee-rate 0.001 --slippage-rate 0.0005 --gap-policy forward_fill
```

## Notes

- `pyproject.toml` keeps core pandas open at `>=2.2` and places the VectorBT `pandas<3.0` constraint inside optional extra `spike-b`.
- Generated `reports_full/` is ignored by git through the existing spike report ignore rule.
- Stable result files are committed in the spike root.
