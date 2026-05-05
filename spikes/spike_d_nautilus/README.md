# Spike D - NautilusTrader

Goal: evaluate NautilusTrader learning curve, event model, and backtest-live parity for the common EMA 20/100 test spec.

## Scope

- BTC/USDT 1h, 2022-01-01 through 2024-12-31.
- EMA 20/100 long-only crossover.
- 10,000 USDT initial cash.
- 1% cash sizing per entry.
- 0.1% taker fee.
- No rate-based slippage in this spike.

## Run

```powershell
.venv\Scripts\python.exe spikes\spike_d_nautilus\run_nautilus_spike.py --input data\ohlcv\BTC_USDT_1h_2022_2024.csv --output-dir spikes\spike_d_nautilus\reports_full --fee-rate 0.001 --gap-policy forward_fill
```

## Output

- `backtest_summary.json`
- `benchmark_comparison.json`
- `reports_full/equity_curve.csv`
- `reports_full/trades.csv`
- `reports_full/summary.json`
- `reports_full/monthly_returns.csv`
- `reports_full/regime_performance.csv`

