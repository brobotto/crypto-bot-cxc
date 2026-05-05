# Crypto Trading Bot Research — Raw Q&A Log v4

> บันทึกคำถามและคำตอบจากการ research ทั้งหมด เรียงตามลำดับการสนทนา
> v4: เพิ่ม Q22-Q24 จาก session ที่ 4 (Codex v3 comparison, Calibration Gates, Jesse Spike, Dead Man's Switch)

---

## Q1-Q21 — ดูใน crypto_bot_qa_log_v3.md

(ไม่ duplicate เนื้อหาเดิม — ดูไฟล์ v3 สำหรับ Q1-Q21)

---

## Q22: Codex v3 มีอะไรที่เราขาดหรือเห็นต่างบ้าง?

**คำถาม:** ดู knowledge base v3 และ raw QA v3 ของ Codex — มีองค์ความรู้ที่น่าสนใจและเป็นประโยชน์อะไรบ้าง

**คำตอบสรุป:**

**สิ่งที่ Codex v3 มีและเราขาด — น่าเอาเข้าจริงๆ:**

1. **Calibration Target เป็น Multi-metric System** — เราบอก "Live Sharpe ≥ 60%" แบบ hard threshold แต่ Codex v3 เสนอ 3 gates แยก (BT→Paper, Paper→Small Live, Small Live→Full) พร้อม metrics ที่แตกต่างกันแต่ละ gate เช่น trade match rate ≥ 90%, order reject rate < 1-2%, unexpected position = 0 ซึ่งเราไม่มีเลย
2. **Reconciliation Frequency แบบ Tiered + Event-driven** — มี Active mode, Idle mode, และ Trigger-based (สำคัญกว่า schedule) รวม Rate-limit rule: reconciliation ต้องใช้ไม่เกิน 5-10% ของ REST budget
3. **Shutdown Policy แบบ Context-aware 5 ชนิด** — เพิ่ม FLATTEN_AND_CANCEL (cancel orders + close positions) และ Dead Man's Switch; KEEP_STOPS เฉพาะ verified server-side orders เท่านั้น
4. **Portfolio Ledger 8 Components + append-only ledger_events** — เพิ่ม Fee Ledger, Performance Attribution และ append-only ledger_events schema
5. **Startup Sequence 14 ขั้น + Single-bot Lock** — เพิ่ม DB single-bot lock, Load exchange metadata ก่อน reconcile, Classify drift severity
6. **Broker Interface Full Command/Query/Event + Capability Flags** — เพิ่ม OrderAccepted/Rejected/Canceled/Expired events และ capability flags (supports_post_only, supports_oco, supports_dead_man_switch ฯลฯ)

**จุดที่ Codex v3 เห็นต่าง — Codex พูดถูก:**
1. Calibration 60% เป็นแค่ heuristic ไม่ใช่ hard rule
2. KEEP_STOPS มีเงื่อนไขต้อง verify ก่อน ไม่ใช่ default blind
3. Startup state machine ควรมี BOOTING แยกจาก RECONCILING

**สิ่งที่ยืนยันตรงกัน:** Custom Modular Monolith, BrokerInterface เป็นจุด swap, Position from fills เท่านั้น, Always PAUSED ก่อน ACTIVE, Exchange wins inventory, Decimal, Spike A-D, Jesse เป็น research spike candidate

---

## Q23: Multi-metric Calibration Gates

**คำถาม:** Research Multi-metric Calibration Gates ต่อ

**คำตอบสรุป:**

### 3 Gates ระหว่าง Environments

```
Backtest → [Gate 1] → Paper Trading → [Gate 2] → Small Live 5% → [Gate 3] → Full Live
```

**Calibration tier (Sharpe retention):**
```
Good:        live/paper Sharpe ≥ 70% ของ conservative backtest
Acceptable:  50-70%
Warning:     30-50%
No-go/Pause: < 30% หรือ DD เกิน backtest p95
```

Note: 60% เป็นแค่ heuristic ไม่ใช่ hard rule

### Gate 1 Key Metrics (Backtest → Paper)

- Signal match rate ≥ 90%
- OOS Sharpe ≥ 60% ของ in-sample
- Monte Carlo 5th pct equity > 0
- Risk of ruin < 5%
- Fee model error < 5%
- Paper slippage 0.5x-2.0x ของ modeled

### Gate 2 Key Metrics (Paper → Small Live)

- Paper Sharpe ≥ 50% (Good: ≥ 70%)
- Fill rate ≥ 90%
- Order reject rate < 1% **HARD gate**
- Unexpected open position = 0 **HARD gate**
- Critical ledger mismatch = 0 **HARD gate**

### Gate 3 Key Metrics (Small Live → Full)

- Live Sharpe ≥ 70% (Acceptable: 50-70%)
- Live slippage ≤ 2x paper
- Order reject rate < 1-2%
- Capital scaling consistency: P&L per unit ≈ paper ±20%

### Capital Scaling Protocol

```
5% → Paper Gate 2 ผ่าน, monitor 30 วัน
10% → 5% stage 30 วัน, drift ≤ Watch
25% → Gate 3 preliminary, 60 วันรวม
50% → Gate 3 เต็ม, 30 วันที่ 25%
100% → 50% stage 30 วัน, stable
```

**ถ้า Drift tier ขึ้น Critical:** roll back capital ลง 1 ขั้น ทันที

### Implementation

```python
class CalibrationGate:
    HARD_GATES = ['unexpected_position==0', 'ledger_mismatch==0', 'drift≤Warning']
    SOFT_GATES_MIN_PASS = 4  # จาก 5 soft gates

    def evaluate(self) -> GateResult:
        if insufficient_data: return GateResult(INSUFFICIENT_DATA)
        if any hard gate fails: return GateResult(FAIL_HARD)
        if >2 soft gates fail: return GateResult(FAIL_SOFT)
        return GateResult(PASS)
```

**Key insight:** Deployment rules: Start with 5-10% of intended capital, run 30 days monitoring daily, if metrics match projections increase to 25%, after 60 days of consistency scale to full allocation.

---

## Q24: Jesse Framework Spike

**คำถาม:** Research Jesse Framework Spike ต่อ

**คำตอบสรุป:**

### Pricing Model (สำคัญมาก)

- **ฟรี (MIT):** backtest, Monte Carlo, optimization (GA), ML pipeline, JesseGPT
- **Paid (lifetime license):** live trading + paper trading กับ live market data
- เหตุผล: "without monetization this project will die like Gekko did"

### Monte Carlo — Unique Selling Point

Jesse มี 2 MC modes ใน dashboard:
1. **Trade-order shuffling** — ทดสอบว่า timing ของ trade ส่งผลแค่ไหน
2. **Candles-based** — ทดสอบ robustness กับ market noise

Jesse MC ให้: median equity, best/worst 5%, worst 5% drawdown, win/loss distribution

Jesse MC ไม่มี: fee/slippage stress test, risk of ruin, DSR/PBO → ต้องทำเพิ่มเอง

### Jesse vs Freqtrade Key Differences

| | Jesse | Freqtrade |
|---|---|---|
| MC built-in | ✅ 2 modes, dashboard | ❌ ทำเอง |
| Live trading | Paid plugin | ฟรี (MIT) |
| Exchange coverage | 4 exchanges | CCXT 100+ |
| Community | ~5k stars | ~39.9k stars |
| Single maintainer | ⚠️ ใช่ | ✅ community |

### Spike Plan (ทำตามลำดับ)

```
Step 1 (ฟรี, 0.5-1 วัน): Backtest spike
  → เปรียบ result กับ Freqtrade Spike A
  → ประเมิน strategy syntax

Step 2 (ฟรี, 0.5-1 วัน): Monte Carlo spike
  → รัน 2 MC modes
  → เปรียบกับ VectorBT MC

Step 3 (ฟรี, 0.5 วัน): Optimization spike
  → ประเมิน GA workflow

Step 4 (Paid, optional): Live plugin
  → ประเมินเมื่อ Steps 1-3 ผ่านแล้วพอใจ
```

### Hybrid Decision (แนะนำ)

```
Jesse free tier → research + backtest + Monte Carlo
Freqtrade       → live production deployment
→ ได้ประโยชน์จากทั้งสอง ไม่ต้องซื้อ Jesse live plugin
→ ข้อเสีย: ต้องเรียน 2 syntax, port strategy เมื่อ go live
```

### Decision Framework

```
Jesse wins:    MC workflow เร็วกว่าชัดเจน + ยอมจ่าย paid
Freqtrade:     MC ไม่ต่างมาก + ต้องการ CCXT 100+ + community
Hybrid:        ทำ Steps 1-3 ก่อน ค่อยตัดสินใจ
```

---

## Q25: Dead Man's Switch (DMS)

**คำถาม:** Research Dead Man's Switch ต่อ

**คำตอบสรุป:**

### DMS คืออะไร

Exchange-side mechanism: bot ส่ง heartbeat ทุก N วินาที ถ้าหมดเวลา exchange cancel all orders อัตโนมัติ

**กฎสำคัญที่สุด:** Cancel orders เท่านั้น — ไม่ close positions

### Exchange Support Matrix

| Exchange | Spot | Futures | Notes |
|----------|------|---------|-------|
| Binance | ❌ ไม่มี | ✅ per-symbol (ms) | V1 target ของเรา = ไม่มี DMS |
| Bybit | ⚠️ ต้องตรวจ | ⚠️ ต้องตรวจ | ยังไม่ confirmed |
| Kraken | ✅ global (seconds) | ✅ global | ดีที่สุด |
| OKX | ⚠️ expTime per-order | ⚠️ expTime | ไม่ใช่ global DMS |
| Coinbase | ❌ ไม่มี | ❌ ไม่มี | — |

### Gotchas สำคัญ

```
1. DMS ≠ Position Close (ย้ำอีกครั้ง)
2. Binance Futures: per-symbol ต้อง heartbeat แยกทุก symbol
3. ต้อง deactivate DMS ก่อน graceful shutdown (timeout=0)
4. Reconcile DMS state ตอน startup
```

### Implementation Pattern

```python
# Exchange DMS (Binance Futures)
async def heartbeat_loop():
    while active:
        await exchange.cancel_all_orders_after(countdown_ms)  # reset countdown
        await asyncio.sleep(heartbeat_s)

# Software DMS (Binance Spot — ไม่มี exchange DMS)
async def watchdog_loop():
    while active:
        age = time.time() - last_heartbeat
        if age > cancel_after_s:
            await emergency_cancel_all()
            break
        await asyncio.sleep(check_interval_s)
```

### Settings แนะนำ

```
countdown_time:     120s
heartbeat_interval: 30s (countdown / 4)
```

### Decision สำหรับโปรเจคนี้

```
V1 (Binance Spot):      Software watchdog loop เท่านั้น
V5 (Binance Futures):   Exchange DMS + Software watchdog backup
```

---

## Summary: Research Topics v4

```
✅ Bot Types (Q1)
✅ Multi-strategy approach (Q2)
✅ Market Regime Detection 8 states (Q3)
✅ Architecture Patterns (Q4)
✅ EDA vs Microservices vs Agent (Q5)
✅ Research gaps (Q6)
✅ Risk Management 5 layers (Q7)
✅ Backtesting & Validation (Q8)
✅ Data Layer & Exchange API (Q9)
✅ Order Execution Engine (Q10)
✅ Security + Live Gate (Q11)
✅ Monitoring & Alerting (Q12)
✅ Deployment & Infrastructure (Q13)
✅ Codex v1 comparison (Q14)
✅ Framework Decision + Spikes A-D (Q15)
✅ Strategy V1 = Backtest-first (Q16)
✅ Validation Methodology: DSR, PBO, Survivorship (Q17)
✅ Operational Security Checklist (Q18)
✅ Codex v2 comparison (Q19)
✅ Jesse Framework initial (Q20)
✅ FinRL-X 2 Deployment Gaps (Q21)
✅ Calibration Targets initial (Q22 — covered in Codex v2 comparison)
✅ Reconciliation Frequency (Q23)
✅ Shutdown Policy 5 types (Q24)
✅ Portfolio Ledger deep dive (Q25)
✅ Startup Recovery deep dive (Q26)
✅ Unified Broker Design (Q27)
✅ Jesse Framework Comparison (Q28)
✅ Codex v3 comparison (Q22 v4)
✅ Multi-metric Calibration Gates (Q23 v4)
✅ Jesse Framework Spike (Q24 v4)
✅ Dead Man's Switch (Q25 v4)

⬜ Paper Broker Implementation Details
⬜ Backtest Engine Implementation (warmup, event loop)
⬜ Legal / Compliance / Exchange Rules
⬜ Order Type → Signal Urgency Mapping
⬜ Funding Rate Arbitrage (V5+)
⬜ Append-only Ledger Events Pattern (implementation detail)
```

---

*Raw Q&A Log v4 — รวมทุก session: Q1-Q17 (session 1-2), Q18-Q21 (session 3), Q22-Q25 (session 4)*
