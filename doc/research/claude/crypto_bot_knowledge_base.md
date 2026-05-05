# Crypto Trading Bot — Knowledge Base

> องค์ความรู้แบบแยกหมวดหมู่ พร้อม design decisions และ recommended stack สำหรับการออกแบบ bot จริง

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
11. [Design Decisions Summary](#11-design-decisions-summary)
12. [กฎสำคัญที่ต้องจำ](#12-กฎสำคัญที่ต้องจำ)

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

### แนวทาง Multi-strategy

เนื่องจากไม่มี bot เดียวที่ work ทุก market phase มี 3 แนวทาง:

```
แนวทางที่ 1 (Beginner):   Bot เดี่ยว → ยอมรับว่า underperform ในบาง phase
แนวทางที่ 2 (Recommended): Grid 50% + Trend 30% + DCA 20%
แนวทางที่ 3 (Advanced):   Market Detection → Auto-switch strategy
```

### ✅ Design Decision
> เริ่มด้วย **Grid + DCA** สองตัวก่อน ครอบคลุม sideways + long-term โดยไม่ซับซ้อน

---

## 2. Market Regime Detection

### เปรียบเทียบวิธี

| Method | Complexity | Accuracy | เหมาะเริ่มต้น |
|--------|-----------|----------|--------------|
| Rule-based (ADX + BBW) | ต่ำ | ปานกลาง | ✅ ใช่ |
| Volatility-based (ATR) | ต่ำ | ปานกลาง | ✅ ใช่ |
| HMM | ปานกลาง | ดี | ❌ (Phase 2) |
| ML Classifier | ยาก | ดีมาก | ❌ (Phase 2) |
| HMM + LSTM | ยากมาก | สูงสุด | ❌ (Advanced) |
| Sentiment + On-chain | ยากมาก | แปรผัน | ❌ (Optional) |

### Rule-based Baseline (แนะนำสำหรับเริ่มต้น)

```python
# Regime detection logic
def detect_regime(adx, ema_short, ema_long, bb_width, bb_width_avg):
    if adx > 25:
        if ema_short > ema_long:
            return "BULL"
        else:
            return "BEAR"
    elif adx < 20:
        return "SIDEWAYS"
    else:
        return "TRANSITION"  # ระวัง — หลีกเลี่ยงการ trade ในช่วงนี้
```

### HMM (Phase 2)
- ใช้ 3-state model (Bull / Bear / Sideways) — งานวิจัยพิสูจน์ว่าดีกว่า 2-state สำหรับ BTC
- ต้อง retrain ทุก 30-90 วัน
- Output เป็น probability ของแต่ละ state ไม่ใช่แค่ binary

### ✅ Design Decision
> Phase 1: **ADX + BBW + EMA** (rule-based) → Phase 2: **HMM** เมื่อมี baseline performance

---

## 3. Architecture Patterns

### Pipeline Architecture (แนะนำ)

```
Data Layer → Feature Engineering → Regime Detection → Strategy Engine → Risk Manager → Order Executor → Exchange
     ↑                                                                                          ↓
  WebSocket/REST                                                                          Trade Log
```

### Module Structure (Modular Monolith)

```
crypto-bot/
├── data/
│   ├── exchange_client.py      # CCXT wrapper
│   ├── websocket_manager.py    # WebSocket + reconnect
│   ├── data_validator.py       # Anomaly detection
│   └── ohlcv_store.py          # SQLite storage
├── regime/
│   ├── detector.py             # ADX + BBW + EMA logic
│   └── hmm_detector.py         # Phase 2
├── strategy/
│   ├── base_strategy.py        # Abstract class
│   ├── grid_strategy.py
│   ├── dca_strategy.py
│   └── trend_strategy.py
├── risk/
│   ├── position_sizer.py       # Fixed % + ATR
│   ├── stop_loss.py            # ATR stop + trailing
│   └── portfolio_risk.py       # Correlation + drawdown
├── execution/
│   ├── order_executor.py       # Order lifecycle
│   ├── retry_manager.py        # Exponential backoff
│   └── kill_switch.py          # Emergency stop
├── monitoring/
│   ├── metrics.py              # Prometheus metrics
│   ├── alert.py                # Telegram + email
│   └── logger.py               # Structured JSON log
└── config/
    ├── settings.py             # Load from .env
    └── strategy_config.yaml
```

### Key Principle
> **Separation of concerns:** Strategy code ต้องไม่มีทางลัด bypass Risk Manager เด็ดขาด

### ✅ Design Decision
> **Modular Monolith + Pipeline pattern** — เริ่มใน process เดียว ออกแบบ interface ให้ดี พร้อม extract เป็น microservices ในอนาคต

---

## 4. Risk Management Framework

### Layer 1 — Trade Level

#### Position Sizing
```python
# Fixed % per trade (เริ่มต้น)
position_size = (account_balance * risk_pct) / (entry_price - stop_loss_price)

# ATR-based (แนะนำ)
atr_stop_distance = atr * atr_multiplier  # e.g., 2.0
position_size = (account_balance * risk_pct) / atr_stop_distance

# Parameters แนะนำ
RISK_PER_TRADE = 0.01      # 1% ต่อ trade
ATR_MULTIPLIER = 2.0       # stop ห่าง 2× ATR
MAX_POSITION_SIZE = 0.05   # max 5% ของ portfolio ต่อ position
```

#### Stop-Loss Types
| Type | สูตร | เหมาะกับ |
|------|------|---------|
| Fixed % | `SL = Entry × (1 - stop_pct)` | เริ่มต้น ง่าย |
| ATR | `SL = Entry - (ATR × multiplier)` | แนะนำ — ปรับตาม volatility |
| Trailing | ขยับตาม price ขึ้น ไม่ลง | Trend following |
| Time-based | ถือ > N ชั่วโมง → ออก | ป้องกัน dead trade |

### Layer 2 — Session Level

#### Circuit Breakers
```python
CIRCUIT_BREAKERS = {
    'daily_loss_limit': 0.05,       # หยุดถ้า loss > 5% ของ capital วันนั้น
    'max_drawdown_from_peak': 0.15, # หยุดถ้า equity ต่ำกว่า peak > 15%
    'consecutive_losses': 5,         # pause หลังแพ้ 5 ไม้ติด
    'max_daily_trades': 50,         # ป้องกัน runaway loop
}
```

#### Recovery Math (ต้องจำ)
```
10% loss → ต้องการ 11.1% gain เพื่อ breakeven
25% loss → ต้องการ 33.3% gain
50% loss → ต้องการ 100% gain
75% loss → ต้องการ 300% gain
```

### Layer 3 — Portfolio Level
```python
PORTFOLIO_RULES = {
    'max_correlated_positions': 3,  # max 3 position ทิศทางเดียวกัน
    'active_capital_ratio': 0.65,   # deploy 65%, เก็บ 35% reserve
    'strategy_allocation': {
        'grid': 0.50,
        'trend': 0.30,
        'dca': 0.20,
    }
}
```

### Layer 4 — Volatility-adaptive
```python
# ลด position size เมื่อ drawdown เพิ่ม
def drawdown_scaled_size(base_size, current_drawdown, max_drawdown):
    scale = 1 - (current_drawdown / max_drawdown)
    return base_size * max(scale, 0.25)  # ลดได้สูงสุด 75%

# ปรับ stop ตาม volatility
def volatility_adjusted_stop(base_stop, current_atr, avg_atr):
    vol_ratio = current_atr / avg_atr
    return base_stop * vol_ratio
```

### ✅ Design Decision
> **Fixed 1% risk/trade + ATR stop (2×) + Daily loss limit 3-5% + Max drawdown 15% kill switch**

---

## 5. Backtesting & Validation

### Workflow
```
1. Develop strategy
2. Simple backtest (in-sample) — idea validation
3. Walk-forward test — robustness check
4. Monte Carlo simulation — edge case testing
5. Paper trade 30+ วัน — live validation
6. Live trade (small capital) — scale ขึ้นเมื่อ proven
```

### Walk-Forward Protocol
```python
# Sliding window
# Train: Jan-Jun → Test: Jul
# Train: Feb-Jul → Test: Aug
# Train: Mar-Aug → Test: Sep
# ...

# Overfitting check
if out_of_sample_sharpe < in_sample_sharpe * 0.6:  # ลด >40%
    print("OVERFIT — do not deploy")

if out_of_sample_max_dd > in_sample_max_dd * 2.0:  # เพิ่ม >2×
    print("OVERFIT — do not deploy")
```

### Transaction Cost Modeling
```python
REALISTIC_COSTS = {
    'fee_multiplier': 2.0,          # fee × 2 สำหรับ conservative test
    'slippage': {
        'top_10': 0.001,            # 0.1% สำหรับ BTC/ETH
        'altcoin': 0.003,           # 0.3% สำหรับ altcoin
    },
    'latency_ms': 200,              # จำลอง API latency
}

# Stress test: ถ้ายังกำไรหลัง costs ทั้งหมด = robust
```

### Key Metrics
```
Sharpe Ratio     > 1.0 (ดี) / > 2.0 (ดีมาก สำหรับ crypto)
Sortino Ratio    > 1.0 (นับแค่ downside vol)
Calmar Ratio     > 1.0 (Annual Return / Max Drawdown)
Profit Factor    > 1.5 (Gross Profit / Gross Loss)
Max Drawdown     < 20% (ควรรับได้)
Win Rate + R:R   ดูคู่กัน — 40% win + 1:3 R:R ยังกำไรได้
```

### Framework Recommendation
```
Crypto bot:        Freqtrade (backtesting + hyperopt + live ในที่เดียว)
Parameter sweep:   VectorBT (เร็วมาก vectorized)
HFT/Market making: hftbacktest (tick-by-tick, order queue simulation)
```

---

## 6. Data Layer & Exchange API

### Architecture

```
Exchange WebSocket ──┐
Exchange REST API ───┤
Third-party API ─────┼──→ [Normalizer] → [Validator] → [Cache/DB] → Strategy
On-chain data ───────┘

Storage: SQLite (เล็ก) / TimescaleDB (ใหญ่)
```

### CCXT Usage Pattern
```python
import ccxt

# เปลี่ยน exchange แค่บรรทัดนี้ — code ที่เหลือเหมือนกัน
exchange = ccxt.binance({
    'apiKey': os.getenv('API_KEY'),
    'secret': os.getenv('API_SECRET'),
    'enableRateLimit': True,
})

# WebSocket (CCXT Pro)
async def watch_ohlcv():
    while True:
        ohlcv = await exchange.watch_ohlcv('BTC/USDT', '1h')
        process(ohlcv)
```

### WebSocket Resilience Pattern
```python
async def websocket_manager():
    backoff = 1
    while True:
        try:
            await connect_and_stream()
            backoff = 1  # reset on success
        except Exception as e:
            logger.error(f"WS disconnect: {e}")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)  # exponential backoff, max 60s
```

### Data Types Priority
```
เริ่มต้นด้วย:   OHLCV + Account balance
เพิ่มทีหลัง:   Order book depth
Optional:       Trade ticks, Funding rate, Sentiment
```

### Exchange Selection Criteria
```
Primary exchange:   Binance (liquidity สูงสุด) หรือ Bybit (derivatives)
Data API:           CCXT (unified) ก่อน native API ต่อเมื่อ optimize
Region:             เลือก server ใกล้ exchange datacenter
```

---

## 7. Order Execution Engine

### Order Lifecycle State Machine
```
SIGNAL_RECEIVED
      ↓
RISK_CHECKED (pass risk manager)
      ↓
PRE_EXECUTION_CHECK (balance, price sanity, market open)
      ↓
ORDER_SUBMITTED (send to exchange, receive order_id)
      ↓ (timeout: 30s for limit, 10s for cancel)
AWAITING_FILL
      ↓                    ↓                    ↓
   FILLED            PARTIAL_FILLED         FAILED/TIMEOUT
      ↓                    ↓                    ↓
UPDATE_POSITION     HANDLE_PARTIAL        RETRY / CANCEL / ALERT
```

### Order Type Selection Logic
```python
def select_order_type(signal_urgency, market_condition):
    if signal_urgency == 'STOP_LOSS' or signal_urgency == 'EMERGENCY':
        return 'MARKET'     # execution certainty > price
    elif market_condition == 'LIQUID' and not time_critical:
        return 'LIMIT'      # cheaper maker fee
    elif signal_urgency == 'ARBITRAGE':
        return 'FOK'        # all-or-nothing
    else:
        return 'LIMIT'      # default
```

### Retry Logic
```python
async def submit_with_retry(order_params, max_retries=3):
    client_order_id = generate_unique_id()
    order_params['clientOrderId'] = client_order_id

    for attempt in range(max_retries):
        try:
            # Check for existing order first (idempotency)
            existing = await check_existing_order(client_order_id)
            if existing:
                return existing

            result = await exchange.create_order(**order_params)
            return result

        except NetworkError as e:
            wait = (2 ** attempt) + random.uniform(0, 1)  # + jitter
            await asyncio.sleep(min(wait, 30))

    # Last resort: fall back to market order
    return await submit_market_fallback(order_params)
```

### Slippage Control
```python
SLIPPAGE_CONFIG = {
    'BTC/USDT': 0.001,    # 0.1%
    'ETH/USDT': 0.001,    # 0.1%
    'default': 0.003,      # 0.3% สำหรับ altcoin
}

def check_price_deviation(signal_price, current_price, symbol):
    max_slippage = SLIPPAGE_CONFIG.get(symbol, SLIPPAGE_CONFIG['default'])
    deviation = abs(current_price - signal_price) / signal_price
    if deviation > max_slippage:
        raise PriceDeviationError(f"Price moved {deviation:.2%} — skip order")
```

### Kill Switch
```python
class KillSwitch:
    def __init__(self):
        self.triggered = False

    async def trigger(self, reason: str):
        self.triggered = True
        logger.critical(f"KILL SWITCH: {reason}")
        await cancel_all_open_orders()
        await send_alert(f"🚨 KILL SWITCH TRIGGERED: {reason}", channel='critical')

    def check(self):
        if self.triggered:
            raise KillSwitchError("Trading halted")
```

---

## 8. Security

### API Key Configuration
```python
# Permission ที่ควรเปิด/ปิด
REQUIRED:   Read (balance, positions, orders)
REQUIRED:   Trade (place, cancel, modify orders)
DISABLED:   Transfer (subaccount)      ← ปิดถ้าไม่จำเป็น
DISABLED:   Withdraw                   ← ห้ามเปิดเด็ดขาด
```

### Secure Storage Pattern
```python
# .env file (ไม่ commit)
API_KEY=xxx
API_SECRET=yyy

# Python code
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('API_KEY')
if not api_key:
    raise ValueError("API_KEY not set — check .env file")
```

### .gitignore ที่ต้องมี
```gitignore
# Secrets
.env
.env.*
*.key
secrets/
config/private/

# Logs (อาจมี sensitive data)
logs/
*.log

# Local data
data/
*.db
```

### Pre-commit Hook (ป้องกัน accidental commit)
```bash
# Install git-secrets
brew install git-secrets  # macOS
git secrets --install
git secrets --register-aws
git secrets --add 'BINANCE_API_KEY\s*=\s*.+'
git secrets --add 'API_SECRET\s*=\s*.+'
```

### IP Whitelist Setup
```
1. VPS: เลือก provider ที่ให้ static IP (Hetzner, Vultr, DO)
2. Exchange: API Management → เพิ่ม VPS IP ใน whitelist
3. SSH: ปิด password auth, ใช้ SSH key เท่านั้น
4. Firewall: ufw allow 22/tcp from YOUR_HOME_IP
            ufw allow 443/tcp
            ufw enable
```

---

## 9. Monitoring & Alerting

### Metrics Schema (Prometheus)
```python
from prometheus_client import Counter, Gauge, Histogram

# Financial
pnl_gauge = Gauge('bot_pnl_usdt', 'Current P&L in USDT', ['strategy'])
win_rate = Gauge('bot_win_rate', 'Win rate rolling 30d', ['strategy'])
drawdown = Gauge('bot_drawdown_pct', 'Current drawdown from peak')

# Execution
orders_total = Counter('bot_orders_total', 'Total orders', ['status', 'type'])
fill_latency = Histogram('bot_fill_latency_seconds', 'Signal to fill latency')
retry_counter = Counter('bot_retries_total', 'Total retries', ['reason'])

# System
ws_uptime = Gauge('bot_websocket_uptime', 'WebSocket connection uptime')
api_latency = Histogram('bot_api_latency_seconds', 'API call latency', ['endpoint'])
```

### Alert Rules (Prometheus/Grafana)
```yaml
groups:
  - name: bot_critical
    rules:
      - alert: DrawdownCritical
        expr: bot_drawdown_pct > 15
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Drawdown exceeded 15% — considering kill switch"

      - alert: WebSocketDown
        expr: bot_websocket_uptime == 0
        for: 5m
        labels:
          severity: critical

  - name: bot_warning
    rules:
      - alert: FillRateLow
        expr: rate(bot_orders_total{status="filled"}[1h]) / rate(bot_orders_total[1h]) < 0.8
        for: 30m
        labels:
          severity: warning
```

### Telegram Alert Pattern
```python
async def send_alert(message: str, severity: str = 'info'):
    icon = {'critical': '🚨', 'warning': '⚠️', 'info': 'ℹ️'}.get(severity, '📊')
    formatted = f"{icon} *Bot Alert*\n\n{message}\n\n`{datetime.now().isoformat()}`"

    if severity == 'critical':
        await send_telegram(formatted)
        await send_email(formatted)  # backup channel
    elif severity == 'warning':
        await send_telegram(formatted)
    else:
        logger.info(message)  # log only for info
```

### Structured Logging
```python
import structlog

logger = structlog.get_logger()

# Trade log
logger.info("order_filled",
    order_id="12345",
    symbol="BTC/USDT",
    side="buy",
    quantity=0.01,
    price=45000,
    fee=0.045,
    signal_time="2025-01-01T00:00:00Z",
    fill_time="2025-01-01T00:00:00.150Z",
    latency_ms=150,
    strategy="grid",
    regime="sideways"
)
```

### Performance Review Cadence
```
Daily (5 min):     P&L review, error count, fill rate check
Weekly (30 min):   Performance vs backtest, slippage trend
Monthly (2 hr):    Rolling Sharpe, strategy health, parameter review
Quarterly (1 day): Walk-forward re-test, strategy re-optimization
```

---

## 10. Deployment & Infrastructure

### Recommended Stack (Starter)

```yaml
# docker-compose.yml
version: '3.8'

services:
  bot:
    build: .
    restart: always
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - prometheus

  prometheus:
    image: prom/prometheus:latest
    restart: always
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    restart: always
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"

  loki:
    image: grafana/loki:latest
    restart: always

volumes:
  prometheus_data:
  grafana_data:
```

### systemd Service (Python bot)
```ini
# /etc/systemd/system/crypto-bot.service
[Unit]
Description=Crypto Trading Bot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/home/botuser/crypto-bot
ExecStart=/home/botuser/.venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
EnvironmentFile=/home/botuser/crypto-bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable crypto-bot
sudo systemctl start crypto-bot

# Monitor
sudo journalctl -u crypto-bot -f
```

### VPS Selection Guide
```
Strategy ทั่วไป (Grid/DCA/Trend):
  Budget:    Hetzner CX21 €5.83/mo (EU) หรือ Vultr $6/mo
  Spec:      2 vCPU, 4GB RAM, 40GB SSD
  Location:  ใกล้ exchange หลักที่ใช้
  OS:        Ubuntu 24.04 LTS

Exchange → VPS Location:
  Binance EU   → Frankfurt/Amsterdam (Hetzner)
  Binance Asia → Tokyo / Singapore (Vultr)
  Bybit        → Singapore (Vultr)
  Coinbase     → US East / Virginia (DigitalOcean, Vultr)
  Kraken       → US East หรือ EU

Arbitrage / Scalping:
  Upgrade:   4-8 vCPU, NVMe SSD
  Provider:  Vultr High Frequency หรือ Linode Dedicated
```

### Deployment Checklist
```bash
# Pre-deploy
[ ] git pull && run tests
[ ] check .env values
[ ] backup current config + state
[ ] close open positions (major change only)
[ ] deploy during low-volatility (weekend preferred)

# Deploy
[ ] docker-compose pull && docker-compose up -d
[ ] หรือ systemctl restart crypto-bot

# Post-deploy (5-10 min)
[ ] tail logs: journalctl -u crypto-bot -f
[ ] check Telegram: bot ส่ง "Bot started" ไหม
[ ] check Grafana: metrics ขึ้นไหม
[ ] verify first trade executes correctly
[ ] confirm rollback plan if issues
```

---

## 11. Design Decisions Summary

### ตาราง Design Decisions

| หัวข้อ | Decision | เหตุผล |
|--------|---------|--------|
| **Bot Type** | Grid + DCA (เริ่มต้น) | ครอบคลุม sideways + long-term, ไม่ซับซ้อน |
| **Regime Detection** | ADX + BBW + EMA → HMM (Phase 2) | เริ่มง่าย, upgrade ได้เมื่อพร้อม |
| **Architecture** | Modular Monolith + Pipeline | balance ระหว่างความง่ายและ maintainability |
| **Communication** | Event-driven ภายใน module | ลด coupling, ง่าย test แยก |
| **Risk per trade** | Fixed 1% | conservative, scale ได้, ป้องกัน blow-up |
| **Stop-loss** | ATR × 2.0 | ปรับตาม volatility อัตโนมัติ |
| **Circuit breaker** | Daily 5% + Peak 15% | สมดุลระหว่าง protection และ false trigger |
| **Capital reserve** | 35% reserve เสมอ | buffer + opportunity fund |
| **Backtesting** | Freqtrade + Walk-forward | crypto-specific, ครบ workflow |
| **Exchange** | Binance (primary) + CCXT | liquidity สูงสุด, unified interface |
| **Data** | WebSocket (market data) + REST (orders) | hybrid ดีที่สุด |
| **Order default** | Limit order (maker fee) | ประหยัด fee ระยะยาว |
| **Execution guard** | FOK สำหรับ arbitrage | atomic execution |
| **API key** | Trade-only, no withdraw | security baseline |
| **Storage** | .env + HashiCorp Vault (prod) | simple แต่ secure |
| **Network** | IP whitelist + SSH key | block >99% remote attack |
| **Process manager** | systemd (Python) / PM2 (Node.js) | auto-restart, stable |
| **Container** | Docker + Docker Compose | reproducible deployment |
| **Monitoring** | Prometheus + Grafana + Loki | open source, standard |
| **Alerting** | Telegram (critical) + Email (warning) | fast + backup channel |
| **VPS** | Hetzner (EU) หรือ Vultr (Asia/US) | ใกล้ exchange, ราคาสมเหตุ |
| **VPS spec** | 2-4 vCPU, 4GB RAM, Ubuntu 24 | เพียงพอสำหรับ bot ส่วนตัว |
| **CI/CD** | Manual checklist → GitHub Actions | เริ่มง่าย upgrade ทีหลัง |

---

## 12. กฎสำคัญที่ต้องจำ

### 🔴 กฎเหล็ก (ห้ามฝ่าฝืน)

1. **Strategy code ต้องผ่าน Risk Manager เสมอ** — ไม่มีทางลัด bypass
2. **ห้าม enable withdrawal permission บน bot API key เด็ดขาด**
3. **ห้าม hardcode API key ใน code หรือ commit ขึ้น git**
4. **Never assume — always verify open orders with exchange before retry**
5. **ไม่มี bot เดียวที่ดีในทุกสภาวะตลาด** — ต้องมี fallback strategy
6. **Home computer ไม่เพียงพอสำหรับ live trading** — ใช้ VPS เสมอ

### 🟡 หลักการสำคัญ

7. **Capital preservation comes first, profits second** — drawdown control > return maximization
8. **Crypto correlation สูงมาก** — 5 bot บน 5 coins ≠ diversified จริง ต้อง strategy diversification
9. **Backtest ส่วนใหญ่โกหก** — model fee×2, slippage×2, latency 200ms เสมอ
10. **Silence ≠ stability** — ถ้าไม่มี alert อาจแปลว่า missing instrumentation
11. **Alert fatigue ทำให้ ignore ของสำคัญ** — แบ่ง tier ให้ชัดเจน ไม่ alert ทุกอย่างเท่ากัน
12. **เปลี่ยนแค่ 1 variable ต่อครั้ง และ document ทุก change** — ไม่งั้นไม่รู้ว่าอะไรทำให้ดีขึ้นหรือแย่ลง

### 🟢 Best Practices

13. **เริ่มเล็ก ทดสอบนาน scale ช้า** — paper trade 30+ วันก่อน live
14. **IP whitelist เป็น defense ที่ cost ต่ำที่สุดแต่ได้ผลมากที่สุด**
15. **VPS ใกล้ exchange datacenter** — latency ต่างกัน 10-50× จาก home connection
16. **systemd / PM2 สำหรับ auto-restart** — ไม่มีใครตื่นมาเปิด bot ตี 3
17. **Walk-forward testing เป็น minimum standard** สำหรับ strategy ที่จะ deploy จริง
18. **Structured JSON log ทุก trade** — เป็น goldmine สำหรับ future optimization
19. **ตรวจ strategy health รายเดือน** — strategy drift เกิดช้าๆ แต่ทำลายพอร์ตได้มาก
20. **Subaccount แยก bot capital จาก main account** — isolate worst-case loss

---

*Knowledge base นี้ compile จาก research session ของ Crypto Trading Bot Design — อัปเดตเมื่อมีข้อมูลใหม่*
