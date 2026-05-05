# Crypto Trading Bot Research — Raw Q&A Log v3

> บันทึกคำถามและคำตอบจากการ research ทั้งหมด เรียงตามลำดับการสนทนา
> v3: เพิ่ม Q18-Q21 จาก session ที่ 3 (Codex v2 comparison, Validation Methodology, Drift Detection, Framework Spikes)

---

## Q1: Trading Bot Crypto มีกี่ประเภท?

**คำตอบสรุป:** 7 ประเภทหลัก จุดประสงค์ 7 แบบ

| Bot | เหมาะกับ | ข้อควรระวัง |
|-----|---------|------------|
| Grid | Sideways | หลุด range ขาดทุน |
| DCA | Long-term | ไม่ maximize bull |
| Trend | Bull/Bear | แย่ใน sideways |
| Arbitrage | ทุกสภาวะ | ต้องการทุนสูงมาก |
| Market Making | ทุกสภาวะ | inventory risk |
| AI/ML | ทุกสภาวะ | ต้องมี guardrail เสมอ |
| Rebalancing | Long-term | เสีย fee ทุก rebalance |

**Key insight:** AI/ML ควรเป็น analyst layer ไม่ใช่ execution authority โดยตรง

---

## Q2: ต้องมีหลาย Strategy ไหม?

**คำตอบสรุป:** ในระยะยาวควรมี แต่ architecture ต้องรองรับตั้งแต่แรก

```
แนวทาง 1 (Beginner):    1 bot — ยอมรับ underperform บาง phase
แนวทาง 2 (Recommended): Grid 50% + Trend 30% + DCA 20%
แนวทาง 3 (Advanced):    Regime detector → auto-switch strategy
```

Version progression: V1=1 strategy, V2=regime-aware routing, V4=multi-strategy allocation

---

## Q3: Market Regime Detection มีวิธีไหนบ้าง?

**คำตอบสรุป:** 8 states, 6 detection methods

**8 Regime States:**
```
UPTREND_LOW_VOL, UPTREND_HIGH_VOL
DOWNTREND_LOW_VOL, DOWNTREND_HIGH_VOL
SIDEWAYS_LOW_VOL, SIDEWAYS_HIGH_VOL
BREAKOUT_WATCH, NO_TRADE
```

**Methods ตาม tier:**
- Tier 1: ADX + BBW + EMA + Volume/Spread filter (เริ่มต้น)
- Tier 2: HMM 3-state model (Phase 2)
- Tier 3: HMM + LSTM Hybrid (Advanced)

**Key insight:** NO_TRADE state สำคัญมาก — ห้าม trade ช่วง low-liquidity/wide spread/stale data

---

## Q4: Architecture ของ Bot มีแบบไหนบ้าง?

**คำตอบสรุป:** 5 patterns หลัก, แนะนำ Modular Monolith + Pipeline

**Pipeline flow:**
```
MarketDataEvent → Feature Engine → Regime Detector → Strategy →
OrderIntent → Risk Manager → Execution → Broker Interface →
FillEvent → Portfolio Ledger → Monitoring
```

**Module structure:**
```
data/ regime/ strategy/ risk/ execution/ broker/ ledger/ monitoring/ config/
```

**Key principles:**
1. Strategy ไม่รู้ว่าอยู่ใน backtest/paper/live
2. ทุก order ผ่าน Risk Manager เสมอ
3. Broker Interface คือจุดเดียวที่ swap ได้

---

## Q5: EDA vs Microservices vs Agent ต่างกันอย่างไร?

**คำตอบสรุป:** ตอบคนละคำถาม

| Concept | ถามว่า | ประเภท |
|---------|--------|--------|
| EDA | "component คุยกันยังไง" | Communication Pattern |
| Microservices | "code อยู่ที่ไหน" | Infrastructure |
| Agent | "unit ฉลาดแค่ไหน" | AI Layer |

ใน production มักใช้ทั้ง 3 ร่วมกัน — Microservices สื่อสารผ่าน Event Bus, Strategy agent ตัดสินใจภายใน

---

## Q6: หมวดที่ยังต้อง Research

**คำตอบสรุป:** (จาก session 1) หมวดที่ต้อง research ต่อ:
- Risk Management, Backtesting, Data Layer, Order Execution
- Security, Monitoring, Deployment
- **Portfolio Ledger** (พบว่าขาดจาก Codex v1)
- **Startup Recovery** (พบว่าขาดจาก Codex v1)

---

## Q7: Risk Management

**คำตอบสรุป:** 5 layers

```python
# Conservative baseline V1
RISK_PER_TRADE         = 0.005    # 0.5-1%
ATR_MULTIPLIER         = 2.0
DAILY_LOSS_LIMIT       = 0.02     # 2%
MAX_DRAWDOWN_FROM_PEAK = 0.10     # 10%
ACTIVE_CAPITAL_RATIO   = 0.60     # deploy 60%, reserve 40%
MAX_OPEN_POSITIONS     = 3
SPOT_ONLY              = True
```

**Recovery math:** 25% loss → ต้องการ 33.3% gain, 50% loss → ต้องการ 100% gain

---

## Q8: Backtesting

**คำตอบสรุป:**

**Workflow:** Simple backtest → Walk-forward → Monte Carlo → Paper trade → Live

**Key rules:**
```
✅ causal indicators, warmup period ครบ, next-candle execution
✅ is_closed = True ก่อน signal, benchmark vs BTC
✅ regime_performance.csv, out-of-sample ≥ 20%
```

**Stress test:** fee×2 + slippage×2 + latency 200ms → ยังกำไร = robust

**Overfitting:** Sharpe ลด >40% ใน OOS = overfit | DD เพิ่ม >2× = overfit

---

## Q9: Data Layer & Exchange API

**คำตอบสรุป:**

**Storage:**
```
Parquet:  historical OHLCV (columnar, compressed)
SQLite:   operational (orders, fills, positions, state)
DuckDB:   analytics บน Parquet (later)
```

**Pattern:** CCXT REST + Native WebSocket Adapter, strategy ต้องไม่คุยกับ exchange โดยตรง

**Exchange metadata validation ก่อน submit:**
- price precision / tick size, amount / step size, min_amount, min_notional

**Data quality:** UTC timestamps, reject non-closed candles, detect stale feed (>30s = NO_TRADE)

---

## Q10: Order Execution Engine

**คำตอบสรุป:**

**Lifecycle:** CREATED → SUBMITTED → ACCEPTED → PARTIAL → FILLED / CANCELED / REJECTED / FAILED

**Order type selection:**
```python
STOP_LOSS / EMERGENCY → MARKET (certainty > price)
ARBITRAGE             → FOK (atomic)
LIQUID + not urgent   → LIMIT (maker fee)
default               → LIMIT
```

**Critical:** clientOrderId ทุก order, query ก่อน retry หลัง timeout, partial fill ต้อง update position

**Safeguards:** max_slippage, max_notional, price sanity check, trade frequency limiter, kill switch

---

## Q11: Security

**คำตอบสรุป:**

**กฎเหล็ก:** ห้าม withdrawal permission บน bot key เด็ดขาด

**Key controls:**
```
.env ไม่ commit, IP whitelist, subaccount แยก
withdrawal whitelist บน exchange, 2FA (authenticator app)
pin dependency versions + lockfile, Dependabot scan
ห้าม log key/secret/signature ใทุกกรณี
```

**Live Gate (Hard gate):** subaccount + IP whitelist + secret scanning + rollback procedure ต้องครบก่อนเปิด live

---

## Q12: Monitoring & Alerting

**คำตอบสรุป:**

**3 Pillars:** Metrics (Prometheus) + Logs (Loki) + Traces (latency chain)

**Alert Tiers:**
```
🔴 Critical: ภายใน 5 นาที — drawdown >10%, WS down, API fail, kill switch
🟡 Warning:  ภายใน 30 นาที — fill rate <80%, slippage >2×, stuck order
🔵 Info:     Daily review — trade executed, daily P&L
⚪ Silent:   Log only — heartbeat, polling
```

**Telegram commands:** /status /positions /orders /pnl /pause_entries /resume_entries /halt /cancel_all

**Starter stack:** Structured logs + Telegram → Prometheus + Grafana ใน V2-3

---

## Q13: Deployment & Infrastructure

**คำตอบสรุป:**

**VPS:** Hetzner/Vultr $5-10/mo, ใกล้ exchange datacenter, Ubuntu 24.04 LTS

**Exchange → Region:**
```
Binance EU → Frankfurt (Hetzner)
Bybit/OKX  → Singapore (Vultr)
Coinbase   → US East
```

**Process manager:** systemd (Python) หรือ Docker --restart=unless-stopped

**Stack progression:**
```
Starter:      VPS + systemd + .env + Telegram alert
Intermediate: + Docker Compose + Prometheus + Grafana
Advanced:     + Multiple VPS + Blue-green deploy
```

---

## Q14: Codex v1 Research Comparison

**คำตอบสรุป:** สิ่งที่เพิ่มจาก Codex v1

สิ่งที่ขาดและสำคัญ:
- Portfolio Ledger, Startup Recovery, Backtest-Live Unified Design
- Regime States 8 states, Volume/Liquidity เป็น regime input
- Exchange Metadata Validation, Telegram Remote Commands
- Bot Runtime States (ACTIVE/HALTED/REDUCE_ONLY)

จุดที่รับจาก Codex:
- Risk baseline conservative (0.5-1%, daily 2%, max 10%)
- Parquet + SQLite, Version roadmap V0-V5

---

## Q15: Portfolio Ledger & Accounting

**คำตอบสรุป:**

**5 Components:** Position Manager, Trade Ledger, Balance Tracker, P&L Calculator, Reconciliation Engine

**P&L Formulas:**
```python
unrealized = (current_price - avg_entry) * qty           # ไม่รวม fee
realized   = (exit_price - avg_entry) * qty - fees       # รวม fee
new_avg    = (old_avg*old_qty + fill_price*fill_qty) / (old_qty+fill_qty)
drawdown   = (peak_equity - current_equity) / peak_equity
```

**กฎ:** ใช้ Decimal เสมอ, เชื่อ exchange เมื่อ internal ≠ exchange แต่ต้อง alert ก่อน

**Edge cases:**
- Partial fill + scale-in → recalc avg_entry
- Fill ระหว่าง downtime → fetch since last_fill_timestamp
- Cancel race → ตรวจ fill event ก่อน update state
- Dust position → threshold + policy

**Performance tracking per regime:**
```csv
regime,trades,win_rate,avg_pnl,profit_factor
SIDEWAYS_LOW_VOL,45,0.62,12.3,1.8
```

---

## Q16: Startup Recovery & Reconciliation

**คำตอบสรุป:**

**Bot State Machine (6 states):**
```
INITIALIZING → RECONCILING → PAUSED → ACTIVE ↔ REDUCE_ONLY
                           ↘ HALTED
```

**Startup Sequence (8 ขั้นตอน — ห้ามข้าม):**
```python
# 0. Pre-flight checks
# 1. Load local state
# 2. Fetch exchange: open_orders + balance + fills
# 3. Reconcile orders (orphans + ghosts)
# 4. Process missing fills (เกิดระหว่าง downtime)
# 5. Reconcile positions
# 6. Reconcile balance → drift > threshold → HALTED
# 7. Resolve unknowns → determine startup mode
# 8. Start PAUSED → auto-resume หรือ wait_human
```

**Must persist:**
```
open_positions, pending_orders, last_fill_timestamp (สำคัญที่สุด),
circuit_breaker_state, bot_state, peak_equity
```

**Shutdown policy (แนะนำ KEEP_STOPS):**
```
CANCEL_ALL:  ยกเลิกทุก order (conservative)
KEEP_STOPS:  ยกเลิก entry, คง stop/TP ← แนะนำ
KEEP_ALL:    ทิ้งทุก order (อันตราย)
```

**Periodic reconciliation:**
```
ทุก 15-30s: WS heartbeat, stuck orders, unrealized P&L update
ทุก 60-120s: fetch open orders, balance drift check
ทุก 5-10min: full balance reconcile, orphan position check
EOD:         reset daily_loss, archive logs
```

---

## Q17: Backtest-Live Unified Design

**คำตอบสรุป:**

**หลักการ:** เปลี่ยนแค่ Broker Interface — ทุกอย่างอื่นเหมือนกัน

**Core Events:**
```python
MarketDataEvent: timestamp, OHLCV, is_closed (ห้าม signal บน False)
OrderIntent:     strategy_id, symbol, side, order_type, quantity
FillEvent:       intent_id (link กลับ), actual_price, actual_qty, fee, is_partial
```

**Broker Interface (swap ตาม mode):**
```python
broker = BacktestBroker(data=historical)  # fast, next-candle
broker = PaperBroker(exchange=live)       # live price, simulated fill
broker = LiveBroker(exchange=live)        # real money
```

**Fill Models (conservative → realistic):**
```
❌ Instant fill at signal price
⚠️ Next candle open (basic)
✅ Conservative limit fill (recommended)
✅ Realistic + slippage + volume (best)
```

**2 Deployment Gaps (FinRL-X 2025):**
```
Gap 1 Backtest→Paper: instant fills, no market impact
  Fix: realistic fill + slippage + warmup + next-candle + benchmark

Gap 2 Paper→Live: latency, partial fills, infrastructure fragility
  Fix: reconciliation + retry + kill switch + small position first
```

**Calibration target:** Live Sharpe ≥ 60% ของ Backtest Sharpe → implementation ดี

---

## Q18: Codex v2 มีอะไรที่เราขาดหรือเห็นต่างบ้าง?

**คำตอบสรุป:**

**สิ่งที่ Codex v2 มีและเราขาด — น่าเอาเข้าจริงๆ:**

1. **Validation Methodology ครบกว่า** — DSR, PBO/CSCV, Survivorship Bias controls ที่เราไม่ได้ cover
2. **Drift Detection 4 types + Action Tiers** — เรามีแค่ flat signals ไม่มี response ชัดเจน
3. **Operational Security เป็น Live Gate** — "ไม่มี subaccount / whitelist / secret scanning / rollback = ยังไม่เปิด live"
4. **Framework Decision + Spikes A-D** — ทดสอบก่อนตัดสินใจ platform
5. **Backtest-First Harness** — ไม่เลือก strategy ก่อนมี backtest framework

**จุดที่ Codex v2 เห็นต่าง — Codex พูดถูก:**
1. Retry → Market fallback เฉพาะ emergency ไม่ใช่ default
2. Limit order default อาจพลาด fill — ต้องเลือกตาม urgency
3. Prometheus/Grafana ตั้งแต่ starter อาจ overkill — structured logs ก่อน

**สิ่งที่ยืนยันตรงกัน (ทั้งสอง session agree):**
Modular monolith, strategy ไม่ bypass risk, spot-only ก่อน, CCXT + native WS,
paper trading ก่อน live, clientOrderId, walk-forward, VPS + Docker,
no withdrawal permission, Telegram alert, JSON logs, Parquet + SQLite

---

## Q19: Validation Methodology ที่ครบชุด

**คำตอบสรุป:**

### Full Validation Pipeline (8 ขั้นตอน)

```
1. Unit/Logic Validation     — ตรวจ code ก่อนแตะ data จริง
2. Bias Checks               — lookahead, leakage, warmup, UTC
3. Backtest In-sample        — idea validation เท่านั้น
4. Robustness Checks         — Monte Carlo, sensitivity, walk-forward
5. Multiple Testing Controls — DSR, PBO/CSCV ถ้าลอง >5 variants
6. Generalization Checks     — survivorship bias, หลาย period, หลาย assets
7. Paper Trading             — validate execution + latency + reconciliation
8. Live Gating               — security gate + small capital + drift baseline
```

### Data Snooping Controls

**ปัญหา:** งานวิจัย 2025 — Sharpe ratio ลด 63% จาก in-sample ไป OOS, >78% ของ published strategies ล้มเหลว

**Deflated Sharpe Ratio (DSR):**
- แก้ Sharpe สำหรับ: จำนวน trials, non-normality, sample length
- DSR > 0 = รอดจาก selection bias | DSR ≤ 0 = likely snooping artifact
- ใช้เมื่อลอง > 5 variants

**PBO via CSCV:**
- PBO < 20% = robust | 20-50% = fragile | > 50% = overfit
- CSCV ลด false positive จาก 68% เหลือ 22% แต่ heavy — ทำแค่ top 3

**Controls:**
```
[ ] Pre-register hypothesis ก่อนดู data
[ ] Research log ทุก variant (ไม่ใช่แค่ตัวที่ดี)
[ ] Parameter budget ก่อน optimize
[ ] Locked holdout set (ใช้แค่ครั้งเดียว)
[ ] DSR ถ้าลอง > 5 variants
[ ] CSCV/PBO สำหรับ top 3 candidates
```

### Survivorship Bias — อันตรายพิเศษใน Crypto

**ตัวอย่างจริง:** 'buy top-20 altcoins 2020-2021'
- Today's top-20: +2,800%
- Historical top-20: +680%
- ต่างกัน 4× เพราะไม่รวม LUNA, FTT, dead altcoins

**Policy:**
```
V1:          BTC/ETH เท่านั้น — ไม่มี survivorship bias เลย
ถ้า altcoins: point-in-time universe (ไม่ใช่ current symbols)
              historical liquidity filter (ไม่ใช่ volume วันนี้)
```

### Monte Carlo — Metrics สำคัญ

```
5th pct final equity   — ต้อง > 0
risk of ruin           — P(equity < 10% initial) ต้อง < 5%
95th pct max drawdown  — เปรียบกับ circuit breaker
worst losing streak    — เปรียบกับ consecutive loss limit ที่ตั้งไว้
breakeven fee          — fee × N ที่ strategy ยังกำไร (ต้อง > 2×)
```

### Validation Checklist (Hard Gate ก่อน Live)

```
Pre-registration: hypothesis + parameter budget + locked holdout
Bias: no lookahead (unit test) + warmup + next-candle + point-in-time
MC: 5th pct equity > 0, fee breakeven > 2×, param sensitivity ±20%
Multiple testing: DSR > 0, PBO < 30%
Drift baseline: record out-of-sample stats ก่อน live
Security gate: subaccount + IP whitelist + secret scan + rollback
```

---

## Q20: Drift Detection Types + Action Tiers

**คำตอบสรุป:**

### 4 Drift Types — ตรวจตามลำดับ

**Data → Execution → Performance → Concept**

เหตุผล: Data drift ที่ตรวจไม่พบแสดงผลเหมือน Performance drift ทำให้ retune strategy โดยไม่จำเป็น

| Type | Detection | Response หลัก |
|------|-----------|--------------|
| Data | ws_lag >5s, reconnects >3/hr, spread >2× | Stale guard → REDUCE_ONLY |
| Execution | fill_rate <80%, slippage >2× backtest | Pause entries, fix code ทันที |
| Performance | rolling Sharpe ลด, PF < 1.0 | Action Tiers |
| Concept | regime distribution เปลี่ยน, per-regime PF เปลี่ยน | รัน regime_performance, retune |

### Action Tiers (Performance Drift)

```
📋 Watch:     Sharpe ลด 15-20% → log, monitor 1-2 สัปดาห์
⚠️ Warning:  Sharpe ลด 20-30% → ลด size 50%, review meeting
🔴 Critical: Sharpe ลด >30% หรือ PF < 1.0 ต่อเนื่อง → REDUCE_ONLY, rerun WF
🚨 Emergency: DD > backtest p95 หรือ daily loss > 2× → HALT ทันที
💀 Retire:   drift ไม่หาย 4+ สัปดาห์ → ยุติถาวร, post-mortem
```

**กฎสำคัญ:** กำหนด tier criteria ก่อน live ขณะคิดได้ปกติ ไม่ใช่ตอน losing

### Detection System Design

**Automated (background task):**
```python
class DriftMonitor:
    def classify_tier(self, metrics: dict) -> str:
        b = self.baseline
        if metrics['max_dd'] > b['backtest_p95_dd']:  return 'EMERGENCY'
        if metrics['sharpe'] < b['sharpe'] * 0.70:    return 'CRITICAL'
        if metrics['pf'] < 1.0:                        return 'CRITICAL'
        if metrics['fill_rate'] < b['fill_rate'] * 0.8: return 'WARNING'
        if metrics['sharpe'] < b['sharpe'] * 0.80:    return 'WARNING'
        return 'WATCH'
```

**Baseline:** First 90 วันของ live trading (ไม่ใช่ backtest stats)

**Cadence:**
```
Real-time: emergency check ทุก 60 วินาที
EOD:       rolling metrics update + alert routing
Weekly:    human review: live vs paper/backtest baseline
Monthly:   rerun walk-forward บน recent data
```

### Drift Decision Tree (Quick Reference)

```
เจอ anomaly:
1. Data drift? ws_lag / reconnects / spread → YES: stale guard
2. Execution drift? fill_rate / slippage → YES: pause entries, fix code
3. Performance tier?
   DD > backtest p95 → EMERGENCY HALT
   Sharpe < 70% baseline → CRITICAL: pause entries
   Sharpe < 80% baseline → WARNING: ลด size 50%
4. Concept drift? regime distribution เปลี่ยน → retune
5. Retire? Warning/Critical > 4 สัปดาห์ → RETIRE + post-mortem
```

**Key insight:** 73% ของ automated crypto accounts ล้มเหลวใน 6 เดือนเพราะไม่มี drift monitoring

---

## Q21: Framework Spikes — เลือก Platform อย่างไร

**คำตอบสรุป:**

### Framework Roles (2026)

**2026 split:** Vectorized (fast research) vs Event-driven (realistic execution)

| Framework | Best Role | ข้อดีหลัก | ข้อจำกัดหลัก |
|-----------|-----------|-----------|-------------|
| Freqtrade | MVP + Benchmark | crypto-native, deploy เร็ว, 39.9k stars | ติดกรอบ architecture |
| VectorBT | Research Lab | sweep 1000+ params, Monte Carlo ง่าย | ไม่ใช่ live engine |
| NautilusTrader | Advanced Production | Rust core, backtest=live code, nanosecond | learning curve สูงมาก |
| Backtrader | Learning/Legacy | docs เยอะ, event-driven concept | development หยุดแล้ว |
| Custom Engine | Full Control | ควบคุมทุกจุด | build นาน, เสี่ยง infrastructure bug |

### Spike Plan (ใช้ EMA Trend BTC/USDT 1h, data 2022-2024 เดียวกัน)

```
Spike A — Freqtrade (2-3 วัน):
  install + config → backtest → dry-run 1 wk → Telegram alerts
  คำถาม: Architecture จำกัดอะไร? custom logic ได้แค่ไหน?

Spike B — VectorBT (1-2 วัน):
  1000 param combinations + Monte Carlo 1000 paths
  คำถาม: Result ต่างจาก Freqtrade เท่าไหร่? fill model ส่งผลแค่ไหน?

Spike C — Custom Mini Engine (3-5 วัน):
  MarketDataEvent + BacktestBroker + RiskManager + PortfolioLedger
  คำถาม: effort จริงแค่ไหน? มี infrastructure bug ไหม?

Spike D — NautilusTrader (3-5 วัน):
  Rust build setup + Actor pattern strategy
  คำถาม: learning curve สูงแค่ไหน? worth the complexity?
```

**รวม ~2 สัปดาห์ — ดีกว่าลงทุน 3 เดือนกับ approach ผิด**

### Decision Framework หลัง Spike

```
1. Freqtrade ทำ custom logic ได้?        YES → use Freqtrade
2. Custom (Spike C) < 2wk MVP?           YES → build custom
3. Nautilus learning curve OK?           YES → use NautilusTrader
4. Results ต่างกันมากไหม?               NO  → fill model ไม่ critical → Freqtrade พอ
5. Need latency < 10ms?                  YES → NautilusTrader หรือ Rust
```

**NautilusTrader key facts:**
- identical strategy code backtest↔live (no code changes)
- learning curve: build complexity + paradigm shift + high-fidelity data
- API ยังเปลี่ยนบ่อย (breaking changes between releases)
- ไม่มี UI dashboard / AI tooling — focused on core engine

**2026 recommended path:** VectorBT research → Freqtrade validate → NautilusTrader production (หรือ custom ถ้าจำเป็น)

---

## Summary: Research Topics v3

```
✅ Bot Types
✅ Market Regime Detection (8 states)
✅ Architecture (Modular Monolith + Pipeline + Unified Broker)
✅ Risk Management (5 layers, conservative baseline)
✅ Backtesting & Validation (walk-forward, Monte Carlo)
✅ Data Layer & Exchange API (Parquet + SQLite, CCXT)
✅ Order Execution Engine (lifecycle, retry, safeguards)
✅ Security (Live Gate checklist)
✅ Monitoring & Alerting (3 pillars, 4 tiers, Telegram commands)
✅ Deployment & Infrastructure (VPS, Docker, systemd)
✅ Portfolio Ledger & Accounting (Position, Trade, P&L, Reconciliation)
✅ Startup Recovery & Reconciliation (6 states, 8-step sequence)
✅ Backtest-Live Unified Design (Broker Interface, fill models, 2 gaps)
✅ Codex v1 Comparison (Q14)
✅ Codex v2 Comparison (Q18)
✅ Validation Methodology ครบชุด — DSR, PBO, Survivorship Bias (Q19)
✅ Drift Detection 4 Types + Action Tiers (Q20)
✅ Framework Spikes A-D + Decision Framework (Q21)

⬜ Paper Broker Implementation Details
⬜ Backtest Engine Implementation (event loop detail)
⬜ Legal / Compliance / Exchange Rules
⬜ Order Type → Signal Urgency Mapping (full framework)
⬜ Funding Rate Arbitrage (futures, V5+)
```

---

*Raw Q&A Log v3 — รวมทุก session: Q1-Q13 (session 1), Q14-Q17 (session 2), Q18-Q21 (session 3)*
