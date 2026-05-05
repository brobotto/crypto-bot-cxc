# Crypto Trading Bot Research — Raw Q&A Log v2

> บันทึกคำถามและคำตอบจากการ research ทั้งหมด เรียงตามลำดับการสนทนา
> v2: เพิ่ม Q13-Q17 จาก session ที่ 2 (Portfolio Ledger, Startup Recovery, Backtest-Live Unified Design, Codex comparison)

---

## Q1: Trading Bot Crypto มีกี่ประเภท?

**คำถาม:** ในช่วงปีนี้หรือปีที่ผ่านมา trading bot crypto มีกี่ประเภทที่น่าสนใจ มีจุดประสงค์ในการทำงานกี่แบบ และข้อดีข้อเสียของแต่ละแบบคืออะไร

**คำตอบสรุป:** มี 7 ประเภทหลัก (Grid, DCA, Trend, Arbitrage, Market Making, AI/ML, Rebalancing) และจุดประสงค์หลัก 7 แบบ

จุดสำคัญ:
- ไม่มี bot เดียวที่ดีในทุกสภาวะตลาด
- AI/ML ควรเป็น analyst layer ไม่ใช่ execution authority
- Sniper/Launch bot เสี่ยง scam, rug, MEV, rule violations — ไม่ใช่ legitimate strategy
- Freqtrade (2025) พิสูจน์ว่า platform-based bot มี monthly volume กว่า $60B

---

## Q2: ต้องมีหลาย Strategy ไหม?

**คำถาม:** แต่ละ strategy เหมาะกับตลาดต่างกัน แสดงว่าต้องทำมากกว่า 1 strategy หรือเปล่า

**คำตอบสรุป:** ใช่ — ในระยะยาวควรมีมากกว่า 1 แต่ architecture ต้องรองรับตั้งแต่แรก

โครงสร้างที่แนะนำ:
```
Market Data → Regime Detector → Strategy Router → Risk Manager → Execution
```

ตัวอย่าง routing:
- Sideways: Grid, mean reversion
- Uptrend: Trend-following, breakout, DCA
- Downtrend: Cash, cautious DCA, hedge
- High volatility: ลด size, widen stops
- Low liquidity: avoid scalping → NO_TRADE

Version progression:
- V1: strategy เดียว แต่ architecture รองรับหลาย strategy
- V2: regime detector + strategy router
- V3: allocation และ risk budget ต่อ strategy

---

## Q3: Market Regime Detection มีวิธีไหนบ้าง?

**คำถาม:** บอทจะรู้ได้อย่างไรว่าตอนนี้ตลาดอยู่ในสถานะไหน

**คำตอบสรุป:** 8 กลุ่มวิธีหลัก

1. **Moving Average Filter:** ง่าย lagging, false signal ใน sideways
2. **ADX / Directional Movement:** แยก trend กับ range ได้ดี, lagging
3. **ATR / Realized Volatility:** ดีสำหรับ position sizing/risk, ไม่บอกทิศทาง
4. **Bollinger Band Width:** จับ compression/expansion, ไม่บอกทิศทาง breakout
5. **Market Structure Detection:** ใกล้ trader logic แต่ rule robust ยาก
6. **Volume / Liquidity Regime:** สำคัญมากสำหรับ live execution, ต้องการ data เพิ่ม
7. **K-Means Clustering:** เจอ hidden pattern แต่ตีความยาก
8. **Hidden Markov Model:** probabilistic regimes, ซับซ้อน

**Baseline V1:**
```
EMA 50/200 + ADX + ATR percentile + Bollinger Band Width + Volume + Spread
```

**Regime states (8 states):**
```
UPTREND_LOW_VOL, UPTREND_HIGH_VOL, DOWNTREND_LOW_VOL, DOWNTREND_HIGH_VOL,
SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL, BREAKOUT_WATCH, NO_TRADE
```

Key insight: NO_TRADE state สำคัญมาก — ห้าม trade ในช่วง low-liquidity, wide spread, stale data

---

## Q4: Architecture ของ Bot มีแบบไหนบ้าง?

**คำถาม:** Architecture ที่น่าสนใจมีอะไรบ้าง

**คำตอบสรุป:**

1. **Simple Loop Bot:** เร็ว แต่โตยาก, live/backtest คนละ logic
2. **Layered Modular Bot:** แยก data/strategy/risk/execution — เหมาะ V1
3. **Event-Driven Bot:** realistic backtest/live flow, ซับซ้อนกว่า loop
4. **Backtest-Live Unified Engine:** strategy code เดียวทุก mode — คุ้มค่ามาก
5. **Multi-Strategy Portfolio Bot:** allocation + regime switching — V4+
6. **Microservices:** scale ดี แต่ operational complexity สูง — ไม่แนะนำ V1
7. **Connector-Based:** เปลี่ยน exchange ง่าย แต่ abstraction อาจรั่ว
8. **Risk-First Execution:** ทุก order ผ่าน risk engine กลาง — production-grade
9. **AI/Agentic:** AI ช่วย analyze แต่ต้องมี rule-based guardrail

**แนะนำ:**
```
Modular Monolith + Event-inspired internals + Backtest-live unified + Central Risk Manager
+ Connector abstraction + Microservice-ready boundaries
```

---

## Q5: EDA vs Microservices vs Agent ต่างกันอย่างไร?

**คำถาม:** ความแตกต่างระหว่าง 3 concept

**คำตอบสรุป:**

| Concept | ถามว่า | ประเภท |
|---------|--------|--------|
| EDA | "component คุยกันยังไง" | Communication Pattern |
| Microservices | "code อยู่ที่ไหน deploy ยังไง" | Infrastructure |
| Agent | "unit ฉลาดแค่ไหน ตัดสินใจเองได้ไหม" | AI Layer |

Agent-like components (software) เช่น StrategyAgent, RiskAgent — ไม่ใช่ AI agent แต่เป็น module ที่มี role ชัดเจน

AI agent ต้องไม่ control live execution โดยไม่มี rule-based guardrail

---

## Q6: หมวดที่ยังต้อง Research

**คำถาม:** มีส่วนของ crypto bot ที่ยังไม่ได้ research ไหม

**คำตอบสรุป:** หมวดที่ต้อง research ต่อ (เรียงตามความสำคัญ):
1. Risk Management
2. Backtesting Methodology
3. Exchange/API + Execution
4. Data Pipeline
5. Monitoring/Security/Deployment
6. **Portfolio & Accounting (Ledger)** ← พบว่าขาดจาก Codex comparison
7. **Startup Recovery / Reconciliation** ← พบว่าขาดจาก Codex comparison
8. Legal / Compliance / Exchange Rules

---

## Q7: Risk Management

**คำถาม:** Research risk management

**คำตอบสรุป:** 6 ชั้น (trade → position → portfolio → drawdown → execution → leverage)

**Conservative Baseline V1:**
```
spot_only = true
risk_per_trade = 0.5%-1%
max_position_per_pair = 10%
max_total_exposure = 50%-60%
max_open_positions = 3-5
daily_loss_limit = 2%
max_drawdown_stop = 10%
spread_filter = enabled
stale_data_guard = enabled
cooldown_after_loss = enabled
```

Key insight: strategy ที่มี win rate 60% ยังพังได้ถ้า position sizing ผิด

---

## Q8: Backtesting

**คำถาม:** Research backtesting

**คำตอบสรุป:**

Workflow: Simple backtest → Walk-forward → Monte Carlo → Paper trade → Live

**Key rules:**
- causal indicators only (no repainting)
- next-candle execution เสมอ
- warmup period = max(all indicator lookback)
- is_closed = True ก่อน generate signal
- benchmark vs buy-and-hold BTC เสมอ
- regime_performance.csv สำคัญมาก

**Stress test formula:** fee×2 + slippage×2 + latency 200ms → ถ้ายังกำไร = robust

**Overfitting check:**
- Sharpe ลด > 40% ใน out-of-sample = overfit
- Max drawdown เพิ่ม > 2× ใน out-of-sample = overfit

---

## Q9: Data Layer & Exchange API

**คำถาม:** Research Data Layer & Exchange API

**คำตอบสรุป:**

**Storage แนะนำ (จาก Codex):**
```
Parquet: historical OHLCV — columnar, compressed ดีกว่า SQLite มาก
SQLite:  operational data (orders, fills, positions, state)
DuckDB:  analytics บน Parquet (later)
```

**CCXT pattern:** strategy ต้องไม่คุยกับ exchange โดยตรง ต้องมี internal exchange interface ห่อ CCXT อีกชั้น

**Exchange metadata ต้องตรวจก่อน submit:**
- price precision / tick size
- amount precision / step size
- min quantity / min notional
- order type supported

**Data quality rules:**
- timestamps UTC
- reject non-closed candles
- detect stale feed
- resync หลัง WS gap

---

## Q10: Order Execution Engine

**คำถาม:** Research Order Execution Engine

**คำตอบสรุป:**

Execution Engine แปลง OrderIntent ที่ผ่าน risk แล้วเป็น order จริงอย่างปลอดภัย

**Lifecycle:** CREATED → SUBMITTED → ACCEPTED → PARTIALLY_FILLED → FILLED / CANCELED / EXPIRED / FAILED / REJECTED

**Safety rules ที่สำคัญ:**
- clientOrderId ทุก order
- API timeout ≠ order ไม่ถูกสร้าง — query ก่อน retry เสมอ
- partial fill ต้อง update position + stop size
- cancel อาจเกิดพร้อม fill ได้
- reconciliation ต้องมีทุก startup, disconnect, และ periodic

**V1 order support:** market, limit, post-only, stop-loss, take-profit, cancel/replace

---

## Q11: Security

**คำถาม:** Research Security

**คำตอบสรุป:**

**หลักการสำคัญ:**
- default mode = paper
- live disabled by default
- withdrawal permission: never
- IP whitelist required for live key
- separate keys per environment (backtest/paper/testnet/live)
- central secret loader with redaction
- ห้าม log key/secret/signature ในทุกกรณี

**Runtime safety states:** ACTIVE / HALTED / REDUCE_ONLY

**Dependencies & Supply Chain (Codex เพิ่ม):**
- pin versions + lockfile
- scan vulnerabilities (Dependabot)
- treat skill/library install as high-risk event

---

## Q12: Monitoring & Alerting

**คำถาม:** Research Monitoring & Alerting

**คำตอบสรุป:**

**Monitoring 6 ชั้น:**
- Process health, Data health, Exchange health
- Execution health, Portfolio/risk health, Strategy health

**Telegram remote commands (Codex เพิ่ม):**
```
/status, /positions, /orders, /pnl
/pause_entries, /resume_entries, /halt, /cancel_all
```

**Alert levels:** info / warning / critical / emergency

**Important alerts:**
- bot stopped, market data stale, exchange auth failed
- stuck order, unresolved partial fill, ledger mismatch
- daily loss hit, max drawdown hit, kill switch triggered
- live mode started (critical alert เสมอ)

---

## Q13: Deployment & Infrastructure

**คำถาม:** Research Deployment & Infrastructure

**คำตอบสรุป:**

**Phase roadmap:**
```
Phase 1: Local dev + paper trading
Phase 2: VPS + Docker Compose
Phase 3: VPS production hardened
Phase 4: Cloud/Kubernetes เฉพาะเมื่อ scale จริง
```

**Startup Recovery (สำคัญมาก — Codex highlight):**
```
1. Load local state
2. Fetch exchange open orders + balances
3. Reconcile fills
4. Resolve unknown orders
5. Start PAUSED / REDUCE_ONLY ถ้า mismatch
6. Resume เฉพาะเมื่อ state clean
```

**Production V1 baseline:**
```
VPS Ubuntu LTS + Docker Compose + SQLite + Parquet
+ Telegram alerts + daily backup + startup reconciliation
restart policy: unless-stopped
```

---

## Q14: Codex Research Comparison

**คำถาม:** เปรียบเทียบ knowledge base จาก Codex กับ session นี้ — มีส่วนไหนที่เราขาด และส่วนไหนที่เห็นต่าง

**คำตอบสรุป:**

**สิ่งที่ Codex มีและเราขาด (สำคัญ):**

1. **Portfolio Ledger** — component หลักที่ขาดไป บันทึก fills, position, P&L, reconcile
2. **Startup Recovery** — sequence ชัดเจน: load state → fetch exchange → reconcile → PAUSED
3. **Backtest-Live Unified Design** — strategy code เดิมทุก mode, เปลี่ยนแค่ Broker Interface
4. **Regime States 8 states** (เรามี 3) — เพิ่ม NO_TRADE, BREAKOUT_WATCH, HIGH/LOW VOL split
5. **Volume + Liquidity เป็น regime input** (ไม่ใช่แค่ risk filter)
6. **Exchange Metadata Validation** ก่อน submit (tick size, step size, min notional)
7. **Telegram Remote Commands** — /halt /status /positions (ไม่ใช่แค่ alert ทางเดียว)
8. **Bot Runtime States** — ACTIVE / HALTED / REDUCE_ONLY
9. **Benchmark vs buy-and-hold BTC** ใน backtest
10. **regime_performance.csv** output

**จุดที่เห็นต่างกัน (ต้องคิดดีๆ):**

1. **Risk baseline:** Codex conservative กว่า (0.5-1% risk, 2% daily, 10% max drawdown vs เรา 1-2%, 3-5%, 15%) → รับเอา conservative baseline ของ Codex สำหรับ V1
2. **Storage:** Codex เสนอ Parquet + SQLite ชัดเจน (เรา SQLite อย่างเดียว) → รับเอา Parquet สำหรับ historical
3. **Version roadmap:** Codex แยก Paper Trading เป็น Version แยกชัด → adopt pattern นี้
4. **AI layer:** Codex ระมัดระวังกว่า — AI ต้องมี rule-based guardrail เสมอ → เห็นด้วย

**สิ่งที่ทั้งสองเห็นตรงกัน (ยืนยัน):**
Modular monolith, strategy ไม่ bypass risk, spot-only ก่อน, CCXT + native WS,
paper trading ก่อน live, clientOrderId ทุก order, walk-forward, VPS + Docker,
no withdrawal permission, Telegram alert, structured JSON logs

---

## Q15: Portfolio Ledger & Accounting

**คำถาม:** Research Portfolio Ledger

**คำตอบสรุป:**

**5 components หลัก:**
- Position Manager, Trade Ledger, Balance Tracker, P&L Calculator, Reconciliation Engine

**P&L Formulas:**
```python
# Unrealized (ไม่รวม fee)
unrealized = (current_price - avg_entry) * quantity

# Realized (รวม fee ทั้งหมด)
realized = (exit_price - avg_entry) * quantity - entry_fee - exit_fee

# Average Entry (Partial fills)
new_avg = (old_avg * old_qty + fill_price * fill_qty) / (old_qty + fill_qty)
```

**กฎสำคัญ:** ใช้ Decimal ไม่ใช่ float ทุกกรณี

**Reconciliation:** เมื่อ internal ≠ exchange → เชื่อ exchange เสมอ

**Edge cases:**
- Partial fill + scale-in → recalc avg_entry
- Fill ระหว่าง downtime → fetch since last_seen
- Cancel race condition → ตรวจ fill event ก่อน update state
- Dust position → threshold + policy

**Performance tracking per regime:**
```csv
regime,trades,win_rate,avg_pnl,profit_factor
SIDEWAYS_LOW_VOL,45,0.62,12.3,1.8
```

ข้อมูลนี้ชี้ให้เห็นว่า strategy ทำงานได้ดีใน regime ไหน ควร disable ใน regime ไหน

---

## Q16: Startup Recovery & Reconciliation

**คำถาม:** Research Startup Recovery / Reconciliation

**คำตอบสรุป:**

**Bot State Machine (6 states):**
```
INITIALIZING → RECONCILING → PAUSED → ACTIVE ↔ REDUCE_ONLY
                           ↘ HALTED
```

**Startup Sequence (8 ขั้นตอน — ห้ามข้าม):**
1. Pre-flight checks
2. Load local state
3. Fetch exchange ground truth (orders + balance + fills)
4. Reconcile orders (orphans + ghosts)
5. Process missing fills (เกิดระหว่าง downtime)
6. Reconcile positions
7. Reconcile balance → drift > threshold → HALTED
8. Start PAUSED → auto-resume หรือรอ human

**State Persistence — Must persist:**
```
open_positions, pending_orders, last_fill_timestamp (สำคัญที่สุด),
circuit_breaker_state, bot_state, peak_equity
```

**Graceful Shutdown Policies:**
```
CANCEL_ALL:   ยกเลิกทุก order (conservative)
KEEP_STOPS:   ยกเลิก entry, คง stop/TP ← แนะนำ
KEEP_ALL:     ทิ้งไว้ (อันตราย)
```

**Recovery Scenarios:**
- Clean restart → auto-resume
- Crash restart → PAUSED 30s + alert + process missing fills
- WS disconnect → reconnect → fetch fills since disconnect
- Balance drift > 1% → HALTED รอ human
- Orphan order → cancel ถ้าไม่รู้ที่มา + alert

**Key insight:** last_fill_timestamp คือ field ที่สำคัญที่สุดที่ต้อง persist

---

## Q17: Backtest-Live Unified Design

**คำถาม:** Research Backtest-Live Unified Design

**คำตอบสรุป:**

**หลักการ:** เปลี่ยนแค่ Broker Interface → ทุกอย่างอื่นเหมือนกัน

**Core Events:**
```python
MarketDataEvent: timestamp, symbol, OHLCV, is_closed (สำคัญมาก)
OrderIntent:     strategy_id, symbol, side, order_type, quantity
FillEvent:       order_id, intent_id, actual_price, actual_qty, fee, is_partial
```

**3 Broker Implementations:**
- BacktestBroker: historical data, fast, next-candle execution
- PaperBroker: live price, simulated fill, latency simulation
- LiveBroker: real exchange, real money

**Fill Models (จาก naive → realistic):**
```
❌ Instant fill at signal price — ห้ามใช้
⚠️ Next candle open — basic
✅ Conservative limit fill — recommended
✅ Realistic + slippage + volume — best
🔬 Tick-level / order book — HFT only
```

**2 Deployment Gaps (FinRL-X 2025):**
```
Gap 1 Backtest→Paper:  instant fills, no market impact, data inconsistency
  Fix: realistic fill + slippage + warmup + next-candle + benchmark

Gap 2 Paper→Live:  latency, partial fills, infrastructure fragility, flash crash
  Fix: reconciliation + retry + kill switch + small position + slippage calibration
```

**Lookahead Prevention:** Event-driven ทำให้ lookahead เป็นไปไม่ได้โดยโครงสร้าง
- ใช้ is_closed = True เท่านั้น
- shift(1) ทุก indicator
- execute บน candle ถัดไปเสมอ
- warmup = max(all lookback periods)

**Calibration target:**
```
Live Sharpe ≥ 60% ของ Backtest Sharpe → implementation ดี
```

**Frameworks:**
- Freqtrade: dry_run=true/false เปลี่ยน mode — production-proven
- Jesse: unified codebase ที่ clean ที่สุด
- NautilusTrader: Rust-based, high performance
- Hummingbot: V2 framework, multi-venue

---

## Summary: Topics ที่ยังไม่ได้ Research ในเชิงลึก

```
✅ ประเภท Bot
✅ Market Regime Detection
✅ Architecture
✅ Risk Management
✅ Backtesting
✅ Data Layer & Exchange API
✅ Order Execution Engine
✅ Security
✅ Monitoring & Alerting
✅ Deployment & Infrastructure
✅ Portfolio Ledger & Accounting  (เพิ่มใหม่)
✅ Startup Recovery & Reconciliation  (เพิ่มใหม่)
✅ Backtest-Live Unified Design  (เพิ่มใหม่)

⬜ Paper Broker Design (implementation details)
⬜ Backtest Engine Implementation (warmup, event loop detail)
⬜ Legal / Compliance / Exchange Rules
⬜ Funding Rate Arbitrage (futures, V5+)
⬜ Signal/Webhook Bot Pattern (external signal integration)
```

---

*Raw Q&A Log v2 — อัปเดตจาก session ที่ 2 รวม Codex comparison และ 3 topics ใหม่*
