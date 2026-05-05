# Crypto Trading Bot — Implementation Plan

> Task breakdown สำหรับ V0 และ V1
> Design spec อยู่ใน `merged_design_spec.md` | Working reference อยู่ใน `design_overview.md`

---

## V0 — Design + Framework Spikes

### ✅ เสร็จแล้ว

- [x] Knowledge base v5 ครบ
- [x] Design decisions สรุป
- [x] Merged design spec พร้อม
- [x] Event contracts กำหนดแล้ว (MarketDataEvent, OrderIntent, FillEvent)
- [x] Gate criteria กำหนดแล้ว

---

### ⬜ Spike Preparation

**Common Test Spec (ใช้กับทุก Spike)**

```
Symbol:    BTC/USDT
Timeframe: 1h
Period:    2022-01-01 ถึง 2024-12-31
Capital:   10,000 USDT
Strategy:  EMA crossover — fast=20, slow=100
Entry:     fast crosses above slow
Exit:      fast crosses below slow
Fee:       0.1%
Slippage:  0.05% basic, 0.1% conservative
Execution: next candle open
Benchmark: buy-and-hold BTC (return, DD, Sharpe, Calmar)
```

**Output files ต่อ Spike (เหมือนกันทุกอัน)**

```
spike_X/
├── setup_notes.md        # ขั้นตอน setup, ปัญหาที่เจอ
├── strategy_code/        # code ที่เขียน
├── backtest_summary.json # metrics หลัก
├── trades.csv
├── equity_curve.csv
├── benchmark_comparison.json
├── limitations.md        # อะไรที่ framework ทำไม่ได้หรือยาก
├── time_spent.md         # เวลาจริงที่ใช้
└── decision_notes.md     # สรุปว่าเหมาะหรือไม่เหมาะ
```

---

### ⬜ Spike A — Freqtrade (2-3 วัน)

**เป้าหมาย:** ประเมินว่า Freqtrade เป็น practical MVP path ได้ไหม

```
[ ] ติดตั้ง Freqtrade + config Binance sandbox
[ ] implement EMA 20/100 strategy
[ ] รัน backtest บน common test spec
[ ] ตรวจ: run Freqtrade lookahead-analysis (ชื่อ subcommand ตรวจสอบตาม version จริง)
[ ] ตรวจ: run Freqtrade recursive-analysis
[ ] รัน dry-run 3-5 วัน
[ ] ทดสอบ Telegram /status /profit
[ ] บันทึก output files ครบ
```

**คำถามที่ต้องตอบ:**
```
Architecture ของ Freqtrade จำกัดอะไร?
ledger/reconciliation depth พอไหม?
urgency mapping ทำได้แค่ไหน?
custom logic เพิ่มได้ง่ายแค่ไหน?
```

---

### ⬜ Spike B — VectorBT (1-2 วัน)

**เป้าหมาย:** ประเมิน research + parameter sweep + Monte Carlo workflow

```
[ ] implement strategy เดิมใน VectorBT
[ ] sweep EMA periods (fast: 10-50, slow: 50-200) — 500+ combinations
[ ] build returns_matrix สำหรับ DSR/PBO ภายหลัง
[ ] รัน Monte Carlo 1000 paths (trade shuffle)
[ ] เปรียบ Sharpe/DD กับ Spike A
[ ] ประเมิน fill model: realistic แค่ไหน?
[ ] บันทึก output files ครบ
```

**คำถามที่ต้องตอบ:**
```
Result ต่างจาก Freqtrade เท่าไหร่?
Fill model ส่งผลต่าง Sharpe เท่าไหร่?
MC workflow ง่ายแค่ไหน เทียบกับ Jesse?
Worth ใช้คู่กับ primary framework?
```

---

### ⬜ Spike C — Custom Mini Engine (3-5 วัน) ← Required

**เป้าหมาย:** พิสูจน์ว่า custom path ทำได้จริง และประเมิน effort จริง

```
Phase 1 — Event contracts (0.5 วัน):
[ ] MarketDataEvent dataclass
[ ] OrderIntent dataclass + Urgency enum
[ ] FillEvent dataclass
[ ] RegimeEvent dataclass
[ ] unit tests สำหรับทุก dataclass

Phase 2 — BrokerInterface + BacktestBroker (1 วัน):
[ ] BrokerInterface abstract class (5 methods)
[ ] BacktestBroker: next-candle fill
[ ] BacktestBroker: slippage model (configurable)
[ ] BacktestBroker: fee model (maker/taker)
[ ] BacktestBroker: full fill next-candle model (required)
[ ] BacktestBroker: partial fill by volume cap (optional — ทำถ้าทัน, ไม่ใช่ spike goal)

Phase 3 — Minimal Pipeline (1.5 วัน):
[ ] OHLCV loader จาก CSV/Parquet
[ ] Feature Engine: EMA(20), EMA(100) — stateless function
[ ] Strategy: EMA crossover → OrderIntent(urgency=NORMAL)
[ ] Minimal Risk Manager: position sizing (fixed %)
[ ] Engine loop: iterate candles → pipeline

Phase 4 — Minimal Ledger + Reports (1 วัน):
[ ] PortfolioLedger: position_manager (open/close)
[ ] PortfolioLedger: trade_log (append-only)
[ ] PortfolioLedger: pnl_calculator (realized)
[ ] Output: trades.csv, equity_curve.csv, summary.json

Phase 5 — Run + Compare (0.5 วัน):
[ ] รัน บน common test spec
[ ] เปรียบ result กับ Spike A/B
[ ] บันทึก output files ครบ
```

**คำถามที่ต้องตอบ:**
```
ใช้เวลาจริงแค่ไหน? (track จริง)
มี infrastructure bug อะไรที่คาดไม่ถึง?
Result ต่างจาก Freqtrade/VectorBT เท่าไหร่? ทำไม?
คุ้มกับ effort เทียบกับ Freqtrade ไหม?
```

---

### ⬜ Spike D — NautilusTrader (3-5 วัน)

**เป้าหมาย:** ประเมิน learning curve และ backtest-live parity จริงๆ

```
[ ] setup: Rust build + Python environment
[ ] implement strategy ใน Actor pattern
[ ] รัน backtest บน common test spec
[ ] เปรียบ result กับ Spike A/B/C
[ ] ประเมิน: setup ยากแค่ไหน? ใช้เวลาเท่าไหร่?
[ ] ประเมิน: API เข้าใจง่ายไหม?
[ ] ประเมิน: backtest-live parity ดีกว่า Freqtrade จริงไหม?
[ ] บันทึก output files ครบ
```

**คำถามที่ต้องตอบ:**
```
Learning curve จริง: กี่วันถึงรัน backtest ได้?
API มี breaking changes บ่อยแค่ไหน?
Worth the complexity สำหรับ project นี้?
```

---

### ⬜ Spike E — Jesse Free Tier (1-2 วัน) — Optional

**เป้าหมาย:** ประเมิน Monte Carlo workflow และ strategy syntax

```
[ ] ติดตั้ง Jesse
[ ] implement strategy เดิม
[ ] รัน backtest บน common test spec
[ ] รัน Monte Carlo (2 modes: trade shuffle + candle)
[ ] เปรียบ MC results กับ VectorBT MC
[ ] ประเมิน: UX ง่ายแค่ไหน? เวลา setup?
[ ] บันทึก output files ครบ
```

**หมายเหตุ:** Jesse live/paper ต้องซื้อ plugin — ทำแค่ backtest + MC ในขั้นนี้

---

### ⬜ Framework Decision Meeting (หลัง Spike ครบ)

```
[ ] รวม decision_notes.md จากทุก Spike
[ ] เปรียบ result matrix:
    Framework | Sharpe | DD | Setup time | Limitations | Recommendation
[ ] ตัดสินใจ: primary framework path
[ ] เขียน framework_decision.md สรุปเหตุผล
[ ] update implementation_plan.md ให้ reflect framework ที่เลือก
```

**Gate ออก V0:**
```
[ ] Spike A-D เสร็จทุกอัน (E optional)
[ ] decision_notes.md ครบทุก Spike
[ ] framework_decision.md เขียนแล้ว
[ ] event contracts draft พร้อม (จาก Spike C)
[ ] BrokerInterface draft พร้อม (จาก Spike C)
[ ] data spec พร้อม (exchange, symbol, timeframe, period)
```

---

## V1 — Backtest Core

> เริ่มหลัง gate V0 ผ่าน — ใช้ framework ที่เลือกจาก Spike

---

### V1.1 — Data Foundation

```
[ ] OHLCV downloader (Binance candidate, via CCXT)
    - download BTC/USDT, ETH/USDT
    - period: 2022-2024 (1h)
    - save ไป Parquet: data/ohlcv/{symbol}_{timeframe}.parquet
    - validate: no gaps, correct timestamps, UTC

[ ] src/crypto_bot_cxc/data/ohlcv_store.py
    - load_candles(symbol, timeframe, start, end) → DataFrame
    - append_candles(...) → update Parquet
    - validate_candles(...) → raise ถ้าไม่ครบ
```

**Done criteria:** โหลด BTC/USDT 1h 2022-2024 ได้ ไม่มี gap

---

### V1.2 — Event Contracts + Feature Engine

```
[ ] src/crypto_bot_cxc/events/models.py
    - MarketDataEvent (timestamp, OHLCV, is_closed)
    - OrderIntent (urgency, side, qty, reason, regime, intent_id)
    - FillEvent (order_id, intent_id, price, qty, fee, is_partial)
    - RegimeEvent (state, confidence, prev_state)
    - unit tests ครบทุก dataclass

[ ] src/crypto_bot_cxc/data/feature_engine.py (stateless functions)
    - calc_ema(prices, period) → Series
    - calc_adx(high, low, close, period) → Series
    - calc_atr(high, low, close, period) → Series
    - calc_bb_width(close, period, std) → Series
    - unit tests: compare กับ known values
```

**Done criteria:** unit tests pass, feature values match reference implementation

---

### V1.3 — Regime Detector

```
[ ] src/crypto_bot_cxc/regime/models.py
    - RegimeState enum (8 states)

[ ] src/crypto_bot_cxc/regime/detector.py
    - detect_regime(features, config) → RegimeState
      ← รับ config ทั้งหมดจาก outside ไม่ hardcode
    - unit tests: test ทุก state path

[ ] config/strategy_config.yaml
    - adx_trend_threshold: 25
    - adx_sideways_threshold: 20
    - high_vol_multiplier: 1.5
    - squeeze_multiplier: 0.5
    - min_volume_ratio: 0.3
    - max_spread_bps: 50
```

**Done criteria:** detect_regime() return ถูก state ใน unit tests ครบ 8 cases

---

### V1.4 — BrokerInterface + BacktestBroker

```
[ ] src/crypto_bot_cxc/broker/base.py
    - BrokerInterface (abstract)
      submit_order(order: ConcreteOrder) → order_id   # ExecutionPlanner transforms Intent → ConcreteOrder before this
      cancel_order(order_id) → bool
      get_order_status(order_id) → OrderStatus
      get_balance() → Balance
      get_open_orders() → List[Order]
      get_fills_since(ts) → List[FillEvent]

[ ] src/crypto_bot_cxc/broker/backtest_broker.py
    - BacktestBroker implements BrokerInterface
    - next-candle execution (ไม่มี lookahead)
    - fill models (configurable):
        market: next_open * (1 + slippage + impact)
        limit:  fills เมื่อ low < limit_price * (1 - buffer)
    - fee model: maker/taker rate จาก config
    - partial fill simulation (by volume cap) ← optional, V1.4 ค่อยใส่
    - unit tests: fill logic ทุก case

[ ] tests/test_backtest_broker.py
    - test market fill: ราคาถูก, ถูก candle, fee ถูก
    - test limit fill: fill/no-fill boundary
    - test post-only: reject logic
    - test partial fill ← optional
```

**Done criteria:**
- unit tests pass สำหรับ fill price, fee calculation
- no same-candle execution: signal จาก candle N execute ได้เร็วที่สุดที่ open ของ candle N+1
- ตรวจด้วย test: สร้าง fake data ที่รู้ answer แล้ว verify ว่า engine ไม่ใช้ close ของ candle ที่ signal เกิด

---

### V1.5 — Risk Manager

```
[ ] src/crypto_bot_cxc/risk/position_sizer.py
    - calc_position_size(balance, risk_pct, entry, stop) → Decimal
    - calc_atr_stop(entry, atr, multiplier) → Decimal
    - unit tests

[ ] src/crypto_bot_cxc/risk/circuit_breaker.py
    - check_daily_loss(pnl, limit) → bool
    - check_max_drawdown(equity, peak, limit) → bool
    - check_consecutive_losses(count, limit) → bool

[ ] src/crypto_bot_cxc/risk/manager.py
    - validate(intent, portfolio_state, config) → approved Intent | Reject
    - ห้ามให้ strategy bypass ทางนี้

[ ] config/strategy_config.yaml (เพิ่ม)
    - risk_per_trade: 0.01
    - atr_multiplier: 2.0
    - daily_loss_limit: 0.02
    - max_drawdown: 0.10
    - max_open_positions: 3
```

**Done criteria:** risk_manager.py reject order เมื่อ criteria ไม่ผ่าน, unit tests ครบ

---

### V1.6 — Portfolio Ledger

```
[ ] src/crypto_bot_cxc/ledger/models.py
    - Position dataclass (Decimal fields)
    - Trade dataclass (append-only record)
    - Balance dataclass

[ ] src/crypto_bot_cxc/ledger/position_manager.py
    - open_position(fill) → Position
    - update_position(fill) → Position (partial fill)
    - close_position(fill) → closed Position
    - get_unrealized_pnl(position, current_price) → Decimal

[ ] src/crypto_bot_cxc/ledger/trade_log.py
    - append(fill) → Trade (append-only)
    - get_all() → List[Trade]

[ ] src/crypto_bot_cxc/ledger/pnl_calculator.py
    - calc_realized(entry_fill, exit_fill) → Decimal
    - calc_avg_entry(fills) → Decimal (weighted avg)
    - calc_equity(balance, positions, prices) → Decimal

[ ] src/crypto_bot_cxc/ledger/portfolio_ledger.py
    - on_fill(fill_event) → PortfolioState
    - get_state() → PortfolioState
    - snapshot() → dict (สำหรับ save)
```

**Done criteria:** avg_entry ถูกกับ partial fills, realized PnL ถูกกับ fee, unit tests pass

---

### V1.7 — Strategy + ExecutionPlanner

```
[ ] src/crypto_bot_cxc/execution/planner.py
    - plan(intent, market_ctx, risk_state, caps) → ConcreteOrder
    - urgency → order type mapping (5 levels V1)
    - spread_too_wide guard
    - data_stale guard

[ ] src/crypto_bot_cxc/strategy/base.py
    - BaseStrategy (abstract)
    - on_candle(event, features, regime) → List[OrderIntent] | None

[ ] src/crypto_bot_cxc/strategy/ema_trend.py
    - EMAStrategy implements BaseStrategy
    - signal logic: EMA crossover → NORMAL entry
    - ไม่รู้จัก Broker, ไม่รู้จัก exchange

[ ] src/crypto_bot_cxc/strategy/dca_baseline.py (benchmark fixture)
[ ] src/crypto_bot_cxc/strategy/grid_prototype.py (benchmark fixture)
```

**Done criteria:** EMA strategy ไม่มี lookahead, ส่ง OrderIntent ไม่ใช่ order type

---

### V1.8 — Backtest Engine + Reports

```
[ ] src/crypto_bot_cxc/engine/backtest_engine.py
    - run(data, strategy, risk_mgr, broker, ledger, config) → Report
    - iterate candles ตามลำดับเวลา (ห้ามข้าม)
    - warmup period: skip max(all_lookback_periods) candles แรก
    - บันทึก regime ทุก candle

[ ] src/crypto_bot_cxc/reports/backtest_report.py
    - generate(ledger, equity_curve, regimes) → dict
    - output: trades.csv, equity_curve.csv, summary.json
    - output: monthly_returns.csv
    - output: regime_performance.csv ← สำคัญที่สุด
      columns: regime, trades, win_rate, avg_pnl, profit_factor, sharpe

[ ] src/crypto_bot_cxc/reports/benchmark.py
    - compare_vs_bah(equity_curve, bah_curve) → dict
    - metrics: return, max_drawdown, sharpe, calmar, sortino
    - ไม่ใช้ Sharpe เดี่ยว — multi-metric comparison
```

**Done criteria:** รัน EMA strategy บน 2022-2024 แล้วออก 5 files ครบ

---

### V1.9 — Strategy Validation Gate

```
[ ] validation/oos_validator.py
    - split_oos(data, oos_ratio=0.2) → (train, test)
    - compare_sharpe(train_sharpe, oos_sharpe, threshold=0.6) → bool

[ ] validation/monte_carlo.py
    - shuffle_trades(trades, n_sim=1000) → List[equity_curve]
    - calc_5th_pct_equity(simulations) → Decimal
    - calc_risk_of_ruin(simulations, threshold=0.1) → float
    - calc_fee_breakeven(trades, current_fee) → float

[ ] validation/sensitivity.py
    - sweep_param(strategy, data, param, values) → returns_matrix
    - sensitivity_report(matrix) → dict

[ ] validation/research_log.py
    - log_variant(params, metrics) → append to research_log.csv
    - ← บันทึกทุก variant ที่ลอง ไม่ใช่แค่ตัวที่ดี
```

**Strategy Validation Checklist (ต้องผ่านก่อน V2):**

```
HARD GATES (ต้องผ่านทุกข้อ — ถ้า fail ให้แก้ก่อน):
[ ] ไม่มี lookahead bias (engine sequencing test)
[ ] warmup period ครบ (skip max lookback period)
[ ] OOS Sharpe ≥ 60% ของ in-sample
[ ] Monte Carlo: 5th pct equity > 0
[ ] Monte Carlo: risk of ruin < 5%
[ ] Fee breakeven > 2× current fee
[ ] Parameter sensitivity ±20% ไม่ทำให้ Sharpe ลด > 30%

WATCH / TARGET (positive signal แต่ไม่ใช่ hard gate):
[ ] Benchmark vs BTC (multi-metric: return, DD, Sharpe, Calmar)
    → เปรียบให้ครบ แต่ไม่ต้องชนะทุก metric
[ ] regime_performance.csv: PF > 1.2 ใน regimes ที่ ≥ 20 trades
    → ถ้าไม่ถึงให้ investigate เหตุผล ไม่ใช่ auto-reject
[ ] DSR > 0 ถ้าลอง > 5 variants (heuristic)
[ ] research_log.csv บันทึกทุก variant ครบ
```

---

### V1 Gate → V2

```
ผ่าน Strategy Validation Gate ทุกข้อบังคับ
ระบบ backtest รันได้ไม่มี bug ที่รู้อยู่
5 output files ออกครบ
regime_performance.csv มีข้อมูลพอดูแนวโน้ม
```

---

## Timeline Estimate

| Phase | V0 | V1.1-1.4 | V1.5-1.7 | V1.8-1.9 |
|-------|----|-----------|-----------| ---------|
| เวลา | 2-3 สัปดาห์ | 1 สัปดาห์ | 1-2 สัปดาห์ | 1 สัปดาห์ |
| Output | Framework decision | Data + Broker | Risk + Strategy | Reports + Validation |

**รวม V0+V1: ประมาณ 6-8 สัปดาห์** (ขึ้นกับผล Spike C)

---

## Dependency Map

```
V1.1 (Data) ──────────────────────────────────┐
V1.2 (Events + Feature) ──────────────────────┤
V1.3 (Regime) ← V1.2                         ├── V1.8 (Engine)
V1.4 (Broker) ← V1.2                         ├── V1.8 (Engine)
V1.5 (Risk) ← V1.2                           ├── V1.8 (Engine)
V1.6 (Ledger) ← V1.2                         ├── V1.8 (Engine)
V1.7 (Strategy + Planner) ← V1.2, V1.3, V1.4 ┘
                                               ↓
                                          V1.9 (Validation)
```

V1.1 และ V1.2 สามารถทำพร้อมกันได้ ที่เหลือ depend on V1.2

---

*Implementation Plan v1.0 — สำหรับ V0 และ V1*
*V2-V6 plan จะเขียนหลังจาก V1 validation gate ผ่าน*
