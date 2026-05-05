# Crypto Trading Bot Research - Raw Q&A Notes

บันทึกนี้เก็บคำถามและคำตอบจากการคุยกันแบบ raw ตามลำดับ เพื่อใช้ย้อนดูบริบทก่อนเริ่มออกแบบระบบจริง

วันที่เริ่มบันทึก: 2026-05-04

---

## 1. ประเภทของ Crypto Trading Bot

### คำถาม

ในช่วงปีนี้หรือปีที่ผ่านมา trading bot crypto มีกี่ประเภทที่น่าสนใจ มีจุดประสงค์ในการทำงานกี่แบบ และข้อดีข้อเสียของแต่ละแบบคืออะไร

### คำตอบสรุป

Crypto trading bot ที่น่าสนใจแบ่งได้ประมาณ 11-15 ประเภทหลัก และมีจุดประสงค์หลักประมาณ 7 แบบ

จุดประสงค์หลัก:

- สะสมเหรียญระยะยาว: DCA, auto-invest
- กินความผันผวนในกรอบราคา: grid, mean reversion
- เกาะเทรนด์หรือ momentum: trend-following, breakout
- หากำไรจากราคาคลาดเคลื่อน: arbitrage, funding-rate arbitrage
- ทำตลาดและกิน spread: market making
- จัดพอร์ตและลดความเสี่ยง: rebalancing, hedging, risk bot
- ช่วย execution: TWAP, iceberg, smart order routing

ประเภท bot สำคัญ:

- DCA Bot: เข้าใจง่าย เหมาะกับสะสมระยะยาว แต่ไม่กันเหรียญลงยาว
- Grid Bot: เหมาะกับตลาด sideways แต่เสี่ยงมากถ้าหลุดกรอบ
- Futures Grid Bot: ทำได้ทั้งบางช่วงขึ้น/ลง แต่เสี่ยง liquidation
- Trend-Following Bot: ได้ move ใหญ่ แต่แพ้บ่อยใน sideways
- Momentum/Breakout Bot: จับจังหวะทะลุกรอบ แต่ false breakout เยอะ
- Mean-Reversion/RSI Bot: เหมาะกับตลาดแกว่งกลับค่าเฉลี่ย แต่แพ้ใน trend แรง
- Scalping Bot: กินกำไรสั้นหลายครั้ง แต่แพ้ fee/slippage ง่าย
- Arbitrage Bot: ดูเหมือนเสี่ยงต่ำ แต่ติด latency, fee, liquidity, execution risk
- Funding-Rate Arbitrage Bot: market-neutral ได้บางแบบ แต่ต้อง hedge แม่น
- Market-Making Bot: กิน spread ถี่ แต่มี inventory risk สูง
- Portfolio Rebalancing Bot: คุมสัดส่วนพอร์ต แต่ขาย winner เร็วเกินได้
- Signal/Webhook Bot: แยก signal กับ execution ได้ดี แต่ขึ้นกับคุณภาพ signal
- AI/ML/Sentiment Bot: วิเคราะห์ข้อมูลหลากหลาย แต่ overfit/อธิบายยาก
- TWAP/Iceberg/Execution Bot: ช่วยลด slippage แต่ไม่ใช่ alpha โดยตัวเอง
- Sniper/Launch Bot: upside สูงมาก แต่เสี่ยง scam, rug, MEV, rule violations

ข้อเสนอเบื้องต้น:

- เริ่มจาก backtest + paper trading
- ใช้ spot-only ก่อน
- เริ่มด้วย DCA/Grid/Trend แบบ rule-based ก่อน
- AI ควรเป็น analyst layer ไม่ใช่คนส่ง order จริงตั้งแต่แรก

---

## 2. ต้องมีหลาย Strategy หรือไม่

### คำถาม

แต่ละ strategy เหมาะกับตลาดต่างกัน แสดงว่าต้องทำมากกว่า 1 strategy หรือเปล่า

### คำตอบสรุป

ใช่ ในระยะยาวควรมีมากกว่า 1 strategy เพราะไม่มี strategy เดียวที่เหมาะกับทุก market regime

โครงที่เหมาะ:

```text
Market Data
  -> Regime Detector
  -> Strategy Router
  -> Risk Manager
  -> Execution Engine
```

ตัวอย่าง:

- Sideways: Grid, mean reversion
- Uptrend: Trend-following, breakout, DCA
- Downtrend: Cash, hedge, cautious DCA, short trend ถ้า futures
- High volatility: reduce size, widen grid/stop, maybe pause
- Low liquidity: avoid scalping/market making
- News shock: pause or reduce risk

ข้อเสนอ:

- Version 1: strategy เดียวก่อน แต่ architecture รองรับหลาย strategy
- Version 2: เพิ่ม regime detector + strategy router
- Version 3: strategy allocation และ risk budget ต่อ strategy

---

## 3. Market Regime Detection

### คำถาม

บอทจะรู้ได้อย่างไรว่าตอนนี้ตลาดอยู่ในสถานะไหน มีวิธีจับแบบไหนที่น่าสนใจและข้อดีข้อเสียอย่างไร

### คำตอบสรุป

Market regime detection ที่น่าสนใจแบ่งได้ 8 กลุ่มหลัก:

1. Moving Average Regime Filter
   - ดูราคาเหนือ/ใต้ EMA/SMA และ slope
   - ข้อดี: ง่าย อธิบายได้ backtest ง่าย
   - ข้อเสีย: lagging และ false signal ใน sideways

2. ADX / Directional Movement
   - วัดความแรงของ trend
   - ข้อดี: แยก trend กับ range ได้ดี
   - ข้อเสีย: lagging และ ADX สูงอาจเป็นปลาย trend

3. Volatility Regime: ATR / Realized Volatility
   - วัดความผันผวน
   - ข้อดี: ดีมากสำหรับ position sizing/risk
   - ข้อเสีย: ไม่บอกทิศทาง

4. Bollinger Band Width / Compression
   - จับช่วงบีบตัวและขยายตัว
   - ข้อดี: เหมาะกับ breakout watch
   - ข้อเสีย: ไม่บอกทิศทาง breakout

5. Market Structure Detection
   - higher high/lower low, range, support/resistance
   - ข้อดี: ใกล้ trader logic
   - ข้อเสีย: rule robust ยาก

6. Volume / Liquidity Regime
   - volume, spread, order book depth, open interest, funding
   - ข้อดี: สำคัญมากกับ crypto และ execution
   - ข้อเสีย: ต้องต่อ data/API เพิ่ม

7. Clustering / K-Means
   - ให้ model จัดกลุ่มจาก return, volatility, trend, volume
   - ข้อดี: เจอ regime ที่ indicator เดี่ยวไม่เห็น
   - ข้อเสีย: ตีความยากและเสี่ยง overfit

8. Hidden Markov Model / Markov Regime Switching
   - ประเมิน hidden market state เป็น probability
   - ข้อดี: เหมาะกับแนวคิด regime จริง
   - ข้อเสีย: ซับซ้อนและต้อง validate ดี

Baseline ที่น่าใช้:

```text
EMA 50/200
ADX
ATR percentile
Bollinger Band Width
Volume + spread filter
```

เป้าหมาย output:

```text
UPTREND_LOW_VOL
UPTREND_HIGH_VOL
DOWNTREND_HIGH_VOL
SIDEWAYS_LOW_VOL
SIDEWAYS_HIGH_VOL
BREAKOUT_WATCH
NO_TRADE
```

---

## 4. Bot Architecture

### คำถาม

Architecture ของ bot ที่น่าสนใจมีอะไรบ้าง พร้อมข้อดีข้อเสียของแต่ละแบบ

### คำตอบสรุป

Architecture ที่สำคัญ:

- Simple Loop Bot
  - ทำเร็ว เข้าใจง่าย
  - โตยาก, live/backtest คนละ logic, order state ยาก

- Layered Modular Bot
  - แยก data, strategy, risk, execution
  - เหมาะกับ version แรกจริงจัง
  - ต้องออกแบบ interface ดี

- Event-Driven Bot
  - event เช่น MarketDataEvent, SignalEvent, OrderEvent, FillEvent
  - backtest/live สมจริงขึ้น
  - ซับซ้อนกว่า loop

- Backtest-Live Unified Engine
  - strategy code เดียวใช้ได้ทั้ง backtest/paper/live
  - ลดช่องว่างระหว่างอดีตกับเงินจริง
  - ออกแบบยากกว่าแต่คุ้ม

- Multi-Strategy Portfolio Bot
  - หลาย strategy + allocation + regime switching
  - กระจาย risk ได้
  - attribution/debug ยาก

- Microservices Bot
  - แยก service เช่น data, risk, execution, portfolio
  - scale ดี
  - operational complexity สูง

- Connector-Based Architecture
  - strategy คุยกับ standard exchange interface
  - เปลี่ยน exchange ง่าย
  - abstraction รั่วได้เพราะ exchange ต่างกันจริง

- Research-First Quant Platform
  - เน้น data/backtest/optimization/walk-forward
  - ดีต่อการทดลอง
  - เสี่ยง overfitting ถ้าไม่มีวินัย

- Risk-First Execution Architecture
  - ทุก order ผ่าน risk engine กลาง
  - เหมาะกับเงินจริง
  - ใช้เวลาสร้างเยอะกว่า

- AI/Agentic Architecture
  - ใช้ AI ช่วย analyze/context
  - ไม่ควรให้ AI ส่ง order จริงโดยไม่มี guardrail

ข้อเสนอ:

```text
Modular Monolith
Event-inspired internals
Backtest-live unified design
Central Risk Manager
Connector abstraction
Microservice-ready boundaries
```

---

## 5. Event-Driven vs Microservices vs Agent

### คำถาม

Event-Driven กับ Microservices คล้ายกันมาก ต่างกันอย่างไร และคล้าย agent หลายตัวไหม

### คำตอบสรุป

สามคำนี้อยู่คนละมิติ:

- Event-Driven = วิธีจัด flow ด้วย event/message
- Microservices = วิธีแบ่งระบบเป็น service/process/deployment แยกกัน
- Agent = หน่วยที่รับ input ตัดสินใจ และลงมือทำ อาจเป็น software component หรือ AI agent

ตัวอย่าง:

```text
Monolith + Loop
Monolith + Event-Driven
Microservices + Request/Response
Microservices + Event-Driven
```

Agent อาจหมายถึง:

- software agent/component เช่น StrategyAgent, RiskAgent
- AI/LLM agent ที่ reasoning/use tools
- actor model ที่ถือ state และรับ message

ข้อเสนอ:

```text
Modular Monolith
Event-Driven Internals
Agent-like Components
Microservice-ready Boundaries
```

---

## 6. หมวดที่ยังต้อง Research ก่อนออกแบบ

### คำถาม

มีส่วนของ crypto bot ที่ยังไม่ได้ยกขึ้นมาหรือยังไม่ได้ research ไหม

### คำตอบสรุป

หมวดที่ควร research ต่อ:

- Exchange/API Layer
- Order Execution & Order Types
- Risk Management
- Backtesting Methodology
- Data Pipeline
- Paper Trading / Dry Run
- Portfolio & Accounting
- Monitoring, Alerts, Ops
- Security
- Deployment
- Legal / Compliance / Exchange Rules
- Strategy Evaluation Metrics

ลำดับที่ควร research:

1. Risk Management
2. Backtesting Methodology
3. Exchange/API + Execution
4. Data Pipeline
5. Monitoring/Security/Deployment

---

## 7. Risk Management

### คำถาม

Research risk management ก่อนดีไหม

### คำตอบสรุป

Risk management ควรเป็น core architecture ไม่ใช่ feature เสริม

แบ่งเป็น 6 ชั้น:

1. Trade-Level Risk
   - risk per trade, stop loss, take profit, risk/reward
   - position size ควรคำนวณจากระยะ stop

2. Position Sizing
   - fixed size
   - fixed fractional
   - volatility/ATR based
   - Kelly criterion
   - capped sizing

   ข้อเสนอ:

   ```text
   fixed fractional + ATR adjustment + hard max cap
   ```

3. Portfolio-Level Risk
   - max exposure per symbol
   - max total exposure
   - max open risk
   - max correlated exposure

4. Drawdown Control / Circuit Breaker
   - daily loss limit
   - weekly loss limit
   - max drawdown stop
   - stop after N losses
   - cooldown

5. Execution Risk
   - slippage
   - spread
   - partial fill
   - stale price
   - exchange disconnect

6. Leverage / Futures Risk
   - max leverage
   - isolated/cross margin
   - liquidation buffer
   - funding rate
   - reduce-only

Baseline:

```text
spot_only = true
risk_per_trade = 0.5%-1%
max_position_per_pair = 10%
max_total_exposure = 50%-60%
daily_loss_limit = 2%
max_drawdown_stop = 10%
max_open_positions = 3-5
spread_filter = enabled
cooldown_after_loss = enabled
```

---

## 8. Backtesting

### คำถาม

Research backtesting ต่อ

### คำตอบสรุป

Backtesting ไม่ใช่เครื่องพิสูจน์ว่า strategy จะกำไร แต่เป็นเครื่องมือคัดกรอง strategy ก่อน paper/live

ส่วนสำคัญ:

1. Data Granularity
   - OHLCV, lower timeframe, tick data, order book
   - version แรกควรใช้ OHLCV + lower timeframe detail

2. Lookahead Bias
   - signal จาก candle N ใช้ order ได้เร็วสุด candle N+1
   - strategy ห้ามเห็น future candle

3. Recursive/Warmup Bias
   - indicator ต้องมี warmup
   - backtest/live window ต้องใกล้กัน

4. Fill Simulation
   - market order คิด bid/ask/slippage
   - limit order ไม่ควร assume ว่า fill เสมอ
   - partial fill ต้องรองรับ

5. Fee, Spread, Slippage
   - ทุกผลต้อง net of fees
   - stress test ด้วย fee/slippage แย่กว่าปกติ

6. Out-of-Sample / Walk-Forward
   - train/validate/test
   - walk-forward เพื่อลด overfit

7. Metrics
   - total return, CAGR, max drawdown, Sharpe, Sortino, Calmar
   - profit factor, expectancy, win rate, exposure time, fee drag
   - compare vs buy-and-hold BTC

8. Backtest/Paper/Live Consistency
   - strategy code เดียวกัน
   - ต่างกันแค่ data adapter และ broker adapter

9. Backtesting Protections
   - risk rules ต้องเปิดใน backtest ด้วย

Baseline:

```text
OHLCV data
1m/5m detail + strategy timeframe
configurable maker/taker fees
configurable slippage
next-candle execution
conservative limit fill
risk rules enabled
trades.csv + equity_curve.csv + summary.json
```

---

## 9. Data Layer & Exchange API

### คำถาม

Research Data layer & Exchange API

### คำตอบสรุป

Data Layer คือระบบประสาทสัมผัสของ bot ส่วน Exchange API คือมือที่คุยกับตลาดจริง

ข้อมูลที่ควรมี:

- OHLCV candles
- ticker / best bid-ask
- trades
- order book
- funding rate
- open interest
- balances
- orders/fills
- exchange metadata

Version แรก:

```text
OHLCV + ticker/bookTicker + balances + orders/fills + exchange metadata
```

REST vs WebSocket:

- REST: snapshots, balances, create/cancel order, reconciliation
- WebSocket public: market data สด
- WebSocket private: order/fill/account update

Exchange metadata ต้องตรวจ:

- price precision / tick size
- amount precision / step size
- min quantity
- min notional
- max order size
- supported order types
- active symbol

Storage:

- Parquet: historical candles
- SQLite: orders, fills, positions, balances, bot state
- YAML/JSON: config
- DuckDB/Postgres ค่อยเพิ่มเมื่อระบบโต

Data quality checks:

- missing candles
- duplicate timestamps
- out-of-order events
- stale data
- timezone UTC
- candle close confirmation

CCXT:

- ใช้ได้ดีใน version แรกสำหรับ REST abstraction
- strategy ห้ามคุยกับ exchange โดยตรง
- ควรมี internal exchange interface ห่อ CCXT อีกชั้น

---

## 10. Order Execution Engine

### คำถาม

Research Order Execution Engine

### คำตอบสรุป

Execution Engine ไม่ควรคิดว่าจะซื้อขายไหม แต่ควรเปลี่ยน OrderIntent ที่ผ่าน risk แล้วให้เป็น order จริงอย่างปลอดภัย

หน้าที่หลัก:

- แปลง OrderIntent เป็น exchange order
- validate precision/min notional
- เลือก order type
- ส่ง order
- track lifecycle
- รับ partial/full fill
- cancel/replace/timeout
- ป้องกัน duplicate ด้วย clientOrderId
- reconcile state
- emit order/fill events

Order types:

- market
- limit
- post-only
- IOC
- FOK
- stop loss
- take profit
- OCO
- iceberg
- trailing stop

Version แรก:

```text
market
limit
post_only limit
stop_loss
take_profit
cancel/replace
```

Lifecycle:

```text
CREATED
SUBMITTED
ACCEPTED / REJECTED
PARTIALLY_FILLED
FILLED / CANCELED / EXPIRED / FAILED
```

สำคัญมาก:

- ทุก order ต้องมี clientOrderId
- API timeout ไม่ได้แปลว่า order ไม่ถูกสร้าง
- partial fill ต้อง update position/risk/stop size
- cancel อาจเกิดพร้อม fill ได้
- reconciliation ต้องมี on startup, after disconnect, periodic

Baseline:

```text
execution_mode = paper | live
supported_orders = market, limit, post_only, stop_loss
client_order_id_required = true
max_spread = configurable
max_slippage = configurable
stale_price_guard = enabled
cancel_timeout = enabled
partial_fill_handling = required
reconciliation = required
```

---

## 11. Security

### คำถาม

Research Security

### คำตอบสรุป

Security ต้องเป็น defense-in-depth เพราะ bot ถือ API key ที่ส่งคำสั่งกับเงินได้

หมวดหลัก:

1. API Key Permissions
   - Read: yes
   - Trade: yes เฉพาะที่จำเป็น
   - Withdraw: never
   - Transfer: no ถ้าไม่จำเป็น

2. IP Whitelist
   - live key ควรใช้เฉพาะ static IP ของ VPS

3. Secret Storage
   - `.env` สำหรับ local dev
   - `.env.example` มีแต่ชื่อ field
   - `.env` ต้องอยู่ใน `.gitignore`
   - production อาจใช้ Docker secrets/Vault/Secret Manager

4. Environment Separation
   - backtest
   - paper
   - testnet
   - live

5. Logging Hygiene
   - ห้าม log API key, secret, signature, auth headers
   - ต้อง redact sensitive values

6. Runtime Safety
   - kill switch
   - max daily loss
   - max order notional
   - max orders per minute
   - state: ACTIVE, HALTED, REDUCE_ONLY

7. Dependencies & Supply Chain
   - pin versions
   - lockfile
   - scan vulnerabilities

8. Incident Response
   - halt bot
   - cancel open orders
   - disable/delete key
   - rotate key
   - export logs/fills
   - reconcile balances

Baseline:

```text
default_mode = paper
live disabled by default
withdraw permission forbidden
IP whitelist required for live
separate keys for read/paper/live
API keys never printed
central secret loader with redaction
kill switch required
startup safety checklist required
```

---

## 12. Monitoring & Alerting

### คำถาม

Research Monitoring & Alerting

### คำตอบสรุป

Monitoring & Alerting ต้องตอบว่า bot ยังมีชีวิต เห็นตลาดถูก รู้สถานะ order/position ถูก และไม่เสี่ยงเกิน limit หรือไม่

Monitoring 6 ชั้น:

- Process health
- Data health
- Exchange health
- Execution health
- Portfolio/risk health
- Strategy health

Logs:

- structured JSON logs
- fields เช่น timestamp, level, component, event_type, symbol, strategy_id, client_order_id
- ห้าม log secret

Metrics:

- uptime
- heartbeat age
- market data lag
- websocket reconnect count
- REST error count
- orders submitted/filled/rejected
- open orders
- stuck orders
- exposure
- daily P&L
- drawdown
- risk rejections

Alerts:

- bot stopped
- market data stale
- exchange auth failed
- repeated rate limit
- stuck order
- partial fill unresolved
- ledger mismatch
- daily loss hit
- max drawdown hit
- kill switch triggered
- live mode started

Remote commands:

```text
/status
/positions
/orders
/pnl
/pause_entries
/resume_entries
/halt
/cancel_all
```

Baseline:

```text
structured_logs = true
secret_redaction = true
heartbeat = enabled
telegram_alerts = optional but recommended
alert_levels = info/warning/critical/emergency
daily_summary = enabled
startup_live_alert = critical
kill_switch_alert = emergency
dashboard = simple first, Grafana later
```

---

## 13. Deployment & Infrastructure

### คำถาม

Research Deployment & Infrastructure

### คำตอบสรุป

Deployment ทำให้ bot จากโค้ดที่รันได้กลายเป็นระบบที่รันได้นานพอจะไว้ใจได้

แนวทาง:

```text
Phase 1: Local dev + paper trading
Phase 2: VPS + Docker Compose
Phase 3: VPS production hardened
Phase 4: Cloud/Kubernetes เฉพาะเมื่อใหญ่จริง
```

Options:

- Local Machine: เหมาะ dev/backtest แต่ uptime แย่
- VPS: sweet spot สำหรับ live รุ่นแรก
- Docker Compose: reproducible, restart ง่าย, volume ชัด
- Cloud VM: ดีขึ้นแต่แพงกว่า
- Kubernetes: scale ดีแต่ซับซ้อนเกินตอนเริ่ม
- Serverless: ไม่เหมาะกับ bot 24/7/WebSocket

Production รุ่นแรก:

```text
VPS Ubuntu LTS
Docker Compose
bot container
persistent volumes:
  data/
  logs/
  config/
SQLite first
Parquet historical data
Telegram alerts
daily backups
startup reconciliation
```

Security infra:

- SSH key only
- disable password login
- firewall
- non-root user
- IP whitelist API key
- no withdraw permission

Disaster recovery:

- load local state
- fetch exchange open orders
- fetch balances/positions
- reconcile fills
- cancel unknown stale orders if policy says so
- start PAUSED/REDUCE_ONLY if mismatch

Baseline:

```text
production_host = VPS
deployment = Docker Compose
database = SQLite first
historical_data = Parquet volume
logs = structured JSON files
alerts = Telegram
restart_policy = unless-stopped
startup_mode = paused until reconciliation clean
backup = daily SQLite/config/log snapshot
```

---

## 14. Review of Claude Research Set

### คำถาม

มีชุดความรู้อีกชุดจาก Claude ที่ใช้ชุดคำถามเดียวกัน ให้ช่วยดูว่า research ส่วนไหนที่เราไม่มีและมีประโยชน์ ส่วนไหนน่าสนใจจะเอาไป research เพิ่ม โดยไม่ควรเห็นด้วยทันที

### คำตอบสรุป

ชุด Claude มีประโยชน์ในเชิง checklist และ concrete defaults มากกว่าชุดของเรา ส่วนชุดของเรามีความระวังเรื่อง architecture, risk boundary, execution failure modes และ backtest/live consistency มากกว่า

ส่วนที่ควรเอาเข้ามา:

- Monte Carlo simulation สำหรับ backtest robustness
- Strategy drift monitoring
- Performance review cadence
- Pre-commit secret protection / secret scanning
- Subaccount isolation
- Withdrawal address whitelist / account security checklist
- Deployment workflow และ rollback checklist
- Framework comparison เช่น Freqtrade, VectorBT, Backtrader, NautilusTrader, custom engine

ส่วนที่น่าสนใจแต่ต้อง research เพิ่ม:

- เริ่ม Grid + DCA เป็น default
- Grid 50% + Trend 30% + DCA 20% allocation
- HMM เป็น Phase 2 และ claim ว่า 3-state BTC ดีกว่า 2-state
- ตัวเลข risk เช่น daily loss 3-5%, max drawdown 15%, risk 1% ต่อ trade
- Prometheus + Grafana + Loki ตั้งแต่ starter stack
- VPS location mapping ตาม exchange

ส่วนที่ควรระวังก่อนเห็นด้วย:

- Arbitrage risk ต่ำ อาจ oversimplify เพราะ execution/liquidity/transfer/rate-limit risk สูง
- AI/ML accuracy สูง ไม่ได้แปลว่า profitability สูง
- Retry แล้ว fallback เป็น market order ไม่ควรทำทั่วไป ยกเว้น emergency exit
- Limit order default เพราะ maker fee ถูก อาจพลาด fill หรือพลาด trade
- Home computer ไม่พอสำหรับ live trading เห็นด้วยสำหรับ live จริง แต่ local ยังเหมาะกับ dev/paper

ข้อสรุป:

ควรใช้ชุด Claude เป็น candidate defaults และ checklist แต่ไม่ใช่ final design decisions

---

## 15. Framework Decision: Freqtrade vs VectorBT vs Backtrader/Nautilus vs Custom Engine

### คำถาม

Research Framework decision: Freqtrade vs VectorBT vs Backtrader/Nautilus vs custom engine

### คำตอบสรุป

ไม่มี framework เดียวชนะทุกด้าน ต้องตัดสินจากเป้าหมาย:

- ทำ crypto bot ใช้ได้เร็ว: Freqtrade
- research/parameter sweep เร็วมาก: VectorBT
- event-driven production-grade engine: NautilusTrader
- classic event-driven backtesting: Backtrader
- คุม architecture ตาม design เอง: custom engine

ตารางสรุป:

| Framework | จุดแข็ง | จุดอ่อน | เหมาะกับเรา |
|---|---|---|---|
| Freqtrade | crypto-native, backtest/dry-run/live, CCXT, protections, Telegram/WebUI | ติดกรอบ architecture ของ Freqtrade | ดีเป็น MVP runner หรือ benchmark |
| VectorBT | เร็วมากสำหรับ parameter sweep และ portfolio analysis | ไม่ใช่ live bot engine/OMS | ดีเป็น research lab |
| Backtrader | mature, event-driven, strategy API เข้าใจง่าย | crypto live support ไม่เด่น | ดีสำหรับเรียน/prototype |
| NautilusTrader | event-driven production-grade, backtest/live parity, order model ลึก | learning curve สูง, setup หนัก | ดีสำหรับ advanced production candidate |
| Custom Engine | คุม architecture/risk/execution ได้เต็ม | ใช้เวลามากและเสี่ยง bug infrastructure | ดีถ้าเป้าคือสร้าง platform ของเราเอง |

Recommendation:

```text
Primary implementation:
  Custom modular monolith

Research tools:
  VectorBT for fast experiments
  Freqtrade for crypto-bot benchmark/reference

Not first core:
  Backtrader

Advanced candidate:
  NautilusTrader for future production-grade event-driven engine
```

ควรทำ spike ก่อน final:

- Spike A: strategy ง่าย ๆ ใน Freqtrade
- Spike B: strategy เดียวกันใน VectorBT
- Spike C: custom mini backtest engine เทียบผล
- Spike D: NautilusTrader minimal backtest เพื่อดู complexity

---

## 16. Strategy V1 Decision: DCA/Grid/Trend หรือ Backtest-First

### คำถาม

Research Strategy V1 decision: DCA/Grid/Trend หรือเริ่มจาก framework + backtest ก่อน

### คำตอบสรุป

ไม่ควรเลือก DCA/Grid/Trend เป็น V1 เดี่ยวโดยไม่มี backtest framework และไม่ควรเริ่มจาก framework ล้วน ๆ ที่ไม่มี strategy จริง

Recommendation:

```text
V1 = Backtest-first Strategy Harness
  + DCA baseline
  + EMA Trend baseline
  + Simple Spot Grid prototype
```

เหตุผล:

- DCA เป็น safety baseline และช่วยทดสอบ accounting/scheduler
- EMA Trend เป็น alpha baseline ที่ backtest ง่ายและจับปัญหา whipsaw ได้ดี
- Grid เป็น execution/risk stress test แต่ไม่ควร live เร็ว
- Backtest-first ช่วยตัดสินใจจากข้อมูล ไม่ใช่จากความรู้สึก

ข้อดี/ข้อเสีย:

| ตัวเลือก | ข้อดี | ข้อเสีย | ความเห็น |
|---|---|---|---|
| DCA first | ง่าย, risk ต่ำกว่า, เหมาะ spot | ไม่ใช่ alpha ชัด, แพ้ asset ลงยาว | ดีเป็น baseline |
| Grid first | เหมาะ crypto sideways/volatile | หลุดกรอบแล้วเสี่ยง, fee/fill simulation สำคัญ | ดีแต่ไม่ควรเป็น V1 เดี่ยว |
| Trend first | logic ชัด, backtest ง่าย | whipsaw ใน sideways | ดีเป็น benchmark |
| Framework + Backtest first | ลด bias, test risk rules ได้ | ยังไม่เทรดจริงทันที | ควรเป็นแกน V1 |

V1 ไม่ควรทำ:

- Futures
- Leverage
- AI trading decision
- Arbitrage live
- Multi-strategy allocation จริง
- Auto-switch strategy ด้วยเงินจริง
- Grid live โดยไม่มี range invalidation/capital cap

Implementation order:

```text
1. Data downloader + clean OHLCV
2. Backtest runner/report
3. Metrics + buy-and-hold benchmark
4. DCA baseline
5. EMA trend baseline
6. Simple spot grid backtest
7. Risk rules in backtest
8. Paper trading only
9. ตัดสินใจ live candidate จากผลลัพธ์
```

---

## 17. Validation Methodology: Monte Carlo, Data Snooping, Survivorship Bias, Drift Detection

### คำถาม

Research Validation methodology เพิ่มเติม: Monte Carlo, data snooping, survivorship bias, drift detection

### คำตอบสรุป

Validation ควรมี 4 ชั้น:

```text
Bias Checks
  -> Robustness Checks
  -> Multiple Testing Controls
  -> Live Drift Detection
```

### Monte Carlo Simulation

ใช้เพื่อดูว่า strategy ทนกับลำดับเหตุการณ์ที่แย่กว่า backtest เส้นเดียวได้ไหม

วิธีที่เหมาะกับ V1:

- Trade sequence shuffle
- Bootstrap trades with replacement
- Fee/slippage stress randomization
- Missed fill / delayed entry simulation

Metrics:

- median final equity
- 5th percentile final equity
- 95th percentile max drawdown
- worst losing streak distribution
- risk of ruin
- probability final equity < initial equity

### Data Snooping / Multiple Testing

เกิดเมื่อเราลอง strategy/parameter/เหรียญ/timeframe จำนวนมาก แล้วเลือกตัวที่รอดโดยบังเอิญ

วิธีลดปัญหา:

- Research log ของทุก variant ที่ลอง
- Parameter budget
- Holdout set ที่ล็อกไว้
- Walk-forward
- Penalized score สำหรับ strategy ที่ optimize เยอะ
- Advanced: Deflated Sharpe Ratio / PBO / CSCV

Red flags:

- Sharpe ดีเฉพาะ parameter แคบมาก
- เปลี่ยน parameter นิดเดียวผลพัง
- กำไรส่วนใหญ่มาจาก 1-2 trades
- ชนะเฉพาะ bull market
- trade count ต่ำเกินไป

### Survivorship Bias / Selection Bias

เกิดเมื่อ test เฉพาะเหรียญที่ยังรอดหรือดังในวันนี้

วิธีลด bias:

- static pairlist ต่อช่วงเวลา
- เก็บ delisted/dead pairs ถ้าหา data ได้
- แยก test group: majors, large caps, mid caps, high-vol altcoins
- liquidity filters ต้องใช้ข้อมูล ณเวลานั้น
- benchmark ต่อ asset class ที่เกี่ยวข้อง

V1 อาจเริ่ม BTC/ETH ก่อน แต่ถ้าจะ claim ใช้กับ altcoins ต้องมี survivorship-aware selection

### Drift Detection

ตรวจว่า strategy ที่เคยดีใน backtest/paper กำลังเสื่อมใน live หรือไม่

ชนิด drift:

- Data drift
- Concept drift
- Execution drift
- Performance drift

Signals:

- rolling Sharpe ลด 30-50% จาก baseline
- profit factor < 1.0 ต่อเนื่อง N trades
- win rate ลด 10-15 percentage points
- max drawdown live > backtest expected p95
- slippage > 2x backtest assumption
- fill rate ต่ำกว่า baseline
- trade frequency เปลี่ยนผิดปกติ
- market regime distribution เปลี่ยน

Validation pipeline:

```text
1. Unit/logic validation
2. Bias checks
3. Backtest
4. Robustness checks
5. Generalization tests
6. Data snooping control
7. Paper trading
8. Live gating
```

---

## 18. Operational Security Checklist

### คำถาม

Research Operational security checklist: subaccount, withdrawal whitelist, secret scanning, deployment rollback

### คำตอบสรุป

Operational security ต้องเป็น gate ก่อน live ไม่ใช่เอกสารเสริมท้ายโปรเจกต์

Baseline:

```text
Subaccount แยกทุน bot
API key แยก environment
Read + Trade only
Withdraw disabled
IP whitelist required for live
Withdrawal address whitelist enabled at account level
Secret scanning before commit/push
Deployment checklist + rollback checklist
Startup reconciliation before trading resumes
```

### Subaccount Isolation

ใช้เพื่อ:

- จำกัด worst-case loss
- แยก bot capital จาก main account
- แยก API key ต่อ bot/environment
- ลด manual trade ชนกับ bot

Checklist:

- สร้าง subaccount สำหรับ bot
- โอนเฉพาะทุนที่ยอมรับความเสี่ยงได้
- ห้าม manual trade ใน subaccount เดียวกับ bot
- ตั้ง max capital/exposure ใน config ต่ำกว่ายอดเงินจริง

### API Key / IP / Withdrawal

Checklist:

- Read enabled
- Spot trading enabled เฉพาะ live key
- Withdraw disabled
- Transfer disabled ถ้าไม่จำเป็น
- Futures/margin disabled ใน V1
- IP whitelist live key
- Rotate/review key ทุก 30-90 วัน
- Delete unused keys

Withdrawal whitelist:

- เปิด withdrawal address whitelist
- whitelist เฉพาะ trusted wallet
- เปิด new address withdrawal lock ถ้ามี
- เปิด 2FA และ anti-phishing code

### Secret Scanning

Baseline:

- `.env` local only
- `.env.example` ไม่มี secret จริง
- `.env` อยู่ใน `.gitignore`
- production secrets inject ผ่าน env/secret manager
- secret redaction ใน logs

Checklist:

- ใช้ gitleaks หรือ git-secrets เป็น pre-commit hook
- เปิด GitHub secret scanning/push protection ถ้าใช้ GitHub
- เพิ่ม custom patterns สำหรับ exchange keys
- scan repo ก่อน commit/release
- ถ้า secret เคย commit ให้ revoke/rotate ทันที

### Deployment Rollback

Pre-deploy:

- run tests/backtests
- scan secrets
- backup config + SQLite/state
- export open orders/positions
- alert deploy start
- set bot PAUSED/REDUCE_ONLY สำหรับ major deploy
- verify rollback artifact/version

Post-deploy:

- bot starts in PAUSED
- startup reconciliation ผ่าน
- local ledger == exchange state
- healthcheck ผ่าน
- Telegram/status command ตอบ
- resume entries เฉพาะเมื่อ state clean

Rollback:

```text
1. Pause new entries
2. Cancel unsafe/stale open orders ตาม policy
3. Backup current logs/state
4. Revert image/code/config
5. Restart bot in PAUSED
6. Reconcile exchange state
7. Resume only if clean
8. Write incident/deploy note
```

Final gate:

```text
ไม่มี subaccount
หรือไม่มี IP whitelist
หรือไม่มี secret scanning
หรือไม่มี rollback procedure
= ยังไม่เปิด live
```

---

## Sources Mentioned During Research

- Binance Academy: Crypto Trading Bots
- Binance Academy: Position Size
- Binance Academy: Stop-Loss / Take-Profit
- Binance Spot API Docs
- Binance WebSocket Streams
- Binance.US API Key Guide
- Binance.US Conditional Order Types
- Bybit API Docs / Rate Limit / Risk Limit / API Key Guide
- CCXT Manual
- Freqtrade Docs: Backtesting, Protections, Data Download, Telegram, Docker
- Hummingbot Docs: Architecture, Connectors, Installation, Order Lifecycle
- NautilusTrader Docs: Backtesting, Data Catalog, Execution, Positions
- QuantConnect Docs: Algorithm Engine, Walk-Forward Optimization
- OWASP Secrets Management Cheat Sheet
- OWASP Key Management Cheat Sheet
- Grafana Alerting Best Practices
- OpenTelemetry Logs
- Better Stack Alert Fatigue
- Docker Compose Docs
- systemd Docs
- Prometheus Docs
- VectorBT Docs
- Backtrader Docs
- Freqtrade Strategy / Lookahead / Recursive Analysis Docs
- GitHub Secret Scanning / Push Protection Docs
- Gitleaks / git-secrets / TruffleHog references
- Docker Compose deployment and healthcheck references
- Bailey & Lopez de Prado: Deflated Sharpe Ratio
- Bailey et al.: Probability of Backtest Overfitting
