ได้ครับ นี่คือ **design ล่าสุดหลังปรับตาม feedback รอบล่าสุด** แบบเป็น source-of-truth เวอร์ชันย่อแต่ครบ

## Direction

เราจะสร้าง bot แบบ:

```text
Backtest-first
Spot-only first
Risk-first
Ledger-centric
Modular Monolith
Event-inspired internals
Unified Broker Interface
```

เป้าหมายไม่ใช่ “รีบ live” แต่คือสร้าง engine ที่:

- backtest/paper/live ใช้ logic เดียวกัน
- strategy ส่งแค่ `OrderIntent`
- ทุก order ผ่าน `RiskManager`
- position เปลี่ยนจาก `FillEvent` เท่านั้น
- restart ทุกครั้งต้อง reconcile ก่อน
- live ต้องผ่าน calibration gates ก่อน scale capital

## Core Architecture

```text
Data Adapter
  -> Feature / Indicator Engine
  -> Regime Detector
  -> Strategy Engine
  -> Risk Manager
  -> Execution Planner
  -> BrokerInterface
       BacktestBroker | PaperBroker | LiveBroker
  -> Portfolio Ledger
  -> Monitoring / Drift / Calibration Gates
```

V1-V4 ยังเป็น **single Python process / modular monolith**  
ยังไม่ใช้ microservices, Redis/Kafka, หรือ AI agent architecture

## Key Decisions

| เรื่อง            | Decision ล่าสุด                                              |
| ----------------- | ------------------------------------------------------------ |
| Market            | Spot-only, long-only ก่อน                                    |
| Pairs V1          | BTC/USDT, ETH/USDT เป็นหลัก                                  |
| Exchange          | Binance Spot = default candidate, ยังไม่ใช่ final            |
| Framework         | ทำ spike ก่อนเลือก primary path                              |
| Language          | Python V1-V4                                                 |
| Rust              | พิจารณา V6+ ถ้ามี latency/data-volume need จริง              |
| Storage           | Parquet สำหรับ OHLCV, SQLite สำหรับ operational ledger       |
| Monitoring V1     | structured logs + Telegram                                   |
| DMS V1            | software watchdog เพราะ Binance Spot ไม่มี exchange-side DMS |
| Capital reserve   | V1 default 40%, ไม่ใช่ “เสมอ”                                |
| Regime thresholds | อยู่ใน config ไม่ hardcode                                   |

## Version Roadmap

### V0: Design + Framework Spikes

เป้าหมาย: เลือกทาง implementation ด้วย evidence

ทำ:

- Spike A: Freqtrade
- Spike B: VectorBT
- Spike C: Custom mini engine
- Spike D: NautilusTrader
- Optional: Jesse free-tier Monte Carlo spike
- draft `BrokerInterface`
- draft event contracts
- common dataset/spec

Gate เข้า V1:

```text
spikes completed
decision notes written
architecture path selected
data spec ready
event contracts draft ready
BrokerInterface draft ready
```

### V1: Backtest Core

เป้าหมาย: validate infrastructure ก่อน ไม่ใช่หลาย strategy พร้อมกัน

ทำ:

- OHLCV downloader
- feature engine
- rule-based regime detector
- **1 primary baseline strategy** เช่น EMA Trend
- BacktestBroker
- RiskManager
- PortfolioLedger
- reports
- strategy validation reports

ยังไม่แตะ live exchange

Flow:

```text
HistoricalData
-> MarketDataEvent
-> Strategy
-> OrderIntent
-> RiskManager
-> ExecutionPlanner
-> BrokerInterface
-> BacktestBroker
-> FillEvent
-> Ledger
```

Strategy validation gate ภายใน V1:

```text
no lookahead
next-candle execution
OOS validation
Monte Carlo
parameter sensitivity
DSR/PBO ถ้าลองหลาย variants
regime_performance.csv
```

### V2: Paper Trading

เป้าหมาย: rehearsal กับ live data แต่ไม่ใช้เงินจริง

ทำ:

- LiveDataAdapter
- PaperBroker
- virtual balances
- simulated fills/slippage/latency
- Telegram commands
- startup recovery
- periodic reconciliation
- software watchdog
- drift monitor เบื้องต้น

Gate V2 -> V3:

```text
paper 30-60 วัน หรือ 50+ trades
unexpected_position = 0
critical_ledger_mismatch = 0
fill_rate acceptable
order_reject_rate low
paper slippage within modeled range
drawdown <= Monte Carlo p95
```

### V3: Micro Live Spot

เป้าหมาย: ทดสอบเงินจริงขนาดเล็กมาก

ทำ:

- LiveBroker
- exchange connector
- private WebSocket
- real fills
- micro capital 2-5%
- kill switch
- security gate
- startup reconciliation strict

Gate สำหรับ scale:

```text
no unresolved reconciliation errors
unexpected_position = 0
critical_ledger_mismatch = 0
order reject rate < threshold
slippage <= 2x paper/model
drift tier <= Watch/Warning
```

### V4: Controlled Live + Capital Scaling

เป้าหมาย: scale อย่างมี gate

ทำ:

- CalibrationGate engine
- capital scaling policy
- drift threshold calibration
- deployment rollback
- monitoring เพิ่มขึ้น
- optional Prometheus/Grafana ถ้าจำเป็น

Scaling:

```text
2-5% -> 5-10% -> 25% -> 50% -> approved full bot allocation
```

ถ้า drift เป็น Critical:

```text
roll back capital stage
pause entries / reduce-only
```

### V5: Multi-Strategy + Regime Router

เป้าหมาย: ใช้ market regime เพื่อเลือก strategy/risk budget

ทำ:

- StrategyRouter
- multiple strategy instances
- risk budget per strategy
- regime-aware allocation
- weekly `regime_performance.csv`
- DCA/Grid/Breakout อาจเข้ามาในช่วงนี้หรือ late V4 หลัง harness stable

Regime progression:

```text
V1: tag/report
V2: filter
V3-V4: risk scaler
V5: strategy router
```

### V6: Advanced

ทำเฉพาะเมื่อระบบ spot mature แล้ว:

- futures
- funding/open interest
- HMM regime
- advanced execution/TWAP
- AI analyst layer
- possible Rust/Nautilus/microservices

## Strategy V1

ปรับล่าสุด:

```text
V1 primary strategy = 1 simple strategy ก่อน
likely EMA Trend
```

DCA/Grid ยังไม่ใช่ production strategy ใน V1

ใช้เป็น:

```text
DCA = later benchmark
Grid = later execution/risk stress test
```

เหตุผล:

- V1 ต้อง validate engine, ledger, risk, reports
- หลาย strategy พร้อมกันทำให้ debug ยาก
- เพิ่ม strategy ทีหลังง่ายกว่าซ่อม infrastructure ที่สับสน

## Framework Position

ยังไม่ lock framework ก่อน spike

```text
Freqtrade = practical MVP candidate
VectorBT = research / parameter sweep
Jesse = Monte Carlo / research UX
NautilusTrader = production-grade reference
Custom = primary core candidate
```

แนวโน้มตอนนี้:

```text
Custom modular core
+ VectorBT/Freqtrade/Jesse เป็น benchmark/research tools
```

แต่ final decision ต้องมาจาก V0 spikes

## Final Design Summary

```text
V0: prove implementation path
V1: build backtest core with one strategy
V2: paper trading with live data
V3: micro live spot
V4: controlled live + scaling
V5: multi-strategy regime-aware
V6: advanced/futures/AI/Rust if needed
```

นี่คือ design ที่ผมคิดว่าตอนนี้ balanced ที่สุด: conservative พอสำหรับเงินจริง แต่ยังไม่ช้าเกินจนกลายเป็น research forever.
