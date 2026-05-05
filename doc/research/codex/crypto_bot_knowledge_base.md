# Crypto Trading Bot Knowledge Base

เอกสารนี้จัดองค์ความรู้ที่ research มาเป็นหมวดหมู่ เพื่อใช้เป็นฐานก่อนเริ่ม design decisions หลักของ crypto trading bot

เป้าหมายของเอกสาร:

- สรุปภาพรวมทุกส่วนของ bot
- แยก concern สำคัญของระบบ
- ระบุข้อดีข้อเสียและ baseline ที่ควรเริ่ม
- เตรียมพื้นที่สำหรับตัดสินใจออกแบบจริง

---

## Executive Summary

Crypto trading bot ที่น่าใช้เงินจริงไม่ควรเริ่มจาก strategy อย่างเดียว แต่ควรออกแบบเป็นระบบที่มีชั้นสำคัญครบ:

```text
Data Layer
  -> Market Regime Detector
  -> Strategy Engine / Strategy Router
  -> Risk Manager
  -> Order Execution Engine
  -> Exchange Connector
  -> Portfolio Ledger
  -> Monitoring & Alerting
```

หลักการที่ควรยึด:

- เริ่ม spot-only ก่อน
- default เป็น paper trading
- strategy ห้ามส่ง order ตรงถึง exchange
- ทุก order ต้องผ่าน risk manager และ execution guard
- strategy code ควรใช้ร่วมกันได้ทั้ง backtest, paper, live
- architecture เริ่มเป็น modular monolith แต่มี boundary พร้อมแยก service ในอนาคต
- risk, security, monitoring ต้องเป็น core ตั้งแต่ version แรก

---

## Recommended Starting Architecture

แนวที่เหมาะที่สุดสำหรับโปรเจกต์นี้:

```text
Modular Monolith
+ Event-inspired Internal Flow
+ Backtest-first Design
+ Central Risk Manager
+ Exchange Connector Abstraction
+ Paper/Live Broker Interface
+ Microservice-ready Boundaries
```

เหตุผล:

- เริ่มได้เร็วกว่า microservices
- maintain ง่ายกว่า system กระจายหลาย process
- ได้ประโยชน์จาก event-driven flow โดยไม่แบก infrastructure หนัก
- รองรับ multi-strategy และ market regime switching ในอนาคต
- ทดสอบ backtest/paper/live ด้วย logic ใกล้กัน

High-level flow:

```text
Market Data Event
  -> Feature/Indicator Engine
  -> Regime Detector
  -> Strategy Engine
  -> Signal / OrderIntent
  -> Risk Manager
  -> Execution Engine
  -> Exchange / Paper Broker
  -> Fill Event
  -> Portfolio Ledger
  -> Monitoring / Alerts
```

---

## Bot Strategy Types

### Purpose Categories

| Purpose | Example Bots | Notes |
|---|---|---|
| Accumulation | DCA, Auto-invest | Long-term accumulation |
| Range Trading | Grid, Mean Reversion | Works best in sideways market |
| Trend Capture | Trend-following, Breakout | Works best in clear trends |
| Price Inefficiency | Arbitrage, Funding arbitrage | Execution-sensitive |
| Liquidity Provision | Market making | Advanced, inventory risk |
| Portfolio Control | Rebalancing, Hedging | Risk and allocation focused |
| Execution Optimization | TWAP, Iceberg | Improves execution, not alpha |

### Strategy Notes

- DCA: simplest and safer for long-term accumulation, but cannot protect against fundamentally bad assets
- Grid: attractive in crypto sideways volatility, but dangerous if price escapes range
- Trend-following: captures large moves, but suffers in chop
- Breakout: useful after compression, but vulnerable to fakeouts
- Mean reversion: easy to backtest, but dangerous in strong trend
- Arbitrage: conceptually low direction risk, but practically hard due to latency, fee, liquidity, and withdrawal constraints
- Market making: can produce frequent spread income, but carries high inventory and adverse selection risk
- AI/ML/Sentiment: useful as analysis layer, risky as direct execution authority

Recommended first strategy set:

```text
Version 1: DCA or simple trend/grid strategy
Version 2: Grid + Trend with regime filter
Version 3: Multi-strategy allocation
```

---

## Market Regime Detection

Market regime detection answers: what kind of market are we in now?

Core regime dimensions:

- Direction: uptrend, downtrend, sideways
- Trend strength: weak vs strong trend
- Volatility: low, normal, high
- Liquidity: healthy vs thin
- Structure: range, breakout, breakdown
- Risk state: normal vs abnormal/shock

### Detection Methods

| Method | Strength | Weakness | Recommended Use |
|---|---|---|---|
| MA Filter | Simple, explainable | Lagging | Direction filter |
| ADX | Good trend/range separation | Lagging | Trend strength |
| ATR / Realized Vol | Great for risk sizing | No direction | Position sizing, risk |
| Bollinger Width | Detects compression | No breakout direction | Breakout watch |
| Market Structure | Trader-like logic | Hard to define robustly | Range/breakout levels |
| Volume/Liquidity | Critical for live execution | Needs richer data | Trade/no-trade filter |
| Clustering | Finds hidden patterns | Harder to interpret | Research layer |
| HMM | Probabilistic regimes | Complex | Later adaptive allocation |

Recommended version 1 features:

```text
EMA 50/200
ADX
ATR percentile
Bollinger Band Width
Volume
Spread
```

Possible regime states:

```text
UPTREND_LOW_VOL
UPTREND_HIGH_VOL
DOWNTREND_LOW_VOL
DOWNTREND_HIGH_VOL
SIDEWAYS_LOW_VOL
SIDEWAYS_HIGH_VOL
BREAKOUT_WATCH
NO_TRADE
```

---

## Architecture Patterns

### Simple Loop Bot

Pros:

- Fast to build
- Easy to understand
- Good for prototype

Cons:

- Hard to scale
- Poor order lifecycle handling
- Backtest/live divergence
- Risk logic often scattered

### Layered Modular Bot

Pros:

- Clear separation of data, strategy, risk, execution
- Easy to test modules
- Good starting point

Cons:

- Needs well-defined interfaces
- Can become messy if boundaries are weak

### Event-Driven Bot

Pros:

- Realistic backtest/live flow
- Better order/fill modeling
- Natural fit for live trading

Cons:

- More complex to debug
- Requires event/state discipline

### Microservices

Pros:

- Scales well
- Services can be deployed/restarted independently
- Good for large multi-exchange systems

Cons:

- Much higher operational complexity
- Requires message broker, service monitoring, distributed state handling
- Not recommended at project start

### Agent-like Components

Agent-like component can mean a module with a role:

- MarketDataAgent
- RegimeAgent
- StrategyAgent
- RiskAgent
- ExecutionAgent
- PortfolioAgent

Important distinction:

- Agent-like component is not necessarily an AI agent
- AI agent should not directly control live order execution without rule-based guardrails

---

## Risk Management

Risk management should be a central system, not a helper inside strategies.

### Risk Layers

1. Trade-level risk
   - risk per trade
   - stop loss
   - take profit / exit rule
   - risk/reward constraints

2. Position sizing
   - fixed fractional
   - ATR/volatility adjustment
   - hard position caps

3. Portfolio-level risk
   - max exposure per symbol
   - max total exposure
   - max open positions
   - max correlated exposure

4. Drawdown and circuit breakers
   - daily loss limit
   - weekly loss limit
   - max drawdown stop
   - cooldown after loss streak

5. Execution risk
   - spread guard
   - slippage guard
   - stale price guard
   - partial fill handling

6. Leverage/futures risk
   - max leverage
   - liquidation buffer
   - reduce-only orders
   - funding-rate filter

### Recommended Baseline

```text
spot_only = true
risk_per_trade = 0.5% - 1%
max_position_per_pair = 10%
max_total_exposure = 50% - 60%
max_open_positions = 3 - 5
daily_loss_limit = 2%
max_drawdown_stop = 10%
cooldown_after_loss = enabled
spread_filter = enabled
stale_data_guard = enabled
```

---

## Backtesting

Backtesting should answer whether a strategy is worth testing forward, not prove future profit.

### Key Requirements

- causal indicators only
- no lookahead bias
- warmup period for indicators
- next-candle execution
- realistic fee/slippage
- conservative limit fill
- risk rules included
- out-of-sample testing
- walk-forward testing for optimized parameters
- benchmark comparison

### Backtest Data

Recommended first layer:

```text
OHLCV candles
1m/5m lower timeframe detail
strategy timeframe such as 1h/4h
```

Tick/order-book backtest can come later for scalping, market making, or arbitrage.

### Metrics

Required:

- total return
- net return after fees
- max drawdown
- Sharpe
- Sortino
- Calmar
- profit factor
- expectancy
- win rate
- average win/loss
- max consecutive losses
- exposure time
- fee drag
- benchmark vs buy-and-hold BTC
- performance by market regime

### Recommended Outputs

```text
trades.csv
equity_curve.csv
summary.json
monthly_returns.csv
regime_performance.csv
```

---

## Data Layer & Exchange API

### Data Types

| Data | Needed For | Priority |
|---|---|---|
| OHLCV | indicators/backtest | High |
| Ticker / bid-ask | spread/stale price | High |
| Balances | portfolio/risk | High |
| Orders/Fills | ledger/reconciliation | High |
| Exchange metadata | precision/min notional | High |
| Trades | better backtest/execution | Medium |
| Order book | slippage/market making | Medium-Later |
| Funding/Open Interest | futures/regime | Later |

### REST vs WebSocket

REST:

- load markets
- fetch balances
- create/cancel orders
- fetch open orders/fills
- reconciliation fallback

WebSocket:

- live market data
- ticker/order book updates
- private order/fill updates
- account updates

### Storage

Recommended start:

```text
Parquet: historical candles
SQLite: orders, fills, positions, balances, bot state, backtest results
YAML/JSON: config
```

Later:

```text
DuckDB: analytics over Parquet
Postgres: production multi-bot ledger
```

### Data Quality Rules

- timestamps in UTC
- no duplicate candles
- detect missing candles
- reject non-closed candles for signal generation
- detect stale live feed
- resync after WebSocket gap/disconnect

---

## Exchange Connector

Recommended strategy:

```text
Internal Exchange Interface
  -> CCXT REST Adapter
  -> Native WebSocket Adapter
```

Why:

- CCXT accelerates REST integration
- Internal interface prevents strategy from depending on CCXT directly
- Native WebSocket can be added for better live data and private streams

Required exchange checks:

```text
symbol is active
price matches tick size
amount matches step size
amount >= min amount
notional >= min notional
order type supported
rate limit respected
```

Rule:

```text
Strategy must never call exchange directly.
```

---

## Order Execution Engine

Execution engine turns approved order intent into real/paper orders safely.

### Responsibilities

- plan order
- format price/amount
- attach client order id
- validate exchange constraints
- check spread/slippage/stale price
- submit order
- track lifecycle
- handle partial fills
- cancel/replace/timeout
- reconcile with exchange
- emit order/fill events

### Lifecycle

```text
CREATED
SUBMITTED
ACCEPTED
PARTIALLY_FILLED
FILLED
CANCELED
EXPIRED
FAILED
REJECTED
```

### Required Safety Rules

- every order has clientOrderId
- retry with same clientOrderId
- query before retry after timeout
- partial fill updates position and risk
- stop/take-profit size must match actual filled size
- cancel does not assume no fill occurred
- reconcile after restart and disconnect

### Version 1 Order Support

```text
market
limit
post-only limit
stop loss
take profit
cancel/replace
```

---

## Security

Security baseline:

```text
default_mode = paper
live disabled by default
withdraw permission forbidden
IP whitelist required for live key
separate keys for read/paper/live
.env never committed
.env.example only contains field names
secret redaction in logs
central secret loader
kill switch required
startup safety checklist required
```

### API Key Rules

- read permission: allowed
- trade permission: only for live bot key
- withdrawal permission: never
- transfer permission: disabled unless explicitly needed
- separate key per environment

### Runtime Safety

- ACTIVE / HALTED / REDUCE_ONLY state
- max order notional
- max orders per minute
- daily loss limit
- emergency stop
- cancel all open orders

### Incident Response

```text
1. Halt bot
2. Cancel open orders
3. Disable/delete API key
4. Rotate key
5. Export logs/orders/fills
6. Reconcile balances
7. Review root cause
8. Restart only after state is clean
```

---

## Monitoring & Alerting

Monitoring should show whether the bot is alive, connected, synchronized, and inside risk limits.

### Monitoring Layers

- process health
- data health
- exchange health
- execution health
- portfolio/risk health
- strategy health

### Required Metrics

```text
bot_uptime_seconds
heartbeat_age_seconds
market_data_lag_seconds
websocket_reconnect_count
rest_error_count
orders_submitted_total
orders_filled_total
orders_rejected_total
open_orders_count
stuck_orders_count
current_exposure_usdt
daily_pnl_usdt
daily_drawdown_pct
max_drawdown_pct
risk_rejections_total
strategy_signals_total
```

### Important Alerts

- bot stopped
- market data stale
- exchange auth failed
- repeated rate limit
- stuck order
- unresolved partial fill
- ledger mismatch
- daily loss limit reached
- max drawdown reached
- kill switch triggered
- live mode started
- live config changed

### Recommended Version 1

```text
structured JSON logs
heartbeat
Telegram alerts
/status command
daily P&L summary
critical alerts for stale data, stuck orders, drawdown, kill switch
```

---

## Deployment & Infrastructure

### Recommended Phases

```text
Phase 1: Local dev + backtest + paper trading
Phase 2: VPS + Docker Compose
Phase 3: Hardened VPS production
Phase 4: Cloud/Kubernetes only if scale requires it
```

### Production Version 1

```text
VPS Ubuntu LTS
Docker Compose
single bot container
SQLite persistent volume
Parquet data volume
structured log volume
Telegram alerts
daily backup
startup reconciliation
restart policy: unless-stopped
```

### Infrastructure Safety

- SSH key only
- disable password login
- firewall
- non-root user
- IP whitelist exchange API key
- no withdrawal permission
- encrypted backup if secrets included

### Startup Recovery

```text
1. Load local state
2. Fetch exchange open orders
3. Fetch balances/positions
4. Reconcile fills
5. Resolve unknown orders
6. Start PAUSED or REDUCE_ONLY if mismatch
7. Resume only when state is clean
```

---

## Main Design Decisions To Make Next

ก่อนเริ่ม implement ควรตัดสินใจเรื่องหลักเหล่านี้:

1. Target exchange แรก
   - Binance, Bybit, OKX หรืออื่น ๆ

2. Market type
   - spot-only first หรือรวม futures/testnet

3. Base architecture
   - modular monolith + event-inspired flow
   - full event-driven engine ตั้งแต่แรกหรือค่อยขยาย

4. Strategy version 1
   - DCA
   - Grid
   - EMA trend
   - หรือ strategy framework ก่อน ยังไม่เลือก strategy

5. Backtest engine scope
   - OHLCV only
   - lower timeframe detail
   - conservative limit fill

6. Data storage
   - Parquet + SQLite เป็น default หรือใช้อย่างอื่น

7. Execution mode
   - paper broker ก่อน
   - live connector ทำ interface รอไว้

8. Risk baseline
   - risk per trade
   - exposure caps
   - daily loss limit
   - max drawdown
   - cooldown rules

9. Monitoring channel
   - logs only
   - Telegram
   - simple dashboard

10. Deployment target
   - local only for now
   - VPS + Docker Compose later

---

## Proposed Version Roadmap

### Version 0: Research & Design

- finalize architecture
- choose exchange
- define data models/events
- define risk rules
- define backtest assumptions

### Version 1: Backtest + Paper Core

- OHLCV data downloader
- indicator engine
- one strategy
- risk manager
- simulated broker
- portfolio ledger
- reports

### Version 2: Live Paper Trading

- live market data
- paper execution against live prices
- monitoring/alerts
- startup reconciliation for paper state

### Version 3: Controlled Live Spot

- live exchange connector
- strict risk caps
- small capital only
- Telegram alerts
- kill switch
- daily summary

### Version 4: Multi-Strategy / Regime-Aware

- regime detector
- strategy router
- capital allocation
- performance by regime

### Version 5: Advanced Execution / Futures / AI Layer

- TWAP/advanced limit execution
- futures only after risk maturity
- AI analyst layer only with rule-based execution guard

