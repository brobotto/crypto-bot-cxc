# Crypto Trading Bot — Merged Design (v1.0)

> Detailed spec — gate criteria, urgency mapping, module structure, regime code
> ใช้คู่กับ design_overview.md (working reference) และ implementation_plan.md
> วันที่: 2026-05-05

---

## สารบัญ

1. [ทิศทางหลักและหลักการ](#1-ทิศทางหลักและหลักการ)
2. [Version Roadmap](#2-version-roadmap)
3. [Gate Criteria ต่อ Version](#3-gate-criteria-ต่อ-version)
4. [Architecture](#4-architecture)
5. [Regime Detection — Role ต่อ Version](#5-regime-detection--role-ต่อ-version)
6. [Strategy V1](#6-strategy-v1)
7. [Exchange Decision](#7-exchange-decision)
8. [ภาษาและ Framework](#8-ภาษาและ-framework)
9. [ตัวเลือกที่ยังเปิดอยู่](#9-ตัวเลือกที่ยังเปิดอยู่)

---

## 1. ทิศทางหลักและหลักการ

### ภาพรวม

```
Backtest-first
Spot-only (V1-V4)
Modular monolith
Unified broker interface
Risk-first + Ledger-centric
```

### การตัดสินใจที่ lock แล้ว

| ด้าน             | การตัดสินใจ          | หมายเหตุ                         |
| ---------------- | -------------------- | -------------------------------- |
| Market type      | Spot-only            | Futures พิจารณา V6+              |
| Direction        | Long-only            | Short ทีหลัง                     |
| Pairs V1         | BTC/USDT, ETH/USDT   | ไม่มี survivorship bias          |
| Risk per trade   | 0.5-1%               | Conservative baseline            |
| Daily loss limit | 2%                   | V1 default                       |
| Max drawdown     | 10%                  | V1 default                       |
| Capital reserve  | 40% default          | ปรับได้ตาม stage และ risk budget |
| Language         | Python default V1-V5 | Rust/advanced V6 ถ้าจำเป็น       |

### กฎเหล็กที่ห้ามฝ่าฝืน

```
1. Strategy ห้ามส่ง order ตรง exchange — ต้องผ่าน Risk Manager
2. ทุก Fill Event เท่านั้นที่เปลี่ยน Position state
3. Never skip reconciliation — แม้ restart 30 วินาที
4. Always start PAUSED ก่อน ACTIVE
5. Decimal ไม่ใช่ float ทุกตัวเลขเงิน
6. ห้าม generate signal บน candle ที่ is_closed = False
7. ห้าม enable withdrawal permission บน bot API key
8. ห้าม hardcode threshold ใน code — ทุกค่าต้องเป็น config
```

---

## 2. Version Roadmap

### V0 — Research + Spikes + Design Contracts ← ปัจจุบัน

**เป้าหมาย:** มีข้อมูลพอตัดสินใจ framework/architecture และมี working prototype ที่จับต้องได้

```
✅ Knowledge base ครบ (v5)
✅ Design decisions สรุปแล้ว

⬜ Framework Spikes A-D (common test spec เดียวกัน)
    Spike A: Freqtrade           (2-3 วัน)
    Spike B: VectorBT            (1-2 วัน)
    Spike C: Custom mini engine  (3-5 วัน) ← required
    Spike D: NautilusTrader      (3-5 วัน)
    Spike E: Jesse free tier     (1-2 วัน, optional)

⬜ Custom Mini Engine (Spike C ผลิต)
    MarketDataEvent, OrderIntent, FillEvent dataclasses
    BacktestBroker prototype (next-candle fill)
    BrokerInterface draft
    Minimal Risk Manager
    Minimal Portfolio Ledger

⬜ Spike Common Test Spec:
    Symbol: BTC/USDT | Timeframe: 1h | Period: 2022-2024
    Capital: 10,000 USDT | Strategy: EMA 20/100
    Fee: 0.1% | Slippage: 0.05% basic, 0.1% conservative
    Execution: next candle open | Benchmark: buy-and-hold BTC

⬜ Output files ต่อ Spike:
    setup_notes.md, strategy_code/, backtest_summary.json
    trades.csv, equity_curve.csv, benchmark_comparison.json
    limitations.md, time_spent.md, decision_notes.md
```

**Gate ออก V0:** Spikes เสร็จครบ + framework/architecture path ตัดสินใจ + event contracts draft พร้อม

---

### V1 — Backtest Core

**เป้าหมาย:** ระบบ backtest ที่ครบและถูกต้อง — validate strategy ก่อนแตะ live data

```
Components:
  OHLCV downloader (Parquet storage)
  Feature / Indicator Engine
  Regime Detector (rule-based, 8 states)
  Strategy Engine — 1 primary strategy (EMA Trend)
  BacktestBroker (next-candle + slippage + fee)
  Risk Manager (ATR stop, circuit breaker)
  Portfolio Ledger (position, P&L, reconciliation skeleton)
  Backtest Reports (5 output files)

Benchmark fixtures (ไม่ใช่ production, ใช้เปรียบเทียบ):
  DCA baseline
  Simple Grid prototype

Output files:
  trades.csv
  equity_curve.csv
  summary.json
  monthly_returns.csv
  regime_performance.csv ← สำคัญมาก
```

**Strategy Validation Gate (ภายใน V1 ก่อนออก V2):**

```
✅ OOS Sharpe ≥ 60% ของ in-sample
✅ Monte Carlo: 5th pct equity > 0
✅ Monte Carlo: risk of ruin < 5%
✅ Fee breakeven > 2× current fee
✅ Parameter sensitivity ±20% ไม่ทำให้ Sharpe ลด > 30%
✅ DSR > 0 ถ้าลอง > 5 variants (heuristic ไม่ใช่ hard gate)
✅ Benchmark vs buy-and-hold BTC (multi-metric):
   return, max drawdown, Sharpe, Calmar — ดูทุกด้าน ไม่ใช่แค่ Sharpe เดียว
⬡ regime_performance.csv (watch/target — ไม่ใช่ hard gate):
   PF > 1.2 ใน regimes ที่มี ≥ 20 trades = positive signal
   ถ้าไม่ถึงให้ investigate ไม่ใช่ auto-reject
   อย่างน้อยใน 2 regimes ที่ significant (≥ 20 trades)
```

---

### V2 — Paper Trading Core

**เป้าหมาย:** validate execution code + latency + reconciliation กับ live market data โดยไม่ใช้เงินจริง

```
Components เพิ่ม:
  PaperBroker (live price + simulated fills)
    Fill models: Market = ask×(1+slip), Limit fills เมื่อ ask ≤ limit
    Latency model (config profiles, ไม่ใช่ค่าตายตัว):
    decision_latency, network_latency, exchange_ack_latency
    default estimates: ~5ms, ~50ms, ~20ms — ปรับตาม VPS location จริง
  Live WebSocket data stream
  Bot state machine (6 states: BOOTING→RECONCILING→PAUSED→ACTIVE↔REDUCE_ONLY, HALTED)
  Startup reconciliation (14 ขั้นตอน)
  Software DMS watchdog
  Telegram alerts + remote commands
    /status /positions /pnl /pause_entries /halt
    /resume_entries ← ต้องมี explicit confirmation step + audit log
                      เพราะเป็นคำสั่งเปิด risk ไม่ใช่ one-tap
    ตัวอย่าง flow: /resume_entries → bot ตอบ "confirm? ส่ง /confirm_resume ภายใน 60s"
  Structured JSON logs
```

**Regime role ใน V2:** เพิ่ม filter ปลอดภัย

- `NO_TRADE` → ไม่เปิด position ใหม่
- spread/liquidity แย่ → skip entry
- volatility สูงผิดปกติ → ลด size หรือ pause

**Gate V2 → V3 (Micro Live):**

```
Signal match rate ≥ 90% ของ backtest signals (paper vs backtest logic)
Paper Sharpe ≥ 50% ของ backtest out-of-sample (Good: ≥ 70%)
Fill rate ≥ 90%
Order reject rate < 1%
Slippage actual: 0.5×-2.0× ของ modeled
Win rate ±10pp ของ backtest
Min: 50+ trades AND 30+ calendar days
   Preferred: 60+ days ถ้า trade count ต่ำ
   ห้าม: < 20 trades เข้า live ไม่ว่าจะกี่วัน

HARD GATES (zero tolerance):
  Unexpected/orphan/unreconciled position = 0
  Critical ledger mismatch = 0
  Drift tier ≤ Warning
```

---

### V3 — Micro Live Spot (2-5% Capital)

**เป้าหมาย:** ยืนยัน execution จริงกับ real fills ในปริมาณน้อยมาก — discovery phase ก่อน scale

```
Components เพิ่ม:
  LiveBroker (CCXT REST + native WebSocket)
    retry + clientOrderId + partial fill handling
  Exchange comparison ก่อน deploy:
    Binance vs OKX/Kraken — API, DMS, fee, restrictions
  Security gate ครบก่อน live:
    subaccount แยก
    IP whitelist
    withdrawal permission = OFF
    secret scanning ผ่าน
    rollback procedure พร้อม
  Kill switch (EMERGENCY)
  Prometheus metrics exporter
```

**Regime role ใน V3-V4:** risk scaler สำหรับ active strategy ใน V1-V4

```
SIDEWAYS_LOW_VOL    → position size ปกติ (1.0×)
SIDEWAYS_HIGH_VOL   → ลด position size (0.7×)
UPTREND_LOW_VOL     → position size ปกติ (1.0×)
UPTREND_HIGH_VOL    → ลด position size (0.7×)
DOWNTREND_*         → ลด exposure มาก (0.25-0.5×) ไม่เปิด long ใหม่
BREAKOUT_WATCH      → ระวัง entry (0.5×)
NO_TRADE            → pause entries ทุก strategy (0×)
```

> Strategy-specific routing (Grid / Trend ต่างกัน) อยู่ใน V5 ไม่ใช่ที่นี่

**Gate V3 → V4 (Controlled Live):**

```
Live Sharpe ≥ 70% ของ paper (Acceptable: 50-70%)
Live slippage ≤ 2× paper slippage
Order reject rate < 1-2%
Capital scaling consistency: P&L per unit ≈ paper ±20%
Drift tier ≤ Warning ตลอด 4 สัปดาห์
Min duration: 60 วัน micro live หรือ 50+ trades

HARD GATES:
  Unexpected/orphan/unreconciled position = 0
  Critical ledger mismatch = 0
```

---

### V4 — Controlled Live + Calibration Gates + Capital Scaling

**เป้าหมาย:** scale capital อย่างมีระเบียบ + full monitoring + drift detection จริง

```
Components เพิ่ม:
  Calibration Gate Engine (automated gate tracking)
  DriftMonitor (4 types: Data, Execution, Concept, Performance)
  Capital Scaling Manager
  Grafana + Loki full observability stack
  Deployment rollback procedure
  Periodic reconciliation (full cadence)
```

**Capital Scaling Protocol:**

```
2-5%  → เริ่มจาก V3 micro live
10%   → V3 stage ผ่าน 30 วัน + drift ≤ Watch
25%   → Gate V3→V4 ผ่าน + 60 วันรวม
50%   → Gate 4-week stable + ไม่มี ledger mismatch
100%  → 50% stage ผ่าน 30 วัน + drift stable

ถ้า Drift ขึ้น Critical → roll back capital ลง 1 ขั้น ทันที
```

**Gate V4 → V5 (Multi-Strategy):**

```
regime_performance.csv มีข้อมูลพอ (≥ 50 trades ต่อ regime หลัก)
Strategy มี PF > 1.0 ใน 2+ regimes อย่างน้อย
Drift baseline stable (baseline จาก 90+ วัน หรือ 100+ trades)
Walk-forward retest บน recent data ผ่าน
Capital ≥ 50% allocated อย่างน้อย 30 วัน โดยไม่มี emergency halt
```

---

### V5 — Multi-Strategy + Regime Router

**เป้าหมาย:** ใช้ regime เป็น strategy router จริงๆ โดยอิงจากข้อมูลจาก V1-V4

```
Components เพิ่ม:
  Strategy Router (regime → active strategies)
  Risk Budget per Strategy
  Capital Allocator (regime-aware)
  HMM Regime Detector (upgrade จาก rule-based)
  DSR/PBO full implementation (validation roadmap phase 2 — ดู Section 22 ใน KB)
```

**Regime role ใน V5:** strategy router ตาม data

```
ข้อมูลจาก regime_performance.csv บอกว่า:
  SIDEWAYS_LOW_VOL  → Grid (PF 1.8, 62% win rate)
  UPTREND_LOW_VOL   → EMA Trend (PF 3.2, 78% win rate)
  DOWNTREND_*       → DCA only หรือ pause (PF 0.3-0.6)

Strategy Router ใช้ข้อมูลนี้ ไม่ใช่ hardcode assumption
ถ้า PF < 1.0 ใน regime ไหน → disable strategy นั้นใน regime นั้น
ถ้า trades < 20 ใน regime ไหน → ยังไม่มีข้อมูลพอ ใช้ conservative default
```

---

### V6 — Advanced Execution / Futures / AI Analyst

**เป้าหมาย:** ขยายไปยัง futures, execution algorithms, และ AI layer เมื่อ core stable แล้ว

```
พิจารณา (ยังไม่ตัดสิน):
  Futures support + Exchange DMS
  TWAP / Iceberg execution
  Funding rate monitoring
  AI Analyst layer (ไม่ใช่ execution authority)
  Rust extension ถ้า latency < 1ms จำเป็น
  Microservices ถ้า multi-bot / multi-exchange จริงๆ
  NautilusTrader adoption ถ้า HFT-adjacent
```

---

## 3. Gate Criteria ต่อ Version

### Gate 0 → V1 (เข้า Backtest Core)

```
Spike A-D เสร็จ พร้อม decision_notes.md ทุก spike
Framework/architecture path ตัดสินใจแล้ว
Event contracts draft พร้อม (MarketDataEvent, OrderIntent, FillEvent)
Custom mini engine (Spike C) รัน backtest ได้
Data spec พร้อม (exchange, symbol, timeframe, period)
```

### Strategy Validation Gate (ภายใน V1 ก่อน Gate V1→V2)

ดูรายละเอียดใน V1 section ด้านบน

### Gate V1 → V2

```
ผ่าน Strategy Validation Hard Gates ทุกข้อ (ดูรายละเอียดใน V1.9)
ระบบ backtest รันได้ไม่มี known bug
Output files ครบ: trades.csv, equity_curve.csv, summary.json,
                  monthly_returns.csv, regime_performance.csv
regime_performance.csv มีอยู่และ run ครบ
   (regimes ที่มี < 20 trades ให้ mark "insufficient data" ไม่ใช่ fail gate)
   sample size per regime เป็น hard requirement ก่อน V5 router ไม่ใช่ก่อน V2
```

### Gate V2 → V3, V3 → V4, V4 → V5

ดูรายละเอียดใน section ของแต่ละ version

### Hard Gates (บังคับทุก gate)

```
Unexpected/orphan/unreconciled position = 0
Critical ledger mismatch = 0
Drift tier ≤ Warning (สำหรับ V3+)
```

---

## 4. Architecture

### 4 Patterns ที่ผสมกัน

| Pattern                       | Role                           | ใช้ใน                                    |
| ----------------------------- | ------------------------------ | ---------------------------------------- |
| Modular Monolith              | โครงสร้างหลัก                  | V1-V5 ทั้งหมด                            |
| Pipeline / Layered            | flow ทิศทางเดียว               | ทุก version                              |
| Event-inspired Internals      | module คุยกันผ่าน typed events | ทุก version                              |
| Microservice-ready Boundaries | interface ชัด พร้อม extract    | design ตั้งแต่แรก, extract V6+ ถ้าจำเป็น |

### Pipeline Flow (คงที่ทุก version — เปลี่ยนแค่ Broker)

```
Exchange / WebSocket
    ↓ raw OHLCV
Data Layer (validate · Parquet/SQLite · normalize)
    ↓ MarketDataEvent (is_closed=True เท่านั้น)
Feature / Indicator Engine (ADX · BBW · EMA · ATR · Volume)
    ↓ FeatureSet
Regime Detector (rule-based 8 states → HMM V5)
    ↓ RegimeEvent (state + confidence)
Strategy Engine (ไม่รู้ว่า backtest/paper/live)
    ↓ OrderIntent (urgency + reason + regime)
Risk Manager (ห้าม bypass เด็ดขาด)
    ↓ approved OrderIntent
ExecutionPlanner (urgency → order type)
    ↓ ConcreteOrder
Broker Interface ← จุดเดียวที่ swap ระหว่าง version
    BacktestBroker (V1)
    PaperBroker (V2)
    LiveBroker (V3+)
    ↓ FillEvent
Portfolio Ledger (single source of truth)
    ↓ PortfolioState
Monitoring / Alerting
```

### Module Structure

```
crypto-bot/
├── data/
│   ├── exchange_client.py   # CCXT wrapper
│   ├── ws_manager.py        # WebSocket + reconnect
│   ├── validator.py         # stale guard, anomaly
│   ├── ohlcv_store.py       # Parquet read/write
│   └── feature_engine.py   # indicators (stateless)
├── regime/
│   ├── detector.py          # rule-based 8 states
│   ├── models.py            # RegimeEvent dataclass
│   └── hmm_detector.py     # V5
├── strategy/
│   ├── base.py              # Abstract (ไม่รู้จัก Broker)
│   ├── ema_trend.py         # Primary V1
│   ├── dca_baseline.py      # Benchmark fixture
│   ├── grid_prototype.py    # Benchmark fixture
│   └── router.py            # V5: regime → strategy
├── risk/
│   ├── position_sizer.py   # ATR + fixed %
│   ├── circuit_breaker.py  # daily loss, drawdown
│   └── portfolio_guard.py  # correlation, exposure
├── execution/
│   ├── planner.py           # urgency → ConcreteOrder
│   ├── retry.py             # backoff + idempotency
│   ├── kill_switch.py       # EMERGENCY
│   └── dms_watchdog.py     # software DMS
├── broker/
│   ├── base.py              # BrokerInterface (abstract)
│   ├── backtest_broker.py  # V1
│   ├── paper_broker.py     # V2
│   └── live_broker.py      # V3+
├── ledger/
│   ├── position_manager.py
│   ├── trade_log.py         # append-only audit
│   ├── pnl_calculator.py
│   ├── balance_tracker.py
│   └── reconciler.py
├── monitoring/
│   ├── metrics.py           # Prometheus
│   ├── alerter.py           # Telegram + email
│   ├── logger.py            # structured JSON
│   └── drift_monitor.py    # 4-type drift
├── config/
│   ├── settings.py          # load .env
│   └── strategy_config.yaml # thresholds เป็น config
└── main.py                  # startup → state machine
```

### Core Events

```python
@dataclass
class MarketDataEvent:
    timestamp: datetime   # UTC
    symbol:    str
    open:      Decimal
    high:      Decimal
    low:       Decimal
    close:     Decimal
    volume:    Decimal
    timeframe: str
    is_closed: bool       # ห้าม signal ถ้า False

@dataclass
class OrderIntent:
    strategy_id: str
    symbol: str
    side: Literal['BUY', 'SELL']
    urgency: Urgency      # strategy กำหนดตรงนี้เท่านั้น
    reason: str           # 'ema_crossover', 'stop_loss', etc.
    quantity: Decimal | None
    limit_price: Decimal | None  # hint ไม่ใช่ hard instruction
    stop_price: Decimal | None
    deadline: datetime | None
    intent_id: UUID
    created_at: datetime
    regime: str           # regime ณ เวลาสร้าง intent

@dataclass
class FillEvent:
    order_id: UUID
    intent_id: UUID       # link กลับ OrderIntent
    symbol: str
    side: str
    quantity: Decimal     # actual filled
    price: Decimal        # actual fill price
    fee: Decimal
    fee_currency: str
    filled_at: datetime
    is_partial: bool
```

### Urgency Levels (7 levels, V1 ใช้ 5)

| Level          | V1?    | Default Order          | ตัวอย่าง       |
| -------------- | ------ | ---------------------- | -------------- |
| PASSIVE        | ✅     | Post-only limit        | Grid entry     |
| NORMAL         | ✅     | Limit + timeout 60s    | EMA entry, DCA |
| TIME_SENSITIVE | ⬜ V3+ | Limit IOC              | Breakout       |
| URGENT_EXIT    | ✅     | Market / IOC           | Stop trigger   |
| EMERGENCY      | ✅     | Cancel/Flatten         | Kill switch    |
| ATOMIC         | ⬜ V5+ | FOK limit              | Arbitrage      |
| PROTECTIVE     | ✅     | Software stop → market | Stop-loss      |

---

## 5. Regime Detection — Role ต่อ Version

### 8 States (ตัดสินแล้ว)

```
UPTREND_LOW_VOL     UPTREND_HIGH_VOL
DOWNTREND_LOW_VOL   DOWNTREND_HIGH_VOL
SIDEWAYS_LOW_VOL    SIDEWAYS_HIGH_VOL
BREAKOUT_WATCH      NO_TRADE
```

### Regime Progression

| Version | Role            | ทำอะไร                                                        |
| ------- | --------------- | ------------------------------------------------------------- |
| V1      | Tag / Report    | คำนวณและบันทึก regime ทุก trade → regime_performance.csv      |
| V2      | Filter          | NO_TRADE = ไม่เปิดใหม่, spread แย่ = skip, vol สูง = ลด size  |
| V3-V4   | Risk Scaler     | ปรับ position size / exposure ตาม regime state                |
| V5      | Strategy Router | เลือก strategy / allocation โดยอิงจาก regime_performance data |

### Regime Detector Code (เขียนได้เลย)

```python
def detect_regime(adx, ema_fast, ema_slow,
                  bb_width, bb_width_ma,
                  volume, avg_volume, spread,
                  config):  # thresholds มาจาก config ทั้งหมด

    # Hard filters
    if spread > config.max_spread_bps / 10000:  # max_spread_bps ใน config
        return "NO_TRADE"
    if volume < avg_volume * config.min_volume_ratio: return "NO_TRADE"

    is_high_vol  = bb_width > bb_width_ma * config.high_vol_multiplier
    is_squeeze   = bb_width < bb_width_ma * config.squeeze_multiplier
    is_uptrend   = adx > config.adx_trend_threshold and ema_fast > ema_slow
    is_downtrend = adx > config.adx_trend_threshold and ema_fast < ema_slow
    is_sideways  = adx < config.adx_sideways_threshold

    if is_squeeze:   return "BREAKOUT_WATCH"
    if is_uptrend:   return "UPTREND_HIGH_VOL"   if is_high_vol else "UPTREND_LOW_VOL"
    if is_downtrend: return "DOWNTREND_HIGH_VOL" if is_high_vol else "DOWNTREND_LOW_VOL"
    if is_sideways:  return "SIDEWAYS_HIGH_VOL"  if is_high_vol else "SIDEWAYS_LOW_VOL"
    return "NO_TRADE"  # transition zone
```

**สำคัญ:** Strategy-regime mapping (ว่า strategy ไหน work ใน regime ไหน) ต้องมาจาก `regime_performance.csv` ของ backtest ไม่ใช่ hardcode assumption

---

## 6. Strategy V1

### Structure

```
Primary (production-ready):
  EMA Trend (fast=20, slow=100 เป็น starting point จาก Spike)
  → validate จาก backtest ก่อน
  → parameter อาจเปลี่ยนหลัง sensitivity analysis

Benchmark fixtures (ไม่ใช่ production, ใช้เปรียบเทียบและ stress test):
  DCA baseline    → ง่ายที่สุด เป็น floor benchmark
  Simple Grid     → เทียบกับ EMA ใน sideways regime

ทั้ง DCA/Grid เป็น additional backtest runs ไม่ใช่ production strategy V1
ให้ข้อมูลสำหรับ regime_performance.csv ที่ครอบคลุมกว่า
```

### Strategy Validation Gate (ก่อนออก V2)

ดูรายละเอียดใน section V1

---

## 7. Exchange Decision

### สถานะ

```
Primary candidate:  Binance Spot
Connector design:   exchange-agnostic ผ่าน BrokerInterface
```

### Timeline ตัดสินใจ

```
ตอนนี้:  Binance Spot เป็น default candidate สำหรับ V1-V2 (backtest/paper)
ก่อน V3: เปรียบ Binance vs OKX vs Kraken บน:
  - API rate limits และ behavior
  - Dead Man's Switch support
  - Fee structure + maker/taker
  - Withdrawal security
  - Exchange restrictions บน automated trading
  - VPS location ใกล้ datacenter
  ค่อย lock exchange สำหรับ live trading
```

### Dead Man's Switch

```
V1-V2 (backtest/paper): ไม่จำเป็น
V3+ (live):
  Binance Spot → Software watchdog loop (ไม่มี exchange DMS)
  Binance Futures (V6) → Exchange DMS per-symbol + software backup
  Kraken → Exchange DMS global + software backup (ดีที่สุด)
```

---

## 8. ภาษาและ Framework

### ภาษา

```
Python: default V1-V5
  asyncio สำหรับ concurrent tasks (V2+)
  Decimal ทุกตัวเลขเงิน
  CCXT + pandas + numpy

Rust: พิจารณา V6+ เฉพาะถ้า:
  latency < 1ms เป็น hard requirement
  ใช้ผ่าน NautilusTrader API (PyO3) ไม่เขียนเอง
  ไม่ mix ภาษาก่อนมีเหตุผลจำเป็น
```

### Framework Strategy

```
Custom core:     primary — เขียนเองตาม architecture นี้
VectorBT:        research + parameter sweep + returns_matrix
Freqtrade:       benchmark ว่า result ตรงกับ custom engine ไหม
Jesse (free):    Monte Carlo dashboard (2 modes)
NautilusTrader: reference สำหรับ backtest-live parity best practices
```

### Framework Decision Tree (หลัง Spike)

```
1. Custom mini engine (Spike C) ทำงานได้ใน < 2 สัปดาห์?
   YES → custom core เป็น primary

2. Freqtrade รองรับ ledger/reconciliation/urgency ที่ต้องการได้?
   YES (และ custom ยาก) → Freqtrade เป็น MVP runner

3. NautilusTrader learning curve < 2 สัปดาห์?
   YES (และ backtest-live parity สำคัญมาก) → NautilusTrader

ถ้า custom wins: VectorBT/Freqtrade/Jesse ยังเป็น research tools
ถ้า Freqtrade wins: VectorBT/Jesse ยังเป็น research tools
```

---

## 9. ตัวเลือกที่ยังเปิดอยู่

| เรื่อง                  | สถานะ               | จะตัดสินเมื่อไหร่                 |
| ----------------------- | ------------------- | --------------------------------- |
| Primary framework       | รอ Spike A-D        | หลัง V0 spikes เสร็จ              |
| Exchange final          | รอ comparison       | ก่อน V3 live                      |
| Strategy parameters     | รอ backtest         | ภายใน V1                          |
| Strategy-regime mapping | รอ backtest         | ภายใน V1 (regime_performance.csv) |
| Second strategy (V5)    | รอ V4 data          | ก่อน V5                           |
| Rust adoption           | รอ performance data | V6+ ถ้าจำเป็น                     |
| Microservices           | รอ scale จริง       | V6+ ถ้าจำเป็น                     |
| AI analyst layer        | รอ core stable      | V6                                |

---

## สรุป — สิ่งที่ทำได้เลยโดยไม่ต้องรอ

```
✅ เขียน event dataclasses (MarketDataEvent, OrderIntent, FillEvent)
✅ เขียน BrokerInterface abstract class
✅ เขียน Regime Detector (rule-based, config-driven)
✅ เขียน Portfolio Ledger schema และ basic implementation
✅ เขียน Risk Manager baseline
✅ เริ่ม Spike A-D ตาม common test spec

⬜ รอผล Spike: framework decision, strategy selection
⬜ รอ backtest: strategy-regime mapping, parameter tuning
⬜ รอก่อน V3: exchange final decision
```

---

_Merged Design v1.0 — synthesis จาก KB v5 + Codex feedback + iteration_
_ปรับปรุงแล้ว: gate ordering, regime progression, V0 scope, version numbering, exchange timeline_
