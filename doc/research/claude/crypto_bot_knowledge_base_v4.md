# Crypto Trading Bot — Knowledge Base v4

> องค์ความรู้แบบแยกหมวดหมู่ พร้อม design decisions และ recommended stack
> อัปเดตครั้งที่ 4 — เพิ่ม Multi-metric Calibration Gates (3 gates, capital scaling), Jesse Framework Evaluation (spike plan, hybrid decision), Dead Man's Switch (exchange matrix, software watchdog) จาก Codex v3 research

---

## 📋 สารบัญ

1. [ภาพรวม Bot Types](#1-ภาพรวม-bot-types)
2. [Market Regime Detection](#2-market-regime-detection)
3. [Architecture Patterns](#3-architecture-patterns)
4. [Risk Management Framework](#4-risk-management-framework)
5. [Backtesting & Validation](#5-backtesting--validation)
6. [Data Layer & Exchange API](#6-data-layer--exchange-api)
7. [Order Execution Engine](#7-order-execution-engine)
8. [Security](#8-security)
9. [Monitoring & Alerting](#9-monitoring--alerting)
10. [Deployment & Infrastructure](#10-deployment--infrastructure)
11. [Portfolio Ledger & Accounting](#11-portfolio-ledger--accounting)
12. [Startup Recovery & Reconciliation](#12-startup-recovery--reconciliation)
13. [Backtest-Live Unified Design](#13-backtest-live-unified-design)
14. [Validation Methodology & Bias Controls]
15. [Drift Detection & Action Tiers]
16. [Framework Selection & Spikes]
17. [Multi-metric Calibration Gates]
18. [Jesse Framework Evaluation]
19. [Dead Man's Switch (DMS)]
20. [Design Decisions Summary](#14-design-decisions-summary)
21. [Version Roadmap](#15-version-roadmap)
22. [กฎสำคัญที่ต้องจำ](#16-กฎสำคัญที่ต้องจำ)

---

## 1. ภาพรวม Bot Types

### ตารางเปรียบเทียบ

| Bot Type | Market Phase | ทุนเริ่มต้น | ความยาก | Risk |
|----------|-------------|------------|---------|------|
| Grid Trading | Sideways | $200+ | ง่าย | ปานกลาง |
| DCA | Bull / Long-term | $50+ | ง่ายมาก | ต่ำ |
| Trend Following | Bull / Bear | $500+ | ปานกลาง | ปานกลาง-สูง |
| Arbitrage | ทุกสภาวะ | $5,000+ | ยาก | ต่ำ-ปานกลาง |
| Market Making | ทุกสภาวะ | สูงมาก | ยากมาก | ปานกลาง-สูง |
| AI / ML | ทุกสภาวะ | ปานกลาง-สูง | ยากมาก | แปรผัน |
| Rebalancing | Long-term hold | ต่ำ-ปานกลาง | ง่าย | ต่ำ |

> **หมายเหตุสำคัญ:** AI/ML ควรทำหน้าที่เป็น analyst layer ไม่ใช่ execution authority โดยตรง ต้องมี rule-based guardrail เสมอ

### จุดประสงค์หลัก 7 แบบ

```
สะสมระยะยาว:        DCA, Auto-invest
กินความผันผวน:       Grid, Mean Reversion
เกาะ trend:          Trend-following, Breakout
หากำไรราคาคลาดเคลื่อน: Arbitrage, Funding-rate Arbitrage
ทำตลาด:             Market Making
จัดพอร์ต/ลดความเสี่ยง: Rebalancing, Hedging
ช่วย execution:      TWAP, Iceberg, Smart Order Routing
```

### แนวทาง Multi-strategy

```
แนวทางที่ 1 (Beginner):    Bot เดี่ยว — ยอมรับว่า underperform ในบาง phase
แนวทางที่ 2 (Recommended): Grid 50% + Trend 30% + DCA 20%
แนวทางที่ 3 (Advanced):    Market Detection → Auto-switch strategy
```

### ✅ Design Decision
> เริ่มด้วย **V1 strategy เดียว** (Grid หรือ simple Trend) — architecture รองรับ multi-strategy ตั้งแต่แรก แต่ implement ทีละ strategy

---

## 2. Market Regime Detection

### เปรียบเทียบวิธี

| Method | Complexity | Accuracy | เหมาะเริ่มต้น |
|--------|-----------|----------|--------------|
| Rule-based (ADX + BBW + EMA) | ต่ำ | ปานกลาง | ✅ ใช่ |
| Volatility-based (ATR) | ต่ำ | ปานกลาง | ✅ ใช่ |
| Volume / Liquidity Regime | ต่ำ-ปานกลาง | ดี | ✅ ใช่ (เพิ่มเป็น filter) |
| HMM | ปานกลาง | ดี | ❌ (Phase 2) |
| ML Classifier | ยาก | ดีมาก | ❌ (Phase 2) |
| HMM + LSTM | ยากมาก | สูงสุด | ❌ (Advanced) |

### Regime States ที่แนะนำ (8 states)

```
UPTREND_LOW_VOL      — trend ขึ้น volatility ปกติ → เหมาะ trend bot
UPTREND_HIGH_VOL     — trend ขึ้นแต่ผันผวนสูง → ลด size
DOWNTREND_LOW_VOL    — trend ลง → cash หรือ cautious
DOWNTREND_HIGH_VOL   — trend ลง volatile → ระวังมาก
SIDEWAYS_LOW_VOL     — แกว่งตัว volatility ต่ำ → เหมาะ grid
SIDEWAYS_HIGH_VOL    — แกว่งตัว volatile → grid ระวัง range หลุด
BREAKOUT_WATCH       — compression สูง กำลังจะ breakout
NO_TRADE             — volume/liquidity ต่ำ, spread กว้าง, data stale
```

> **เพิ่มจาก Codex:** Volume + Spread เป็น regime input สำคัญ ไม่ใช่แค่ risk filter — `NO_TRADE` state ป้องกัน trade ในช่วง low-liquidity

### Rule-based Baseline (Phase 1)

```python
def detect_regime(adx, ema_short, ema_long, bb_width, bb_width_avg,
                  volume, avg_volume, spread, max_spread):

    # No-trade conditions ตรวจก่อนเสมอ
    if spread > max_spread:
        return "NO_TRADE"
    if volume < avg_volume * 0.3:
        return "NO_TRADE"

    # Trend detection
    is_uptrend   = adx > 25 and ema_short > ema_long
    is_downtrend = adx > 25 and ema_short < ema_long
    is_sideways  = adx < 20
    is_high_vol  = bb_width > bb_width_avg * 1.5
    is_squeeze   = bb_width < bb_width_avg * 0.5

    if is_squeeze:
        return "BREAKOUT_WATCH"
    if is_uptrend:
        return "UPTREND_HIGH_VOL" if is_high_vol else "UPTREND_LOW_VOL"
    if is_downtrend:
        return "DOWNTREND_HIGH_VOL" if is_high_vol else "DOWNTREND_LOW_VOL"
    if is_sideways:
        return "SIDEWAYS_HIGH_VOL" if is_high_vol else "SIDEWAYS_LOW_VOL"
    return "NO_TRADE"  # transition zone
```

### ✅ Design Decision
> Phase 1: **ADX + BBW + EMA + Volume/Spread filter** (8 states) → Phase 2: **HMM** เมื่อมี baseline performance

---

## 3. Architecture Patterns

### High-level Flow (Unified)

```
Market Data Event
  → Feature / Indicator Engine
  → Regime Detector
  → Strategy Engine          ← strategy code เดิมทุก mode
  → OrderIntent
  → Risk Manager             ← ห้าม bypass
  → Execution Engine
  → Broker Interface         ← swap ตาม mode (backtest/paper/live)
  → Fill Event
  → Portfolio Ledger         ← update position + P&L
  → Monitoring / Alerts
```

### Module Structure

```
crypto-bot/
├── data/
│   ├── exchange_client.py      # CCXT wrapper
│   ├── websocket_manager.py    # WS + reconnect
│   ├── data_validator.py       # Anomaly detection, stale guard
│   ├── ohlcv_store.py          # Parquet + SQLite
│   └── feature_engine.py       # Indicator calculation
├── regime/
│   ├── detector.py             # Rule-based (Phase 1)
│   └── hmm_detector.py         # Phase 2
├── strategy/
│   ├── base_strategy.py        # Abstract class (ไม่รู้ mode)
│   ├── grid_strategy.py
│   ├── dca_strategy.py
│   └── trend_strategy.py
├── risk/
│   ├── position_sizer.py
│   ├── stop_loss.py
│   ├── portfolio_risk.py
│   └── circuit_breaker.py
├── execution/
│   ├── order_executor.py
│   ├── retry_manager.py
│   └── kill_switch.py
├── broker/
│   ├── base_broker.py          # Abstract interface ← จุดสำคัญ
│   ├── backtest_broker.py      # Historical simulation
│   ├── paper_broker.py         # Live price, simulated fill
│   └── live_broker.py          # Real exchange
├── ledger/
│   ├── position_manager.py     # Track open positions
│   ├── trade_log.py            # Fill history
│   ├── pnl_calculator.py       # Realized / Unrealized
│   └── reconciler.py           # Compare with exchange
├── monitoring/
│   ├── metrics.py              # Prometheus
│   ├── alert.py                # Telegram + email
│   └── logger.py               # Structured JSON
└── config/
    ├── settings.py             # Load from .env
    └── strategy_config.yaml
```

### Key Principles

```
1. Strategy code ไม่รู้ว่าอยู่ใน backtest, paper, หรือ live
2. Strategy ต้องไม่ส่ง order ตรงถึง exchange เด็ดขาด
3. ทุก order ผ่าน Risk Manager → Execution Engine → Broker Interface
4. Portfolio Ledger เป็น single source of truth ของ bot
```

### ✅ Design Decision
> **Modular Monolith + Pipeline pattern + Event-inspired internals + Microservice-ready boundaries**

---

## 4. Risk Management Framework

### Layer 1 — Trade Level

```python
# Position Sizing
position_size = (account_balance * risk_pct) / (entry_price - stop_loss_price)
# ATR-based
atr_stop      = atr * atr_multiplier  # 2.0×
position_size = (account_balance * risk_pct) / atr_stop

RISK_PER_TRADE  = 0.005   # 0.5-1% ต่อ trade (conservative baseline)
ATR_MULTIPLIER  = 2.0
MAX_POSITION    = 0.10    # max 10% ต่อ pair
```

#### Stop-Loss Types
| Type | สูตร | เหมาะกับ |
|------|------|---------|
| Fixed % | `SL = Entry × (1 - stop_pct)` | เริ่มต้น |
| ATR | `SL = Entry - (ATR × 2.0)` | แนะนำ |
| Trailing | ขยับตาม price ขึ้น | Trend following |
| Time-based | ถือ > N ชั่วโมง → ออก | ป้องกัน dead trade |

### Layer 2 — Session Level

```python
CIRCUIT_BREAKERS = {
    'daily_loss_limit':        0.02,   # 2% (conservative V1)
    'max_drawdown_from_peak':  0.10,   # 10% (conservative V1)
    'consecutive_losses':       5,
    'max_daily_trades':         50,
}
```

#### Recovery Math (ต้องจำ)
```
10% loss → ต้องการ 11.1% gain
25% loss → ต้องการ 33.3% gain
50% loss → ต้องการ 100% gain
```

### Layer 3 — Portfolio Level

```python
PORTFOLIO_RULES = {
    'spot_only':                 True,   # V1: spot เท่านั้น
    'max_correlated_positions':  3,
    'active_capital_ratio':      0.60,   # deploy 60%, reserve 40%
    'max_open_positions':        3,
    'spread_filter':             True,
    'stale_data_guard':          True,
}
```

### Layer 4 — Volatility-adaptive (Phase 2)

```python
def drawdown_scaled_size(base_size, current_drawdown, max_drawdown):
    scale = 1 - (current_drawdown / max_drawdown)
    return base_size * max(scale, 0.25)  # ลดได้สูงสุด 75%

def vol_adjusted_stop(base_stop, current_atr, avg_atr):
    return base_stop * (current_atr / avg_atr)
```

### Layer 5 — Execution Risk

```python
EXECUTION_GUARDS = {
    'max_spread_pct':   0.005,   # 0.5% max spread
    'max_slippage_pct': 0.002,   # 0.2% BTC/ETH, 0.5% altcoin
    'stale_price_age':  30,      # วินาที
}
```

### ✅ Design Decision
> **Conservative baseline V1:** risk 0.5-1%/trade + ATR stop + Daily limit 2% + Peak drawdown 10% + spot only + max 3-5 positions

---

## 5. Backtesting & Validation

### Workflow

```
1. Develop strategy
2. Simple backtest (in-sample) — idea validation
3. Walk-forward test — robustness check
4. Monte Carlo simulation — edge case testing
5. Paper trade (live market, simulated fill) — V2 milestone
6. Live trade (small capital) — scale ขึ้นเมื่อ proven
```

### Walk-Forward Protocol

```python
# Overfitting check
if out_of_sample_sharpe < in_sample_sharpe * 0.6:
    print("OVERFIT — do not deploy")
if out_of_sample_max_dd > in_sample_max_dd * 2.0:
    print("OVERFIT — do not deploy")
```

### Key Backtest Rules

```
✅ causal indicators only (no repainting)
✅ warmup period = max(all indicator lookback periods)
✅ next-candle execution (ห้าม fill บน signal candle)
✅ is_closed = True เท่านั้นก่อน generate signal
✅ realistic fee + slippage (conservative model)
✅ out-of-sample testing แยกจาก optimization data
✅ walk-forward สำหรับ optimized parameters
✅ benchmark vs buy-and-hold BTC เสมอ
✅ regime_performance.csv — performance แยกต่อ regime
```

### Transaction Cost Model (Conservative)

```python
COSTS = {
    'fee_multiplier':  2.0,         # fee × 2 สำหรับ stress test
    'slippage': {
        'top_10':   0.001,          # 0.1% BTC/ETH
        'altcoin':  0.003,          # 0.3%
    },
    'latency_ms': 200,
}
# Stress test: ยังกำไรหลัง costs ทั้งหมด = robust
```

### Required Metrics

```
Sharpe Ratio     > 1.0 (ดี) / > 2.0 (ดีมาก สำหรับ crypto)
Sortino Ratio    > 1.0
Calmar Ratio     > 1.0 (Annual Return / Max Drawdown)
Profit Factor    > 1.5 (Gross Profit / Gross Loss)
Expectancy       > 0 (win_rate × avg_win + loss_rate × avg_loss)
Max Drawdown     < 20%
Max Consecutive Loss — ต้องรับได้ทางจิตวิทยา
Benchmark vs BTC — ต้องชนะ buy-and-hold ถึงจะ justify complexity
```

### Output Files

```
trades.csv           — รายละเอียดทุก trade
equity_curve.csv     — equity over time
summary.json         — metrics สรุป
monthly_returns.csv  — return รายเดือน
regime_performance.csv — performance แยกต่อ regime
```

### Framework Recommendation

```
Crypto bot (V1):   Freqtrade (production-proven, community 39.9k stars)
Parameter sweep:   VectorBT (vectorized, เร็วมากสำหรับ research)
Advanced engine:   NautilusTrader (backtest-live parity, Rust core)
Custom engine:     ดู section Framework Selection & Spikes ก่อนตัดสินใจ
```

> **สำคัญ:** ทำ Spike A-D ก่อน commit กับ custom engine — ดูรายละเอียดใน Section 16

---

## 6. Data Layer & Exchange API

### Architecture

```
Exchange WebSocket ──┐
Exchange REST API ───┼──→ [Normalizer] → [Validator] → [Parquet/SQLite] → Strategy
Third-party API ─────┘

Storage:
  Parquet:   historical OHLCV candles (columnar, compressed)
  SQLite:    operational data (orders, fills, positions, balances, state)
  YAML/JSON: config
  DuckDB:    analytics queries บน Parquet (later)
  Postgres:  production multi-bot ledger (later)
```

### CCXT Pattern

```python
exchange = ccxt.binance({'apiKey': ..., 'enableRateLimit': True})

# เปลี่ยน exchange แค่บรรทัดนี้
# WS สำหรับ data, REST สำหรับ orders
async def watch_ohlcv():
    while True:
        ohlcv = await exchange.watch_ohlcv('BTC/USDT', '1h')
        process(ohlcv)
```

### WebSocket Resilience

```python
async def websocket_manager():
    backoff = 1
    while True:
        try:
            await connect_and_stream()
            backoff = 1
        except Exception:
            await asyncio.sleep(min(backoff, 60))
            backoff *= 2  # exponential backoff
```

### Data Quality Rules

```
timestamps ต้อง UTC
ไม่มี duplicate candles
detect missing candles
reject non-closed candles สำหรับ signal generation
detect stale live feed (>30 วินาที = NO_TRADE)
resync หลัง WebSocket gap/disconnect
```

### Exchange Connector Architecture

```
Internal Exchange Interface
  → CCXT REST Adapter         (REST operations)
  → Native WebSocket Adapter  (real-time streams)

Rule: Strategy ต้องไม่คุยกับ exchange โดยตรง
```

### Exchange Metadata Validation (ก่อน submit order)

```python
checks = [
    symbol_is_active,
    price_matches_tick_size,
    amount_matches_step_size,
    amount >= min_amount,
    notional >= min_notional,
    order_type_supported,
    rate_limit_ok,
]
```

---

## 7. Order Execution Engine

### Order Lifecycle

```
CREATED → SUBMITTED → ACCEPTED → PARTIALLY_FILLED → FILLED
                    ↘ REJECTED
                    ↘ CANCELED
                    ↘ EXPIRED
                    ↘ FAILED
```

### Order Type Selection

```python
def select_order_type(urgency, liquidity):
    if urgency == 'STOP_LOSS' or urgency == 'EMERGENCY':
        return 'MARKET'
    elif urgency == 'ARBITRAGE':
        return 'FOK'
    elif liquidity == 'GOOD' and not time_critical:
        return 'LIMIT'  # cheaper maker fee
    return 'LIMIT'      # default
```

### V1 Order Support

```
MARKET, LIMIT, POST_ONLY_LIMIT, STOP_LOSS, TAKE_PROFIT, CANCEL/REPLACE
```

### Retry Logic

```python
async def submit_with_retry(params, max_retries=3):
    params['clientOrderId'] = generate_unique_id()
    for attempt in range(max_retries):
        try:
            existing = await check_existing(params['clientOrderId'])
            if existing: return existing
            return await exchange.create_order(**params)
        except NetworkError:
            await asyncio.sleep(min(2**attempt + jitter(), 30))
    return await market_order_fallback(params)
```

### Required Safety Rules

```
ทุก order ต้องมี clientOrderId
retry ด้วย clientOrderId เดิม
query ก่อน retry หลัง timeout
partial fill ต้อง update position + stop size
cancel ไม่ได้แปลว่า fill ไม่เกิด
reconcile หลัง restart และ disconnect
```

### Safeguards

```python
SAFEGUARDS = {
    'max_slippage_pct':     0.002,
    'max_order_notional':   1000,    # USDT
    'max_orders_per_min':   20,
    'price_sanity_pct':     0.05,    # 5% จาก current price
    'kill_switch':          True,
}
```

---

## 8. Security

### API Key Permissions

```
READ:     ✅ required
TRADE:    ✅ required (live bot key only)
TRANSFER: ⚠️ ปิดถ้าไม่จำเป็น
WITHDRAW: 🚫 ห้ามเด็ดขาด
```

### Environment Separation

```
backtest → ไม่ต้องการ API key
paper    → read-only key
testnet  → testnet key
live     → trade key (no withdraw, IP whitelist)
```

### Secure Storage

```python
# .env (ไม่ commit, ใส่ใน .gitignore)
API_KEY=xxx
API_SECRET=yyy

# .env.example (commit ได้ — แค่ชื่อ field)
API_KEY=
API_SECRET=
```

### Runtime Safety States

```
ACTIVE      — ทำงานปกติ
HALTED      — หยุดทุกอย่าง รอ human
REDUCE_ONLY — ปิด position เก่าได้, ห้าม entry ใหม่
```

### Security Checklist

```
[ ] ปิด withdrawal permission บน bot key
[ ] เปิด IP whitelist (VPS IP เท่านั้น)
[ ] .env ใน .gitignore + permission 600
[ ] เปิด withdrawal address whitelist บน exchange
[ ] เปิด 2FA (authenticator app ไม่ใช่ SMS)
[ ] Subaccount แยกสำหรับ bot
[ ] Max capital limit ใน config
[ ] SSH key แทน password
[ ] pin dependency versions + lockfile
[ ] scan vulnerabilities (Dependabot)
[ ] ห้าม log API key, secret, signature ในทุกกรณี
[ ] central secret loader with redaction
[ ] startup safety checklist required
```

### Incident Response

```
1. Halt bot + set HALTED state
2. Cancel all open orders
3. Disable / delete API key
4. Rotate key
5. Export logs + fills
6. Reconcile balances
7. Review root cause
8. Restart เฉพาะเมื่อ state clean
```

---

## 9. Monitoring & Alerting

### 3 Pillars of Observability

```
Metrics → "what is happening?"   — Prometheus + Grafana
Logs    → "what happened?"       — Structured JSON + Loki
Traces  → "why did it happen?"   — Signal → fill latency chain
```

### Required Metrics

```python
# Financial
bot_pnl_usdt           = Gauge('daily P&L')
bot_drawdown_pct        = Gauge('current drawdown from peak')
bot_win_rate            = Gauge('rolling 30d win rate')

# Execution
bot_fill_latency        = Histogram('signal to fill seconds')
bot_orders_total        = Counter('total orders', ['status'])
bot_stuck_orders        = Gauge('stuck orders count')

# System
bot_websocket_uptime    = Gauge('WS uptime %')
bot_market_data_lag     = Gauge('data lag seconds')
bot_heartbeat_age       = Gauge('last heartbeat age')
```

### Alert Tiers

| Tier | Action | ตัวอย่าง |
|------|--------|---------|
| 🔴 Critical | ภายใน 5 นาที | drawdown >10%, WS down >5min, API auth fail, kill switch, live mode start |
| 🟡 Warning | ภายใน 30 นาที | fill rate <80%, slippage >2× backtest, stuck order, partial fill unresolved |
| 🔵 Info | Daily review | trade executed, daily P&L summary |
| ⚪ Silent | Log only | API request/response, heartbeat, polling |

### Telegram Remote Commands

```
/status          — bot state, uptime, current regime
/positions       — open positions + P&L
/orders          — open orders
/pnl             — daily / cumulative P&L
/pause_entries   — ไม่ entry ใหม่ (REDUCE_ONLY)
/resume_entries  — กลับ ACTIVE
/halt            — HALTED + cancel all
/cancel_all      — cancel open orders
```

### Performance Review Cadence

```
ทุกวัน (5 min):     P&L, error count, fill rate
ทุกสัปดาห์ (30 min): performance vs backtest baseline
ทุกเดือน (2 hr):    rolling Sharpe, strategy health, parameter review
ทุกไตรมาส (1 day):  walk-forward re-test, re-optimization
```

### Strategy Drift Signals

```
Sharpe ลด > 30% จาก baseline
Win rate เปลี่ยน > 10% โดยไม่มีเหตุผล
Avg slippage เพิ่ม > 2× จาก backtest
Profit factor < 1.0 ต่อเนื่อง > 2 สัปดาห์
```

---

## 10. Deployment & Infrastructure

### Phase Roadmap

```
Phase 1: Local dev + backtest + paper trading (development)
Phase 2: VPS + Docker Compose (first live)
Phase 3: Hardened VPS production
Phase 4: Cloud/Kubernetes (เฉพาะเมื่อ scale จริง)
```

### VPS Selection

```
Strategy ทั่วไป:    Hetzner CX21 €5.83/mo (EU) หรือ Vultr $6/mo
Spec:               2 vCPU, 4GB RAM, 40GB SSD, Ubuntu 24.04 LTS
OS:                 Ubuntu 24.04 LTS

Exchange → VPS Location:
  Binance EU   → Frankfurt/Amsterdam (Hetzner)
  Bybit        → Singapore (Vultr)
  OKX          → Singapore
  Coinbase     → US East / Virginia
```

### Process Management

```ini
# /etc/systemd/system/crypto-bot.service
[Unit]
Description=Crypto Trading Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/crypto-bot
ExecStart=/home/botuser/.venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/home/botuser/crypto-bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable crypto-bot
sudo systemctl start crypto-bot
```

### Docker Compose Stack

```yaml
services:
  bot:
    build: .
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

  prometheus:
    image: prom/prometheus:latest
    restart: always

  grafana:
    image: grafana/grafana:latest
    restart: always

  loki:
    image: grafana/loki:latest
    restart: always
```

### Deployment Checklist

```
[ ] รัน test suite ก่อน deploy
[ ] Backup config + state
[ ] Close open positions (major change only)
[ ] Deploy ช่วง low-volatility (weekend)
[ ] ตรวจ log 5 นาทีหลัง restart
[ ] ตรวจ Telegram: bot ส่ง "Bot started" ไหม
[ ] มี rollback plan
```

### Recommended Stack ตาม Scale

```
Starter ($6-10/mo):       VPS 2-4GB + Ubuntu + systemd + .env + Telegram
Intermediate ($15-30/mo): 4GB + Docker Compose + Prometheus + Grafana + GitHub Actions
Advanced ($50+/mo):       Multiple VPS + Blue-green + Full observability
HFT ($300+/mo):           Co-location + Dedicated server + Rust/C++
```

---

## 11. Portfolio Ledger & Accounting

### ภาพรวม — ทำไมถึงสำคัญ

Portfolio Ledger ทำหน้าที่เป็น **"ความจริงภายใน"** ของ bot ประกอบด้วย:

```
Position Manager    — track open positions ทุกตัว
Trade Ledger        — บันทึก fills ทุกรายการ
Balance Tracker     — ติดตาม cash / free / reserved
P&L Calculator      — unrealized + realized + daily
Reconciliation Engine — เปรียบกับ exchange จริง
```

### Data Model

#### Position

```python
@dataclass
class Position:
    position_id:    str       # UUID
    strategy_id:    str
    symbol:         str       # 'BTC/USDT'
    side:           str       # 'LONG' | 'SHORT'
    status:         str       # 'OPEN' | 'CLOSED' | 'PARTIAL'
    quantity:       Decimal   # ต้องใช้ Decimal ไม่ใช่ float
    avg_entry:      Decimal   # weighted average price
    stop_loss:      Decimal | None
    take_profit:    Decimal | None
    entry_fee:      Decimal
    unrealized_pnl: Decimal   # update real-time
    realized_pnl:   Decimal   # update on partial/full close
    opened_at:      datetime  # UTC
    closed_at:      datetime | None
    regime:         str       # regime ณ เวลา entry
```

#### Trade (Fill Record)

```python
@dataclass
class Trade:
    trade_id:          str
    position_id:       str       # FK → Position
    order_id:          str
    client_order_id:   str
    symbol:            str
    side:              str       # 'BUY' | 'SELL'
    quantity:          Decimal
    price:             Decimal   # actual fill price
    fee:               Decimal
    fee_currency:      str
    realized_pnl:      Decimal | None
    is_entry:          bool
    filled_at:         datetime
    exchange_trade_id: str
```

### P&L Formulas

```python
# Unrealized P&L (ไม่รวม fee — เป็นแค่ estimate)
unrealized_long  = (current_price - avg_entry) * quantity
unrealized_short = (avg_entry - current_price) * quantity

# Realized P&L (รวม fee — เงินที่ได้จริง)
realized_long  = (exit_price - avg_entry) * quantity - entry_fee - exit_fee
realized_short = (avg_entry - exit_price) * quantity - entry_fee - exit_fee

# Average Entry (Partial fills / Scale-in)
new_avg = (old_avg * old_qty + fill_price * fill_qty) / (old_qty + fill_qty)

# Total Equity
equity = cash_balance + sum(position_value + unrealized_pnl)

# Drawdown from Peak
drawdown = (peak_equity - current_equity) / peak_equity
```

> **สำคัญ:** ใช้ `Decimal` ไม่ใช่ `float` ทุกกรณี — floating-point error สะสมได้

### Reconciliation Types

```
BALANCE_DRIFT     → drift เล็ก: adjust | drift ใหญ่: HALT + alert
MISSING_FILL      → update position, recalc P&L
ORPHAN_ORDER      → cancel หรือ adopt ตาม policy
STALE_POSITION    → close ใน internal state
SIZE_MISMATCH     → adjust to exchange size + alert
```

### Reconciliation Rule

> เมื่อ internal ≠ exchange → **เชื่อ exchange เสมอ** แต่ต้อง alert ก่อน adjust

### Edge Cases ที่ต้องจัดการ

```
1. Partial Fill + Scale-in    → recalc avg_entry ทุกครั้ง
2. Fill ระหว่าง Downtime      → fetch fills since last_seen ตอน startup
3. Dust Position              → threshold + policy: roll into next หรือ liquidate
4. Fee ใน Base Currency       → convert เป็น quote ก่อน P&L
5. Cancel Race Condition      → ตรวจ fill event ก่อน update state
6. Multi-fill per Order       → aggregate fills → single position
```

### Performance Tracking per Regime

```csv
# regime_performance.csv
regime,trades,win_rate,avg_pnl,profit_factor
SIDEWAYS_LOW_VOL,45,0.62,12.3,1.8
UPTREND_LOW_VOL,23,0.78,34.1,3.2
DOWNTREND_HIGH_VOL,18,0.33,-8.7,0.6
```

---

## 12. Startup Recovery & Reconciliation

### Bot State Machine

```
INITIALIZING → RECONCILING → PAUSED → ACTIVE ↔ REDUCE_ONLY
                           ↘ HALTED (error/human needed)
                                    ↗ RECONCILING (after review)
```

| State | หน้าที่ | Trade? |
|-------|--------|--------|
| INITIALIZING | โหลด config, เชื่อม exchange | ❌ |
| RECONCILING | เปรียบ internal vs exchange | ❌ |
| PAUSED | รอ approve / auto-resume | ❌ |
| ACTIVE | ทำงานปกติ | ✅ |
| REDUCE_ONLY | ปิด position เก่า ห้าม entry ใหม่ | ⚠️ exit only |
| HALTED | หยุดทุกอย่าง รอ human | ❌ |

### Startup Sequence (8 ขั้นตอน — ห้ามข้าม)

```python
async def startup():
    # 0. Pre-flight
    assert config_valid() and exchange.ping()

    # 1. Load local state
    state = db.load_state()

    # 2. Fetch exchange ground truth
    ex_orders  = await exchange.fetch_open_orders()
    ex_balance = await exchange.fetch_balance()
    ex_fills   = await exchange.fetch_my_trades(since=state.last_fill_ts)

    # 3. Reconcile orders
    orphans = set(ex_orders) - set(state.pending_orders)
    ghosts  = set(state.pending_orders) - set(ex_orders)

    # 4. Process missing fills
    for fill in set(ex_fills) - set(state.known_fills):
        ledger.apply_fill(fill)

    # 5. Reconcile positions
    for pos in state.open_positions:
        verify_against_exchange(pos)

    # 6. Reconcile balance
    drift = abs(ex_balance - state.balance)
    if drift > HALT_THRESHOLD:
        await alert_critical(f"Balance drift: {drift}")
        return set_state(HALTED)

    # 7. Resolve unknowns → decide mode
    mode = determine_startup_mode(orphans, ghosts, drift)

    # 8. Start PAUSED → auto-resume or wait
    set_state(PAUSED)
    await asyncio.sleep(STARTUP_PAUSE_SEC)
    if mode == 'CLEAN':
        set_state(ACTIVE)
    else:
        await wait_human_approval()
```

> **กฎเหล็ก:** Never skip reconciliation — even for 30-second restarts

### State Persistence — ต้อง Save อะไร

```python
# MUST PERSIST (หายแล้ว recover ไม่ได้)
MUST_PERSIST = {
    'open_positions',           # entry price, qty, stop, strategy
    'pending_orders',           # client_order_id, intent, size
    'last_fill_timestamp',      # สำคัญที่สุด — fetch fills since downtime
    'circuit_breaker_state',    # daily_loss, drawdown, cooldown_until
    'bot_state',                # ACTIVE/PAUSED/HALTED
    'peak_equity',              # max drawdown calculation
}

# RECONSTRUCT FROM EXCHANGE (ไม่ต้อง persist)
RECONSTRUCT = ['current_balance', 'open_orders_detail', 'recent_fills']

# COMPUTE ON-DEMAND (ไม่ต้อง persist)
COMPUTE = ['unrealized_pnl', 'equity', 'current_drawdown']
```

### Graceful Shutdown (SIGTERM → action ใน 30 วินาที)

```python
async def handle_shutdown(sig):
    set_shutdown_flag()
    await drain_operations(timeout=10)      # รอ ops ที่กำลังทำ
    await apply_shutdown_policy()           # cancel / keep stops
    save_state_final()                      # บันทึก last_fill_ts
    await alert('Bot shutdown: reason=...')
```

#### Shutdown Policies
```
CANCEL_ALL:   ยกเลิกทุก order (conservative)
KEEP_STOPS:   ยกเลิก entry, คง stop/TP ← แนะนำ
KEEP_ALL:     ทิ้งทุก order ไว้ (อันตราย)
```

### Recovery Scenarios

| Scenario | Action |
|----------|--------|
| Clean restart | auto-resume หลัง PAUSED 5 วินาที |
| Crash restart | PAUSED 30 วินาที + alert + check fills ระหว่าง downtime |
| WS disconnect | reconnect → fetch fills since disconnect → resume |
| Balance drift < 0.1% | log + adjust |
| Balance drift 0.1-1% | alert + adjust |
| Balance drift > 1% | HALTED รอ human |
| Orphan order | cancel ถ้าไม่รู้ที่มา + alert critical |

### Periodic Reconciliation

```
ทุก 15-30 วินาที:  WS heartbeat, stuck orders, unrealized P&L update
ทุก 60-120 วินาที: fetch open orders, balance drift check
ทุก 5-10 นาที:    full balance reconcile, orphan position check
ทุกวัน EOD:        reset daily_loss, archive logs, generate report
```

---

## 13. Backtest-Live Unified Design

### หลักการ

```
เปลี่ยนแค่ Broker → ทุกอย่างอื่นเหมือนกันทุก environment
```

```
Data Layer     [ต่างกัน: Historical vs Live WebSocket]
     ↓
Strategy       [เหมือนกัน ✅ — ไม่รู้ว่าอยู่ใน mode ไหน]
     ↓
Risk Manager   [เหมือนกัน ✅]
     ↓
Broker Interface [swap ตาม mode 🔄]
  BacktestBroker | PaperBroker | LiveBroker
     ↓
Portfolio Ledger [เหมือนกัน ✅]
```

### Core Events

```python
@dataclass
class MarketDataEvent:
    timestamp: datetime  # UTC
    symbol:    str
    open: Decimal; high: Decimal; low: Decimal; close: Decimal
    volume:    Decimal
    timeframe: str       # '1m', '1h', '4h'
    is_closed: bool      # ⚠️ ห้าม signal บน candle ที่ยังไม่ปิด

@dataclass
class OrderIntent:
    strategy_id: str
    symbol:      str
    side:        str     # 'BUY' | 'SELL'
    order_type:  str     # 'MARKET' | 'LIMIT' | 'STOP'
    quantity:    Decimal | None  # None = position sizer decides
    limit_price: Decimal | None
    intent_id:   UUID
    created_at:  datetime

@dataclass
class FillEvent:
    order_id:   UUID
    intent_id:  UUID    # link กลับ OrderIntent
    symbol:     str
    side:       str
    quantity:   Decimal  # actual filled
    price:      Decimal  # actual fill price
    fee:        Decimal
    filled_at:  datetime
    is_partial: bool
```

### Broker Interface (Abstract)

```python
class BrokerInterface(ABC):
    @abstractmethod
    async def submit_order(self, intent: OrderIntent) -> str: ...
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool: ...
    @abstractmethod
    async def get_order_status(self, order_id: str) -> OrderStatus: ...
    @abstractmethod
    async def get_balance(self) -> Balance: ...
    @abstractmethod
    async def get_open_orders(self) -> List[Order]: ...

# เปลี่ยนแค่บรรทัดนี้
broker = BacktestBroker(data=historical_data)
# หรือ
broker = PaperBroker(exchange=live_exchange)
# หรือ
broker = LiveBroker(exchange=live_exchange)
```

### Fill Models (จาก naive → realistic)

| Model | Description | แนะนำ? |
|-------|-------------|--------|
| Instant fill at signal | fill ทันทีที่ราคาถึง | ❌ ห้ามใช้ |
| Next candle open | fill ที่ open ของ candle ถัดไป | ⚠️ Basic |
| Conservative limit fill | fill เมื่อ low/high ผ่าน limit อย่างชัดเจน | ✅ Better |
| Realistic + slippage + volume | scale slippage ตาม order size/volume | ✅ Recommended |
| Tick-level / order book | จำลอง queue position | 🔬 Advanced |

```python
# Conservative Market Order Fill
def fill_market_buy(next_candle, order_qty, candle_vol, base_slippage):
    impact = order_qty / candle_vol * impact_factor
    fill_price = next_candle.open * (1 + base_slippage + impact)
    fee = fill_price * order_qty * taker_fee_rate
    return fill_price, fee

# Conservative Limit Order Fill
def fill_limit_buy(next_candle, limit_price, buffer=0.001):
    filled = next_candle.low < limit_price * (1 - buffer)
    return limit_price if filled else None
```

### 2 Deployment Gaps (FinRL-X Research 2025)

```
Gap 1: Backtest → Paper Trading
  ปัญหา: instant fills, no market impact, no order book, data feed inconsistency
  Fix:   realistic fill model + slippage + warmup + next-candle + benchmark

Gap 2: Paper → Live Trading
  ปัญหา: real fill uncertainty, latency, partial fills, infrastructure fragility
  Fix:   reconciliation + retry + kill switch + small position start + slippage calibration
```

### Lookahead Bias Prevention (Structural)

```python
# Event-driven ทำให้ lookahead เป็นไปไม่ได้โดยโครงสร้าง
# แต่ต้องระวัง:
# 1. ใช้ candle.is_closed = True เท่านั้น
# 2. shift(1) ทุก indicator
# 3. execute บน candle ถัดไปเสมอ
# 4. indicator warmup = max(all_lookback_periods)
```

### Frameworks ที่ทำ Unified Design แล้ว

```
Freqtrade:      dry_run=true/false เปลี่ยน mode เดียว — crypto-first, production-proven
Jesse:          unified codebase ที่ชัดเจนที่สุด — simple API
NautilusTrader: Rust-based, "backtest-live code parity" — high performance
Hummingbot:     V2 framework — เน้น market making + multi-venue
```

### Calibration Target

```
Live Sharpe ≥ 60% ของ Backtest Sharpe → implementation ดี
Live Slippage ≈ Backtest Slippage ± 50% → fill model ดี
Live Win Rate ≈ Backtest Win Rate ± 10% → no hidden bias
```

---

## 14. Validation Methodology & Bias Controls

### Full Pipeline (8 Steps — ห้ามข้าม)

```
1. Unit/Logic Validation  → ตรวจ indicator, signal logic, execution ก่อนแตะ data
2. Bias Checks            → lookahead, data leakage, warmup period, timestamps
3. Backtest (In-sample)   → idea validation เท่านั้น — ยังสรุปอะไรไม่ได้
4. Robustness Checks      → Monte Carlo, parameter sensitivity, walk-forward
5. Multiple Testing Controls → DSR, PBO/CSCV ถ้าลอง >5 variants
6. Generalization/Selection Bias → survivorship bias, หลาย period, หลาย assets
7. Paper Trading          → validate execution code + latency + reconciliation
8. Live Gating            → security gate ครบ, small capital, drift detection เริ่ม
```

> **กฎ:** ถ้า fail ที่ขั้นไหน กลับไปแก้ขั้นนั้น ไม่ใช่ข้ามต่อไป

### Data Snooping & Multiple Testing Controls

**ปัญหา:** ลอง 100 variants แล้วเลือกตัวที่ดูดีที่สุด = guarantee เจอ winner โดยบังเอิญ

```python
# Deflated Sharpe Ratio (DSR) — Bailey & López de Prado 2014
# แก้ Sharpe สำหรับ:
#   - จำนวน trials ที่ลอง (ยิ่งลองเยอะ ยิ่ง penalize)
#   - non-normality of returns (fat tails, skew)
#   - sample length
#   - variance ของ Sharpe ระหว่าง trials
#
# DSR > 0  → น่าจะรอดจาก selection bias
# DSR ≤ 0  → likely data snooping artifact

# Probability of Backtest Overfitting (PBO) via CSCV
# PBO < 20%  → robust
# PBO 20-50% → fragile
# PBO > 50%  → likely overfit
```

**Controls ที่ต้องทำ:**

```
[ ] Pre-register hypothesis ก่อนดู data (เขียน logic ก่อน test)
[ ] Research log ทุก variant ที่ลอง — ไม่ใช่แค่ตัวที่ดี
[ ] Parameter budget: กำหนดจำนวน combinations สูงสุดก่อน optimize
[ ] Locked holdout set: แยกออกตั้งแต่แรก ใช้แค่ครั้งเดียวตอน final validation
[ ] DSR: คำนวณถ้าลอง > 5 variants
[ ] CSCV/PBO: คำนวณสำหรับ top 3 strategy candidates เท่านั้น
```

**Red flags:**
```
กำไรมาจาก 1-2 trades
Sharpe ดีเฉพาะ parameter แคบมาก
เปลี่ยน parameter นิดเดียวผลพัง
ชนะเฉพาะ bull market
trade count < 30
sensitivity heatmap มีแค่เกาะเดียวที่ดี
```

### Survivorship Bias (อันตรายพิเศษในตลาด Crypto)

**งานวิจัย:** 'buy top-20 altcoins 2020-2021' ด้วย today's top-20 → +2,800% แต่ด้วย historical top-20 → +680% ต่างกัน 4× เพราะไม่รวม LUNA, FTT, altcoins ที่ตายแล้ว

```python
# ❌ Wrong: ใช้ coins ที่ active วันนี้ย้อนหลังไป test
universe = exchange.fetch_tickers()  # only current coins

# ✅ Correct: Point-in-time universe
def get_universe_at_time(t: datetime) -> List[str]:
    return [coin for coin in historical_symbols
            if coin.listed_at <= t <= (coin.delisted_at or now)]
```

**Policy:**
```
V1:          BTC/ETH เท่านั้น — ไม่มี survivorship bias เลย
ถ้า altcoins: ต้องใช้ point-in-time universe + historical liquidity filter
              (ไม่ใช่ volume ปัจจุบัน)
```

### Monte Carlo — Metrics ที่สำคัญ

```python
# วิธีที่เหมาะกับ V1 (เรียงจากง่ายไปยาก)
# 1. Trade sequence shuffle
# 2. Bootstrap with replacement
# 3. Fee/slippage stress (×1.5, ×2.0, ×3.0)
# 4. Missed fill / delayed entry

# Metrics ที่ต้องดู
metrics = {
    'median_final_equity':      ...,   # central estimate
    '5th_pct_final_equity':     ...,   # near worst case — ต้อง > 0
    '95th_pct_max_drawdown':    ...,   # near worst drawdown
    'risk_of_ruin':             ...,   # P(equity < 10% initial) — ต้อง < 5%
    'prob_lose_money':          ...,   # P(final < initial)
    'worst_losing_streak_distr':...,   # เทียบกับ circuit breaker ที่ตั้งไว้
}
```

> **กฎ:** Monte Carlo mandatory สำหรับทุก strategy candidate ก่อน paper trade

### Validation Checklist ก่อน Live

```
Pre-Registration:
  [ ] เขียน hypothesis จาก logic ก่อนดู data
  [ ] กำหนด parameter budget สูงสุด
  [ ] ล็อก holdout set ออก

Bias Checks:
  [ ] ไม่มี lookahead (unit test ก่อน)
  [ ] warmup period ครบ
  [ ] next-candle execution
  [ ] point-in-time universe (ถ้า altcoins)

Backtest Quality:
  [ ] realistic fee + slippage (stress test)
  [ ] benchmark vs buy-and-hold BTC
  [ ] performance by regime (regime_performance.csv)
  [ ] out-of-sample ≥ 20% ของ data

Robustness:
  [ ] Monte Carlo: 5th pct equity > 0
  [ ] fee breakeven > 2× current fee
  [ ] parameter sensitivity ±20% ยังกำไร
  [ ] DSR > 0 (ถ้าลอง > 5 variants)
  [ ] PBO < 30% สำหรับ top candidates

Drift Baseline:
  [ ] บันทึก baseline stats จาก out-of-sample
  [ ] ตั้ง drift thresholds ก่อน live
  [ ] ออกแบบ monitoring dashboard

Live Gate (Hard gate — ต้องครบทุกข้อ):
  [ ] Subaccount แยก
  [ ] IP whitelist
  [ ] Secret scanning ผ่าน (gitleaks/git-secrets)
  [ ] Rollback procedure พร้อม
  → ขาดข้อใดข้อหนึ่ง = ยังไม่เปิด live
```

---

## 15. Drift Detection & Action Tiers

### 4 Drift Types — Response ต่างกัน

ต้องแยก drift types เพราะ response ต่างกันโดยสิ้นเชิง — diagnose ผิดทำให้แก้ผิดทิศทาง

**ลำดับการตรวจ:** Data → Execution → Performance → Concept

| Drift Type | คำถาม | Detection | Response หลัก |
|-----------|--------|-----------|--------------|
| **Data Drift** | data pipeline มีปัญหาไหม? | ws_lag > 5s, reconnects > 3/hr, spread > 2× baseline | Stale guard → REDUCE_ONLY |
| **Execution Drift** | fill/slippage เป็นอย่างที่คาดไหม? | fill_rate < 80%, slippage > 2× backtest, latency p95 > 500ms | Pause entries, fix code |
| **Concept Drift** | ตลาดเปลี่ยน structure ไหม? | regime distribution เปลี่ยน, strategy แพ้ใน regime ที่ควรชนะ | รัน regime_performance, retune |
| **Performance Drift** | ผลลัพธ์โดยรวมเสื่อมลงไหม? | rolling Sharpe ลด >30%, PF < 1.0 ต่อเนื่อง | ตาม Action Tiers ด้านล่าง |

### Action Tiers สำหรับ Performance Drift

```
📋 Watch (Log only)
   Trigger: Sharpe ลด 15-20% หรือ PF 1.1-1.3 หรือ win rate ลด 5-8pp
   Action:  log + tag anomaly, monitor ต่อ 1-2 สัปดาห์

⚠️ Warning (Size down)
   Trigger: Sharpe ลด 20-30% หรือ PF 1.0-1.1 หรือ win rate ลด 8-12pp
   Action:  ลด position size 50%, alert, rerun regime_performance
   Timeline: แก้ภายใน 1 สัปดาห์ ไม่งั้น upgrade tier

🔴 Critical (Pause entries)
   Trigger: Sharpe ลด >30% หรือ PF < 1.0 ต่อเนื่อง 20+ trades หรือ win rate ลด >12pp
   Action:  REDUCE_ONLY state, alert critical, rerun walk-forward
   Timeline: แก้หรือ Retire ภายใน 2 สัปดาห์

🚨 Emergency (Halt)
   Trigger: live drawdown > backtest p95 หรือ daily loss > 2× limit หรือ 5+ losing streak > worst backtest
   Action:  HALTED state, cancel all, human intervention ทันที
   Timeline: resume เมื่อ root cause ชัด

💀 Retire (Remove strategy)
   Trigger: drift ไม่หาย 4+ สัปดาห์ หรือ edge หายจริง (walk-forward ยืนยัน)
   Action:  หยุด permanent, write post-mortem, ห้าม revive โดยไม่มีข้อมูลใหม่
```

> **กฎการตัดสินใจ:** กำหนด tier criteria **ก่อน live** ขณะคิดได้ปกติ ไม่ใช่ตอนกำลัง lose money

### Drift Detection System

```python
class DriftMonitor:
    def __init__(self, baseline: dict, window: int = 30):
        self.baseline = baseline
        self.history  = deque(maxlen=window)  # trades หรือ days

    def classify_tier(self, metrics: dict) -> str:
        b = self.baseline
        # Emergency ก่อนเสมอ
        if metrics['max_dd'] > b['backtest_p95_dd']:
            return 'EMERGENCY'
        if metrics['sharpe'] < b['sharpe'] * 0.70:
            return 'CRITICAL'
        if metrics['pf'] < 1.0 and len(self.history) > 20:
            return 'CRITICAL'
        if metrics['sharpe'] < b['sharpe'] * 0.80:
            return 'WARNING'
        if metrics['fill_rate'] < b['fill_rate'] * 0.80:
            return 'WARNING'  # Execution drift
        return 'WATCH'
```

### Baseline Definition & Cadence

```
Baseline period: First 90 วันของ live trading (ไม่ใช่ paper)
  baseline_sharpe    = mean(rolling_sharpe, first 90 days)
  baseline_pf        = mean(profit_factor, first 90 days)
  baseline_fill_rate = mean(fill_rate, first 90 days)
  backtest_p95_dd    = percentile(Monte Carlo drawdowns, 95)

Cadence:
  Real-time:    Emergency checks ทุก 60 วินาที
  EOD:          Rolling metrics update + alert routing
  Weekly:       Human review: live vs paper/backtest baseline
  Monthly:      Rerun walk-forward บน recent data
```

### Drift Decision Tree (Quick Reference)

```
เจอ anomaly → ตรวจตามลำดับนี้:

1. Data Drift?
   ws_lag > 5s OR reconnects > 3/hr OR spread > 2× baseline?
   YES → Stale guard, alert, REDUCE_ONLY ถ้า > 5 min

2. Execution Drift?
   fill_rate < 80% OR slippage > 2× baseline?
   YES → Pause entries, inspect execution code

3. Performance Drift?
   drawdown > backtest p95? → EMERGENCY HALT
   Sharpe < 70% baseline?   → CRITICAL: pause entries
   Sharpe < 80% baseline?   → WARNING: ลด size 50%

4. Concept Drift?
   regime distribution เปลี่ยนมาก?
   YES → รัน regime_performance analysis

5. Retire?
   Warning/Critical > 4 สัปดาห์? walk-forward ยืนยัน edge หาย?
   YES → RETIRE: stop permanent, write post-mortem
```

---

## 16. Framework Selection & Spikes

### เปรียบเทียบ 5 Frameworks — Best Role

| Framework | Best Role | Strength | Limitation | เหมาะกับ |
|-----------|-----------|----------|------------|---------|
| **Freqtrade** | MVP Runner / Benchmark | crypto-native, CCXT, dry-run, Telegram/WebUI, hyperopt, 39.9k stars | ติด Freqtrade architecture | V1 production, benchmark |
| **VectorBT** | Research Lab | parameter sweep เร็วสุด (NumPy), Monte Carlo ง่าย, portfolio analysis | ไม่ใช่ live engine, execution realism ต่ำ | Research phase, robustness check |
| **NautilusTrader** | Advanced Production | Rust core, nanosecond resolution, identical backtest↔live code, multi-venue | learning curve สูงมาก, paradigm shift, API ยังเปลี่ยน | Production เมื่อ validate แล้ว, HFT-adjacent |
| **Backtrader** | Learning/Legacy | mature, docs เยอะ, event-driven concept | development หยุดแล้ว, crypto live ไม่ดี | เรียน concept เท่านั้น |
| **Custom Engine** | Full Control | ควบคุมทุกจุด, ไม่ติดข้อจำกัด framework | build นาน, เสี่ยง infrastructure bug, maintain เอง | เมื่อรู้ชัดว่า framework ทำไม่ได้ |

> **2026 consensus:** VectorBT (research) → Freqtrade (validate) → NautilusTrader (production) หรือ Custom ถ้าจำเป็น

### Spike A-D — ทดสอบก่อนตัดสินใจ

ใช้ **strategy เดียวกัน** (EMA Trend บน BTC/USDT 1h), **data เดียวกัน** (2022-2024) เพื่อเปรียบผลได้ตรงๆ

```
Spike A: Freqtrade (2-3 วัน)
  Tasks: install + config → implement EMA strategy → backtest 2022-2024
         → dry-run 1 สัปดาห์ → ทดสอบ Telegram alerts
  Output: Architecture ของ Freqtrade จำกัดอะไรบ้าง? ขยาย custom logic ได้แค่ไหน?

Spike B: VectorBT (1-2 วัน)
  Tasks: implement strategy เดิม → sweep EMA period 1000 combinations
         → รัน Monte Carlo 1000 paths → เปรียบ result กับ Spike A
  Output: Result ต่างจาก Freqtrade เท่าไหร่? Fill model ส่งผลแค่ไหน?

Spike C: Custom Mini Engine (3-5 วัน)
  Tasks: สร้าง MarketDataEvent, OrderIntent, FillEvent
         → BacktestBroker (next-candle + fee + slippage)
         → RiskManager + Portfolio Ledger
         → รัน strategy เดิม เปรียบผล
  Output: ใช้เวลานานแค่ไหน? มี infrastructure bug ไหม? คุ้มกับ effort?

Spike D: NautilusTrader (3-5 วัน)
  Tasks: setup Rust build + Python → implement strategy ใน Actor pattern
         → รัน backtest เดิม → เปรียบ result
  Output: Learning curve สูงแค่ไหน? Backtest-live parity ดีกว่า Freqtrade จริงไหม?
```

> **รวมเวลา:** ~2 สัปดาห์ — ดีกว่าลงทุน 3 เดือนกับ approach ผิด

### Decision Framework หลังทำ Spike

```
5 คำถามหลัง Spike:

1. Freqtrade ทำ custom logic ที่ต้องการได้ไหม?
   YES → เริ่ม production บน Freqtrade

2. Custom engine (Spike C) ใช้เวลา < 2 สัปดาห์สำหรับ MVP ไหม?
   YES → สร้าง custom engine

3. NautilusTrader learning curve ยอมรับได้ (< 2 สัปดาห์ setup)?
   YES → ใช้ NautilusTrader เป็น production engine

4. Result ของ Spike A/B/C/D ต่างกันมากไหม?
   NO  → fill model ไม่ critical → Freqtrade พอ
   YES → fill model สำคัญ → NautilusTrader หรือ custom

5. ต้องการ latency < 10ms ไหม?
   YES → NautilusTrader หรือ Rust custom

ตัดสินใจ:
  Freqtrade wins if: crypto-native, deploy fast, team เล็ก, strategy ไม่ต้องการ tick-level
  NautilusTrader wins if: execution realism สูง, multi-venue, team พร้อม invest learning
  Custom wins if: มี specific requirement ที่ framework ทำไม่ได้ และ Spike C ไม่ยากเกิน
```

### NautilusTrader Key Facts (สำหรับ Spike D)

```python
# backtest และ live ใช้ strategy code เดียวกัน
strategy = MyStrategy(config=config)

# Backtest
backtest_engine.add_strategy(strategy)
backtest_engine.run()

# Live — code เดิมทุกบรรทัด ไม่ต้องแก้อะไร
trading_node.add_strategy(strategy)
trading_node.start()
```

- Core: Rust + Python API (PyO3)
- Learning curve จริง: build complexity, paradigm shift จาก vectorized, high-fidelity data
- API ยังเปลี่ยนบ่อย (breaking changes between releases)
- ไม่มี UI dashboard หรือ built-in AI/ML tooling — focused on core engine

---


## 17. Multi-metric Calibration Gates

### ทำไมต้องมีหลาย Gates

Calibration ที่ดีต้องเป็น 3 gates ไม่ใช่ตัวเลขเดียว — แต่ละ gate ผ่าน environment หนึ่งไปอีก environment และวัด metric คนละกลุ่ม:

```
🧪 Backtest → 📄 Paper (Gate 1) → 💰 Small Live 5-10% (Gate 2) → 🚀 Full Live (Gate 3)
```

> **กฎ:** Calibration ≥ 60% Sharpe เป็นแค่ heuristic หนึ่งใน multi-metric system ไม่ใช่ hard pass/fail เดี่ยว

### Gate 1 — Backtest ไป Paper Trading

| Metric | Pass | Watch | Fail |
|--------|------|-------|------|
| Signal match rate | ≥ 90% ของ backtest signals | 80-90% | < 80% |
| OOS Sharpe vs in-sample | ≥ 60% | 40-60% | < 40% |
| Monte Carlo 5th pct equity | > 0 (บวก) | ใกล้ 0 | < 0 |
| Risk of ruin (MC) | < 5% | 5-15% | > 15% |
| Fee model error | < 5% | 5-10% | > 10% |
| Paper slippage vs modeled | 0.5x-2.0x | 2x-3x | > 3x |
| Parameter sensitivity ±20% | Sharpe เปลี่ยน < 30% | 30-50% | > 50% |
| Backtest DD vs MC p95 | backtest < p95 | backtest ≈ p95 | backtest > p95 |

**ขั้นต่ำก่อนประเมิน:** OOS อย่างน้อย 30 trades หรือ 3 เดือน

### Gate 2 — Paper Trading ไป Small Live (5-10%)

| Metric | Pass | Watch | Fail |
|--------|------|-------|------|
| Paper Sharpe vs backtest | ≥ 50% (Good: ≥ 70%) | 30-50% | < 30% |
| Fill rate | ≥ 90% | 80-90% | < 80% |
| Slippage actual vs modeled | 0.5x-2.0x | 2x-3x | > 3x |
| Trade frequency vs expected | ±20% | ±20-40% | > ±40% |
| Order reject rate | < 1% | 1-3% | > 3% |
| Unexpected open position | = 0 (**HARD gate**) | — | > 0 |
| Critical ledger mismatch | = 0 (**HARD gate**) | — | > 0 |
| Paper DD vs MC p95 | ≤ p95 | นิดหน่อย | เกิน p95 มาก |
| Win rate vs backtest | ±10pp | ±10-15pp | > ±15pp |

**ขั้นต่ำก่อนประเมิน:** Paper trading 60-90 วัน หรือ minimum 50 trades

### Gate 3 — Small Live ไป Full Allocation

| Metric | Pass | Watch | Fail |
|--------|------|-------|------|
| Live Sharpe vs paper | ≥ 70% (Acceptable: 50-70%) | 30-50% | < 30% |
| Live slippage vs paper | ≤ 2x | 2x-3x | > 3x |
| Live fee error vs modeled | < 5% | 5-10% | > 10% |
| Order reject rate (live) | < 1-2% | 2-5% | > 5% |
| Unexpected open position | = 0 (**HARD gate**) | — | > 0 |
| Critical ledger mismatch | = 0 (**HARD gate**) | — | > 0 |
| Live DD vs expected p95 | ≤ p95 | นิดหน่อย | เกิน p95 |
| Drift tier (4-week window) | ≤ Watch | Warning | Critical+ |
| Capital scaling consistency | P&L per unit ≈ paper ±20% | ±20-30% | > ±30% |

**ขั้นต่ำก่อนประเมิน:** 60 วัน Small Live หรือ minimum 50 trades

### Capital Scaling Protocol

```
5%  → Paper ผ่าน Gate 2 | รัน 30 วัน | เฝ้าทุกวัน
10% → 5% stage ผ่าน 30 วัน | Drift ≤ Watch | metrics consistent
25% → Gate 3 preliminary ผ่าน | 60 วันรวม | P&L per unit consistent
50% → Gate 3 เต็ม | 30 วันที่ 25% | ไม่มี ledger mismatch
100%→ 50% stage ผ่าน 30 วัน | drift stable | no warnings
```

> **ถ้า Drift tier ขึ้นเป็น Critical:** roll back capital ลง 1 ขั้น อย่ารอ Emergency

### Calibration Tiers (Sharpe Retention)

```
Good:         live/paper Sharpe ≥ 70% ของ conservative backtest
Acceptable:   50-70%
Warning:      30-50% → ลด size, review
No-go/Pause:  < 30% หรือ DD เกิน backtest p95
```

> **หมายเหตุ:** 60% เป็น heuristic ไม่ใช่ hard rule — conservative backtest อาจ live ≥ 70%, optimistic backtest อาจ 60% ยังแย่อยู่

### Gate Implementation

```python
class CalibrationGate:
    HARD_GATES = [
        'unexpected_position == 0',
        'critical_ledger_mismatch == 0',
        'drift_tier not in [CRITICAL, EMERGENCY]',
    ]
    SOFT_GATES_MIN_PASS = 4  # จาก 5 soft gates

    def evaluate(self) -> GateResult:
        if self.trade_count < self.min_trades:
            return GateResult(INSUFFICIENT_DATA)
        hard_fails = [c for c in checks if c.is_hard and c.failed]
        soft_fails  = [c for c in checks if not c.is_hard and c.failed]
        if hard_fails:            return GateResult(FAIL_HARD, hard_fails)
        if len(soft_fails) > 2:   return GateResult(FAIL_SOFT, soft_fails)
        return GateResult(PASS)
```

---

## 18. Jesse Framework Evaluation

### ภาพรวม

Jesse เป็น crypto-first Python framework ที่มี Monte Carlo built-in และ strategy syntax ที่สะอาด แต่มี pricing model ที่ต้องเข้าใจก่อนตัดสินใจ

### Feature Tiers

| Feature | ฟรี (MIT) | Paid (Lifetime) |
|---------|-----------|-----------------|
| Backtest engine | ✅ สมบูรณ์ | — |
| Monte Carlo (2 modes) | ✅ dashboard | — |
| Optimization (GA) | ✅ | — |
| ML pipeline built-in | ✅ | — |
| JesseGPT AI assistant | ✅ | — |
| Live trading | — | ✅ Binance/Bybit/Coinbase/Bitget |
| Paper trading (live data) | — | ✅ อยู่ใน live plugin |

### Jesse vs Freqtrade vs Custom

| Dimension | Jesse | Freqtrade | Custom |
|-----------|-------|-----------|--------|
| Monte Carlo built-in | 🟢 2 modes, dashboard | 🔴 ทำเอง | 🔴 ทำเอง |
| Strategy syntax | 🟢 ง่ายมาก | 🟡 ปานกลาง | ขึ้นกับ design |
| Live trading cost | 🟡 Paid plugin | 🟢 ฟรี (MIT) | 🟢 ฟรี |
| Exchange coverage | 🟡 4 exchanges | 🟢 CCXT 100+ | ขึ้นกับ implementation |
| Community size | 🟡 ~5k stars | 🟢 ~39.9k stars | 🔴 ไม่มี |
| Architecture control | 🟡 ติดกรอบ | 🟡 ติดกรอบ | 🟢 เต็ม |
| Single maintainer risk | ⚠️ ใช่ | 🟢 community | 🟢 ของเราเอง |

### Jesse Monte Carlo — ทำได้และทำไม่ได้

```
✅ Jesse MC ทำได้:
  - Trade-order shuffling (ทดสอบว่า timing สำคัญแค่ไหน)
  - Candles-based simulation (market noise robustness)
  - Worst 5% drawdown
  - Median / best 5% equity

⚠️ Jesse MC ทำไม่ได้ (ต้องทำเพิ่มเอง):
  - Fee/slippage stress test
  - Risk of ruin P(equity < threshold)
  - DSR / PBO calculation
```

### Spike Plan สำหรับ Jesse

```
Step 1 (ฟรี, 0.5-1 วัน): Backtest spike
  - implement EMA Trend เดียวกับ Spike A
  - เปรียบ Sharpe/DD กับ Freqtrade
  - ประเมิน strategy syntax complexity

Step 2 (ฟรี, 0.5-1 วัน): Monte Carlo spike
  - รัน MC ทั้ง 2 modes
  - เปรียบกับ VectorBT MC
  - ประเมิน UX และ workflow time

Step 3 (ฟรี, 0.5 วัน): Optimization spike
  - รัน genetic algorithm optimization
  - ประเมิน overfitting risk

Step 4 (Paid, optional): Live plugin evaluation
  - paper trading behavior
  - reconciliation depth
  - exchange connector quality
```

### Decision Framework

```
Jesse wins if:
  Monte Carlo workflow เร็วกว่า VectorBT ชัดเจน
  Strategy iteration เร็วกว่า 2×
  ยอมจ่าย paid plugin

Freqtrade wins if:
  Jesse MC ไม่ต่างจาก custom MC มาก
  ต้องการ exchange coverage กว้าง (CCXT 100+)
  Community support สำคัญ

Hybrid (แนะนำ):
  Jesse free tier → research + backtest + Monte Carlo
  Freqtrade → live production
  → ได้ประโยชน์จากทั้งสอง ไม่ต้องเลือก
```

---

## 19. Dead Man's Switch (DMS)

### หลักการ

DMS คือ exchange-side mechanism ที่ cancel orders อัตโนมัติเมื่อ bot หยุดส่ง heartbeat — เป็น safety net ระดับ network ที่ software kill switch ทำไม่ได้ถ้า process crash

```
Bot ส่ง heartbeat ทุก 30s พร้อม countdown_time=120s
↓
ถ้าหมด 120s โดยไม่มี heartbeat ใหม่
↓
Exchange cancel all orders อัตโนมัติ
↓
⚠️ Cancel orders เท่านั้น — ไม่ close positions
```

### Exchange Support Matrix

| Exchange | Spot | Futures/Perps | Notes |
|----------|------|---------------|-------|
| **Binance** | ❌ ไม่มี DMS | ✅ countdownCancelAll (per-symbol, ms) | Spot = ไม่มี DMS |
| **Bybit** | ⚠️ ต้องตรวจ V5 | ⚠️ ต้องตรวจ | ยังไม่ confirmed |
| **Kraken** | ✅ CancelAllOrdersAfter (global, seconds) | ✅ global | ดีที่สุด — global ไม่ต้อง per-symbol |
| **OKX** | ⚠️ expTime per-order เท่านั้น | ⚠️ expTime | ไม่ใช่ global DMS |
| **BitMEX** | N/A | ✅ cancelAllAfter (ms) | — |
| **Coinbase** | ❌ ไม่มี | ❌ ไม่มี | — |

> **สำคัญมาก:** Binance Spot (V1 ของเรา) ไม่มี DMS → ต้อง implement software watchdog แทน

### Gotchas ที่ต้องรู้

```
1. DMS ≠ Position Close
   cancel orders ≠ close positions
   ถ้ามี BTC long position หลัง DMS trigger → ยังถือ BTC อยู่

2. Binance Futures: per-symbol ไม่ใช่ global
   ต้องส่ง heartbeat แยกต่างหากสำหรับแต่ละ symbol ที่ trade

3. DMS trigger ≠ bot หยุด
   bot ที่ recover กลับมาต้อง reconcile DMS state ด้วย

4. Deactivate ก่อน graceful shutdown
   ส่ง timeout=0 เพื่อ disable DMS ก่อน planned restart
   ไม่งั้น DMS trigger ระหว่าง restarting
```

### Implementation Pattern

```python
# Exchange DMS (ถ้า exchange รองรับ เช่น Binance Futures)
class ExchangeDMS:
    async def start(self):
        await exchange.cancel_all_orders_after(countdown_ms)
        asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        while self.active:
            await exchange.cancel_all_orders_after(countdown_ms)
            await asyncio.sleep(heartbeat_interval_s)

    async def deactivate(self):
        await exchange.cancel_all_orders_after(0)  # timeout=0 = disable


# Software DMS (สำหรับ Binance Spot หรือ exchange ที่ไม่รองรับ)
class SoftwareDMS:
    async def update_heartbeat(self):
        self.last_heartbeat = time.time()

    async def watchdog_loop(self):
        while self.active:
            age = time.time() - self.last_heartbeat
            if age > self.cancel_after_s:
                await self.emergency_cancel_all()
                break
            await asyncio.sleep(self.check_interval_s)
```

### Settings ที่แนะนำ

```
countdown_time:      120s (3-5× heartbeat interval)
heartbeat_interval:  30s
heartbeat task:      asyncio task แยกจาก trading loop
Binance Futures:     call per active symbol
Kraken:              1 call ครอบคลุมทั้งหมด
```

### Decision สำหรับโปรเจคนี้

```
V1 (Binance Spot):
  → Software watchdog loop
  → ไม่มี exchange DMS

Future V5 (Binance Futures):
  → Exchange DMS (primary) + Software watchdog (backup)
  → Heartbeat per active symbol ทุก 30s
```

---

## 20. Design Decisions Summary

| หัวข้อ | Decision | เหตุผล |
|--------|---------|--------|
| **Bot Type V1** | Strategy เดียวก่อน (Grid หรือ Trend) | Architecture รองรับ multi แต่ไม่ซับซ้อนเกิน |
| **Strategy V2** | Grid + Trend with regime filter | ครอบคลุม sideways + trending |
| **Regime Detection** | ADX + BBW + EMA + Volume (8 states) → HMM | เริ่มง่าย, upgrade ได้ |
| **Architecture** | Modular Monolith + Pipeline | สมดุล ง่าย + maintainable |
| **Broker Interface** | Abstract + swap ตาม mode | unified design หลัก |
| **Risk per trade** | 0.5-1% (conservative V1) | ป้องกัน blow-up |
| **Stop-loss** | ATR × 2.0 | ปรับตาม volatility |
| **Circuit breaker** | Daily 2% + Peak 10% | conservative V1 |
| **Capital reserve** | 40% reserve | buffer + opportunity |
| **Market type** | Spot only (V1) | futures ทีหลัง |
| **Backtesting** | Freqtrade / Jesse + Walk-forward | crypto-specific unified |
| **Framework V1** | Freqtrade (default) หลังทำ Spike | production-proven, deploy เร็ว |
| **Research tool** | VectorBT | parameter sweep + Monte Carlo เร็วสุด |
| **Advanced engine** | NautilusTrader (หลัง Spike D) | backtest-live parity สูงสุด |
| **Validation** | DSR + Monte Carlo + Walk-forward | mandatory ก่อน paper trade |
| **Survivorship bias** | BTC/ETH เท่านั้น (V1) | ไม่มี bias เลย |
| **Drift detection** | 4 types + Action tiers | diagnose ก่อน act เสมอ |
| **Drift baseline** | First 90 วันของ live | ไม่ใช่ raw backtest stats |
| **Monitoring start** | Structured logs + Telegram (V1) | Prometheus + Grafana ใน V2-3 |
| **Calibration** | Multi-metric gates (3 gates) | ไม่ใช่แค่ Sharpe 60% |
| **Capital scaling** | 5% → 10% → 25% → 50% → 100% | ไม่ all-in หลัง pass gate |
| **Jesse role** | Free tier research + MC spike | Freqtrade สำหรับ live |
| **DMS (V1)** | Software watchdog loop | Binance Spot ไม่มี exchange DMS |
| **DMS (Futures)** | Exchange DMS + software backup | เพิ่มตอน V5 |
| **Fill model** | Next-candle + slippage + taker fee | conservative พอ |
| **Exchange** | Binance (primary) + CCXT | liquidity + unified |
| **Data** | WebSocket (market) + REST (orders) | hybrid |
| **Storage** | Parquet (OHLCV) + SQLite (operational) | efficient + simple |
| **Portfolio Ledger** | Position + Trade + Balance + Reconciler | single source of truth |
| **Reconciliation** | Startup + Post-disconnect + Periodic | never skip |
| **Startup mode** | Always PAUSED first | never trade on bad state |
| **Shutdown policy** | KEEP_STOPS | protective + flexible |
| **Bot states** | 6 states state machine | clear transition rules |
| **Order default** | Limit (maker fee) | ประหยัด |
| **Security key** | Trade-only + IP whitelist + subaccount | defense in depth |
| **Secret storage** | .env → Vault (prod) | simple → secure |
| **Process manager** | systemd (Python) | auto-restart |
| **Container** | Docker + Docker Compose | reproducible |
| **Monitoring** | Prometheus + Grafana + Loki | open source standard |
| **Alerting** | Telegram (critical) + Email (warning) | fast + backup |
| **Remote control** | Telegram commands | /halt /status /positions |
| **VPS** | Hetzner/Vultr ใกล้ exchange | latency + cost |

---

## 21. Version Roadmap

### Version 0: Research & Design (ปัจจุบัน)
- ✅ finalize architecture
- ✅ choose exchange
- ✅ define data models / events / bot states
- ✅ define risk rules
- ✅ define backtest assumptions
- ✅ design Portfolio Ledger
- ✅ design Startup Recovery flow
- ✅ design Unified Broker Interface

### Version 1: Backtest + Paper Core
- OHLCV data downloader (Parquet)
- Feature / Indicator engine
- Regime detector (rule-based, 8 states)
- One strategy (Grid หรือ Trend)
- BacktestBroker + fill model
- Risk manager
- Portfolio Ledger
- Backtest reports (5 output files)
- Startup reconciliation skeleton

### Version 2: Live Paper Trading
- PaperBroker (live price, simulated fill)
- Live market data (WebSocket)
- Telegram alerts + remote commands
- Full startup reconciliation
- Bot state machine (6 states)
- Monitoring (structured logs + basic metrics)

### Version 3: Controlled Live Spot
- LiveBroker (real exchange)
- Strict risk caps (conservative baseline)
- Small capital only
- Kill switch
- Prometheus + Grafana
- Daily summary + performance review

### Version 4: Multi-Strategy / Regime-Aware
- Regime router
- Strategy allocation + risk budget per strategy
- regime_performance.csv analysis
- Capital reserve management

### Version 5: Advanced Execution / Futures / AI Layer
- TWAP / advanced limit execution
- Futures (เฉพาะเมื่อ risk maturity สูงพอ)
- AI analyst layer (ไม่ใช่ execution authority)
- HMM regime detector

---

## 22. กฎสำคัญที่ต้องจำ

### 🔴 กฎเหล็ก (ห้ามฝ่าฝืน)

1. **Strategy ต้องไม่ส่ง order ตรงถึง exchange** — ต้องผ่าน Risk Manager เสมอ
2. **ห้าม enable withdrawal permission บน bot API key เด็ดขาด**
3. **ห้าม hardcode API key ใน code หรือ commit ขึ้น git**
4. **Never assume — always verify with exchange before retry**
5. **Never skip reconciliation — even for 30-second restarts**
6. **เริ่ม PAUSED เสมอ — never trade on unreconciled state**
7. **Home computer ไม่เหมาะกับ live trading** — ใช้ VPS เสมอ
8. **ใช้ Decimal ไม่ใช่ float สำหรับทุกตัวเลขเงิน**
9. **ห้าม generate signal บน candle ที่ยัง is_closed = False**
10. **ห้าม log API key, secret, signature ในทุกกรณี**
11. **ห้ามลอง > 5 strategy variants โดยไม่คำนวณ DSR** — ไม่งั้น selection bias การันตี
12. **ทำ Spike A-D ก่อน commit กับ custom engine** — ไม่ใช่เพราะรู้สึกว่าจะดีกว่า

### 🟡 หลักการสำคัญ

13. **Capital preservation comes first** — drawdown control > return maximization
14. **Crypto correlation สูงมาก** — 5 bot บน 5 coins ≠ diversified จริง
15. **Backtest ส่วนใหญ่โกหก** — model fee×2, slippage×2, latency 200ms
16. **Silence ≠ stability** — ถ้าไม่มี alert อาจหมายถึง missing instrumentation
17. **Alert fatigue ทำให้ ignore ของสำคัญ** — แบ่ง tier ให้ชัดเจน
18. **เมื่อ internal ≠ exchange → เชื่อ exchange เสมอ** แต่ alert ก่อน adjust
19. **AI/ML ควรเป็น analyst layer** — ไม่ใช่ execution authority โดยตรง
20. **Spot only ก่อน** — futures ทีหลังเมื่อ risk maturity สูงพอ
21. **Retry → Market fallback เฉพาะ emergency exit** — ไม่ใช่ default retry ทั่วไป
22. **Limit order เลือกตาม urgency ไม่ใช่ default ตลอด** — บาง signal ต้องการ execution certainty
23. **Drift ต้อง diagnose ก่อน act** — เริ่มจาก Data → Execution → Performance → Concept
24. **Drift baseline จาก live 90 วันแรก** — ไม่ใช่จาก backtest stats ที่ optimistic

### 🟢 Best Practices

25. **เริ่มเล็ก ทดสอบนาน scale ช้า** — paper trade ก่อนเสมอ
26. **IP whitelist + subaccount** — defense in depth ที่ cost ต่ำสุด
27. **VPS ใกล้ exchange datacenter** — latency ต่างกัน 10-50× จาก home
28. **systemd/Docker restart=always** — ไม่มีใครตื่นมาเปิด bot ตี 3
29. **Walk-forward เป็น minimum standard** ก่อน deploy จริง
30. **Structured JSON log ทุก trade** พร้อม regime ณ เวลา entry
31. **ตรวจ strategy health รายเดือน** — strategy drift เกิดช้าๆ แต่ทำลายพอร์ต
32. **Calibrate fill model ด้วย live data** — เทียบ actual slippage กับ backtest หลัง 50 trades
33. **Document ทุก change เปลี่ยนแค่ 1 variable ต่อครั้ง**
34. **Pre-register hypothesis ก่อนดู data** — บังคับ logic-first ไม่ใช่ data-mining
35. **Research log ทุก variant ที่ลอง** — ไม่ใช่แค่ตัวที่ดี ใช้คำนวณ DSR ทีหลัง
36. **V1 BTC/ETH เท่านั้น** — เพิ่ม altcoins ทีหลังพร้อม point-in-time universe
37. **Monte Carlo mandatory** ก่อน paper trade — ดู 5th pct equity และ risk of ruin
38. **Retire strategy ที่ drift ไม่หาย 4 สัปดาห์** — อย่าถือเพราะ sunk cost fallacy
39. **เมื่อ in doubt → PAUSED + alert → human decides**
40. **Gate ทุกข้อต้องผ่าน ไม่ใช่บางตัว** — Hard gates (unexpected position, ledger mismatch) = zero tolerance
41. **Capital scaling ทีละขั้น** — อย่า all-in หลังผ่าน gate เดียว scale 5% → 10% → 25% → 50% → 100%
42. **DMS ≠ Position close** — cancel orders ≠ close positions อย่า design ว่า DMS คือ emergency exit
43. **Deactivate DMS ก่อน graceful shutdown** — ไม่งั้น DMS trigger ระหว่าง planned restart
44. **Jesse free tier ก่อน** — ทำ Spike 1-3 (ฟรี) ก่อนตัดสินใจซื้อ live plugin

---

*Knowledge base v4 — อัปเดตเพิ่ม Multi-metric Calibration Gates (3 gates + capital scaling protocol), Jesse Framework Evaluation (spike plan + hybrid decision), Dead Man's Switch (exchange matrix + software watchdog pattern) จาก Codex v3 research*
