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

---

## External Research Cross-Check

เราเทียบกับชุด research จาก Claude แล้วพบว่า:

สิ่งที่ควรรับเข้าฐานความรู้:

- Monte Carlo simulation สำหรับ robustness
- Strategy drift monitoring
- Performance review cadence
- Pre-commit secret scanning
- Subaccount isolation
- Withdrawal address whitelist
- Deployment and rollback checklist
- Framework decision matrix

สิ่งที่ควรใช้เป็น hypothesis ไม่ใช่ decision:

- Grid + DCA เป็น default strategy แรก
- Grid 50% + Trend 30% + DCA 20% allocation
- HMM เป็น Phase 2 โดยอัตโนมัติ
- daily loss 3-5%, max drawdown 15%, risk 1% เป็นค่าถาวร
- Prometheus/Grafana/Loki ตั้งแต่ starter stack

สิ่งที่ควรระวัง:

- Arbitrage ไม่ได้ risk ต่ำเสมอ เพราะ execution/liquidity risk สูง
- AI/ML accuracy สูงไม่เท่ากับ trading profitability
- Retry แล้ว fallback เป็น market order ต้องจำกัดเฉพาะ emergency exit
- Limit order default ไม่เหมาะกับทุก urgency

---

## Framework Decision

Framework ไม่ควรเลือกจากความนิยมอย่างเดียว แต่เลือกจากบทบาท:

| Tool | Best Role | Why | Caution |
|---|---|---|---|
| Freqtrade | MVP runner / benchmark | crypto-native, backtest, dry-run, live, protections, Telegram/WebUI | ติด architecture ของ Freqtrade |
| VectorBT | Research lab | parameter sweep เร็ว, portfolio analysis ดี | ไม่ใช่ live trading engine |
| Backtrader | Learning/prototype | mature event-driven backtest concepts | crypto live support ไม่เด่น |
| NautilusTrader | Advanced production candidate | event-driven, backtest/live parity, execution model ลึก | learning curve สูง |
| Custom Engine | Primary platform candidate | คุม architecture/risk/execution ได้เต็ม | ใช้เวลามากและต้องระวัง infrastructure bugs |

Recommendation:

```text
Primary implementation:
  Custom modular monolith

Research / benchmark:
  VectorBT for fast experiments
  Freqtrade for crypto-bot workflow comparison

Advanced candidate:
  NautilusTrader spike before production-grade event engine

Not first core:
  Backtrader
```

Recommended spikes:

```text
Spike A: Freqtrade simple strategy + backtest/dry-run
Spike B: VectorBT same strategy + parameter sweep
Spike C: Custom mini backtest engine
Spike D: NautilusTrader minimal backtest
```

---

## Strategy V1 Decision

Do not choose DCA/Grid/Trend as a single V1 before the backtest harness exists.

Recommended V1:

```text
Backtest-first Strategy Harness
  + DCA baseline
  + EMA Trend baseline
  + Simple Spot Grid prototype
```

Roles:

- DCA baseline: conservative benchmark, tests accounting and scheduler
- EMA Trend baseline: simple alpha benchmark, tests trend logic and whipsaw behavior
- Spot Grid prototype: execution/risk stress test, not live-first

V1 should not include:

- futures
- leverage
- AI trading decisions
- live arbitrage
- true multi-strategy allocation
- auto-switch strategy with real money
- live grid without range invalidation and capital cap

Implementation order:

```text
1. Data downloader + clean OHLCV
2. Backtest runner/report
3. Metrics + buy-and-hold benchmark
4. DCA baseline
5. EMA trend baseline
6. Simple spot grid backtest
7. Risk rules applied in backtest
8. Paper trading only
9. Choose live candidate from evidence
```

---

## Validation Methodology

Validation should prevent us from trusting a beautiful but fragile backtest.

Core pipeline:

```text
Bias Checks
  -> Robustness Checks
  -> Multiple Testing Controls
  -> Paper/Live Drift Detection
```

### Monte Carlo

Use trade logs to simulate alternative outcome paths.

Methods:

- trade sequence shuffle
- bootstrap trades with replacement
- fee/slippage stress randomization
- missed fill / delayed entry simulation

Metrics:

```text
median final equity
5th percentile final equity
95th percentile max drawdown
worst losing streak distribution
risk of ruin
probability final equity < initial equity
```

Rule:

```text
Monte Carlo robustness is mandatory for every strategy candidate.
```

### Data Snooping

Data snooping happens when many strategies/parameters/assets/timeframes are tested and only winners are remembered.

Controls:

- research log of every variant
- parameter budget before optimization
- locked holdout set
- walk-forward testing
- parameter sensitivity heatmaps
- optional Deflated Sharpe Ratio / PBO / CSCV for heavy optimization

Red flags:

- performance survives only in a narrow parameter range
- profit comes from 1-2 trades
- works only in bull market
- trade count is too low
- out-of-sample Sharpe collapses

### Survivorship / Selection Bias

Crypto-specific risk: testing only coins that survived to today.

Controls:

- start with BTC/ETH for V1 honesty
- use historical/static pairlists for altcoin research
- include delisted/dead pairs if available
- use historical liquidity filters, not current volume rankings
- benchmark by asset class

### Drift Detection

Track degradation from backtest/paper baseline.

Types:

- data drift
- concept drift
- execution drift
- performance drift

Signals:

```text
rolling Sharpe down 30-50%
profit factor < 1.0 for N trades
win rate down 10-15 percentage points
live drawdown > backtest p95
slippage > 2x assumption
fill rate below baseline
trade frequency abnormal
regime distribution changed
```

Actions:

```text
Warning: reduce position size
Critical: pause new entries
Emergency: halt or reduce-only
Review: rerun walk-forward
Retire: remove strategy if drift persists
```

---

## Operational Security Checklist

Operational security is a live gate.

```text
No subaccount
or no IP whitelist
or no secret scanning
or no rollback procedure
= no live trading
```

### Subaccount

```text
[ ] dedicated bot subaccount
[ ] only risk capital transferred
[ ] no manual trading in bot subaccount
[ ] API key scoped to subaccount
[ ] config max capital lower than actual balance
```

### API Key / Account Controls

```text
[ ] read enabled
[ ] spot trade enabled only for live key
[ ] withdrawal disabled
[ ] transfer disabled unless necessary
[ ] futures/margin disabled in V1
[ ] IP whitelist enabled for live key
[ ] unused keys deleted
[ ] key review/rotation every 30-90 days
[ ] withdrawal address whitelist enabled
[ ] 2FA enabled
[ ] anti-phishing code enabled if exchange supports it
```

### Secret Scanning

```text
[ ] .env and .env.* ignored
[ ] .env.example contains no real secrets
[ ] logs redact secrets
[ ] pre-commit scanner: gitleaks/git-secrets/trufflehog
[ ] GitHub secret scanning / push protection if using GitHub
[ ] custom patterns for exchange keys
[ ] leaked secret means revoke/rotate immediately
```

### Deployment Rollback

Pre-deploy:

```text
[ ] tests/backtests pass
[ ] secret scan pass
[ ] config + SQLite/state backup
[ ] open orders/positions exported
[ ] deploy starts PAUSED or REDUCE_ONLY for major changes
[ ] rollback artifact/version ready
```

Post-deploy:

```text
[ ] startup reconciliation passes
[ ] local ledger == exchange state
[ ] healthcheck passes
[ ] alert/status command works
[ ] no repeated auth/rate-limit/order errors
[ ] resume entries only when clean
```

Rollback:

```text
1. Pause new entries
2. Cancel unsafe/stale open orders by policy
3. Backup current logs/state
4. Revert image/code/config
5. Restart in PAUSED
6. Reconcile exchange state
7. Resume only if clean
8. Write incident/deploy note
```

---

## Claude V2 Cross-Check

Useful additions from Claude v2:

- Portfolio Ledger & Accounting as a first-class core system
- Decimal arithmetic for all money, price, and quantity values
- Startup Recovery & Reconciliation state machine
- `last_fill_timestamp` as a critical persisted field
- Graceful shutdown policy such as `KEEP_STOPS`
- Backtest-Live Unified Design via Broker Interface
- Core event models: `MarketDataEvent`, `OrderIntent`, `FillEvent`
- Performance tracking per regime

Use as hypothesis, not final decision:

- V1 as Grid or Trend only
- Freqtrade/Jesse as backtesting default
- Prometheus/Grafana/Loki in early V1
- fixed calibration targets such as Live Sharpe >= 60% of backtest Sharpe

---

## Jesse Framework

Jesse is a crypto-first Python framework for research, backtesting, optimization, paper/live trading, and strategy development.

Best uses:

- strategy spike
- Monte Carlo validation reference
- unified workflow study
- compare strategy results with Freqtrade/custom

Avoid relying on Jesse yet for:

- final live execution engine
- accounting ledger source of truth
- custom reconciliation policy
- AI/ML production authority

Why it is interesting:

- unified strategy workflow
- built-in Monte Carlo: trade-order shuffling and candles-based
- strategy syntax is simple
- self-hosted

Cautions:

- live/paper exchange support can be paid-tier dependent
- production feature access may differ from open-source core
- live reconciliation depth must be verified
- framework lock-in is real

---

## FinRL-X Deployment Gaps

FinRL-X proposes deployment consistency across research/backtest/paper/live. It is not a crypto bot framework, but the "two gaps" model is useful.

### Backtest To Paper Gap

Causes:

- instant fill at bar price
- unrealistic transaction cost model
- no market impact
- no order book dynamics
- survivorship bias
- historical feed differs from live feed

Mitigations:

- realistic fill model
- fee/slippage stress
- no lookahead
- same data schema
- benchmark comparison

### Paper To Live Gap

Causes:

- latency
- partial fills
- real slippage
- queue/liquidity effects
- API behavior
- server crash/disconnect
- state recovery failure
- flash crash or bad deployment

Mitigations:

- reconciliation
- startup recovery
- partial fill handling
- kill switch
- small capital start
- deployment rollback

Design implication:

- weight-centric interface is useful for DCA/rebalancing/target exposure
- grid still needs order-level engine
- our event/order/fill model remains necessary

---

## Calibration Targets

Calibration target should be a multi-metric drift system, not a single hard threshold.

Metrics:

- equity curve divergence
- return retention
- Sharpe retention
- drawdown inflation
- actual vs modeled slippage
- actual vs modeled fees
- fill rate
- latency
- expected trades vs actual trades
- win rate / profit factor drift

Suggested interpretation:

```text
Good:
  live/paper Sharpe >= 70% of conservative backtest

Acceptable / Watch:
  50-70%

Warning:
  30-50%

No-go / Pause:
  < 30% or drawdown exceeds backtest p95
```

Backtest to paper gates:

```text
Trade match rate >= 90% for signal-level strategies
Paper slippage within 0.5x-2.0x modeled slippage
Paper fee error < 5%
Paper fill rate within 10-20% of assumption
Paper max drawdown <= Monte Carlo p95
```

Paper to small live gates:

```text
Live slippage <= 2x paper slippage
Live fee error < 5%
Order reject rate < 1-2%
Unexpected position = 0 tolerance
Critical unresolved ledger mismatch = 0
Live drawdown <= expected p95
```

Rule:

```text
Paper/live should stay inside the conservative backtest + Monte Carlo envelope.
```

---

## Reconciliation Frequency

Reconciliation should be hybrid:

```text
private WebSocket = primary real-time state updates
REST = periodic audit and fallback
trigger-based full reconcile on suspicious events
```

Recommended V1 frequencies:

| Task | Frequency |
|---|---:|
| Private WS processing | real-time |
| Heartbeat/staleness check | 10-30s |
| Query after submit/cancel timeout | immediate |
| Open orders reconcile | 60-120s active |
| Balance reconcile | 2-5m active |
| Missing fills since last_seen | 5-10m |
| Full reconciliation | 15-30m active |
| Startup reconciliation | every startup before ACTIVE |
| Post-disconnect reconciliation | immediately after reconnect |
| EOD audit | daily |

Idle mode:

```text
open_orders = every 5-15m
balance = every 10-30m
full reconcile = hourly
```

Rate-limit rule:

```text
normal reconciliation uses <= 5-10% of REST budget
never operate near exchange rate limit
honor retry/rate-limit headers
backoff immediately on rate-limit errors
```

---

## Shutdown Policy

Default shutdown policy should be context-aware.

Policy types:

| Policy | Behavior | Use |
|---|---|---|
| KEEP_STOPS | cancel entries/grid, keep protective stop/TP | normal deploy/restart |
| CANCEL_ALL_ORDERS | cancel all open orders, leave positions | unknown order state/crash |
| FLATTEN_AND_CANCEL | cancel orders and close positions | emergency/security/risk breach |
| REDUCE_ONLY | no new entries, exits only | wind-down/post-incident |
| KEEP_ALL | leave all orders | almost never |

Default graceful shutdown:

```text
1. Set state = PAUSED
2. Stop new signals/orders
3. Wait for in-flight operations briefly
4. Cancel entry/grid/stale limit orders
5. Keep verified exchange-side protective stop-loss/take-profit
6. Save state: open positions, pending orders, last_fill_timestamp
7. Alert shutdown summary
```

Rule:

```text
Default = KEEP_STOPS only for verified exchange-side protective orders.
Unknown state = PAUSED + reconcile.
Emergency = CANCEL_ALL_ORDERS or FLATTEN_AND_CANCEL by severity.
```

Use dead man's switch if an exchange supports it, but remember it cancels orders and does not close positions.

---

## Portfolio Ledger & Accounting Deep Dive

Portfolio Ledger is an internal state authority for risk, P&L, recovery, reconciliation, and attribution.

Components:

- Position Manager
- Order Ledger
- Fill / Trade Ledger
- Balance Tracker
- Fee Ledger
- P&L Calculator
- Reconciliation Engine
- Performance Attribution

Core rule:

```text
Position changes only from Fill events, never from Signals.
```

V1 decisions:

```text
Market:
  spot-only, long-only

Position model:
  netting per account + strategy + symbol

Numeric type:
  Decimal for money, price, quantity

Persistence:
  SQLite operational ledger
  append-only ledger_events + current state tables

PnL:
  weighted average cost
  net realized P&L including allocated fees
  unrealized gross + estimated net

Fees:
  store original fee currency
  convert to quote/base reporting currency
  base-fee reduces net quantity

Reconciliation:
  exchange current state wins inventory
  internal audit trail is never discarded
  adjustment events required
```

Schema V1:

```text
orders
fills
positions
position_snapshots
balances
fee_events
portfolio_snapshots
reconciliation_runs
ledger_events
```

Edge cases:

- partial fill + scale-in
- fill during downtime
- dust position
- fee in base currency
- cancel/fill race condition
- multi-fill per order

---

## Startup Recovery & Reconciliation Deep Dive

Startup recovery is a state machine and policy engine.

State machine:

```text
BOOTING
  -> PREFLIGHT
  -> CONNECTING
  -> RECONCILING
  -> PAUSED
  -> ACTIVE
  -> REDUCE_ONLY
  -> HALTED
```

Rule:

```text
Never enter ACTIVE directly from BOOTING.
```

Startup sequence:

```text
1. Load config and safety mode
2. Open DB and acquire single-bot lock
3. Load persisted state
4. Connect exchange REST
5. Load exchange metadata
6. Fetch exchange open orders
7. Fetch exchange balances
8. Fetch fills since last_fill_timestamp - safety lookback
9. Rebuild/verify ledger from missing fills
10. Reconcile orders
11. Reconcile positions and balances
12. Classify drift severity
13. Set mode: PAUSED / ACTIVE / REDUCE_ONLY / HALTED
14. Alert startup summary
```

Policies:

- Missing fill: apply fill event, update ledger, alert
- Orphan order: adopt only if bot clientOrderId recognized; otherwise cancel non-protective and PAUSED
- Ghost order: query by id/clientOrderId, fetch nearby fills, mark unknown only after evidence
- Inflight timeout: query first, never submit duplicate
- Balance drift: dust/small adjust with event, medium PAUSED, large HALTED

V1 decisions:

```text
Always start RECONCILING then PAUSED
Exchange wins current inventory
Ledger preserves audit/attribution
Auto resume disabled by default
Single instance lock required
Startup + post-disconnect + trigger + periodic reconciliation
```

---

## Unified Broker Design

Unified broker design keeps Strategy, Risk, and Ledger stable across backtest/paper/live.

Flow:

```text
MarketDataEvent
  -> Feature/Indicator Engine
  -> Regime Detector
  -> Strategy
  -> OrderIntent
  -> Risk Manager
  -> BrokerInterface
  -> OrderEvent / FillEvent
  -> Portfolio Ledger
  -> Monitoring
```

Broker interface groups:

```text
Commands:
  submit_order
  cancel_order
  replace_order

Queries:
  get_order
  get_open_orders
  get_balances
  get_fills_since

Events:
  OrderAccepted
  OrderRejected
  OrderCanceled
  OrderExpired
  FillReceived
  BalanceUpdated
```

Modes:

- BacktestBroker: deterministic simulation with fill model, fees, slippage
- PaperBroker: live market data with simulated fills, latency/spread/slippage
- LiveBroker: real exchange, private WS, REST fallback, idempotency, reconciliation

Capability flags:

```text
supports_post_only
supports_stop_loss
supports_oco
supports_server_side_stop
supports_reduce_only
supports_dead_man_switch
supports_replace_order
supports_private_ws
```

V1 order:

```text
BacktestBroker first
PaperBroker second
LiveBroker only after ledger/reconciliation stable
All modes emit same event types
Every event persisted to ledger_events
```

---

## Jesse Framework Comparison

Updated framework role matrix:

```text
Primary architecture:
  Custom modular monolith + BrokerInterface

Research benchmark tools:
  VectorBT: fast parameter sweep
  Jesse: strategy workflow + Monte Carlo validation spike
  Freqtrade: mature crypto bot runner benchmark

Production reference:
  NautilusTrader: event-driven execution/reconciliation model
```

Jesse is useful because:

- crypto-first
- simple strategy syntax
- built-in Monte Carlo
- unified workflow direction

Cautions:

- live/paper exchange support can be paid-tier dependent
- execution model needs verification
- ledger/reconcile depth needs verification
- framework lock-in risk

Conclusion:

```text
Jesse = serious research/validation spike candidate
not production core yet
```

---

## Claude V3 Cross-Check

Useful additions from Claude v3:

- full validation pipeline with explicit gates
- pre-registration, research log, parameter budget
- survivorship bias policy for crypto
- drift detection separated into Data, Execution, Concept, Performance
- action tiers: Watch, Warning, Critical, Emergency, Retire
- framework spike plan using same strategy/data/metrics

Use with caution:

- statistical claims need source verification
- DSR/PBO thresholds are heuristics
- Freqtrade as default should wait for spike evidence
- first 90 live days as baseline may be noisy if trade count is low

---

## DSR / PBO / CSCV

Purpose:

```text
Detect whether the selected strategy is likely a winner chosen from too many trials.
```

Required data:

```text
returns_matrix:
  rows = timestamps
  columns = strategy variants / parameter sets
```

### DSR

Deflated Sharpe Ratio adjusts raw Sharpe for:

- multiple testing / selection bias
- non-normal returns
- short sample length
- dispersion of Sharpes across trials

Inputs:

```text
selected_returns
observed_sharpe
all_variant_sharpes or number_of_trials
number_of_observations
skewness
kurtosis
effective_number_of_trials
```

### PBO / CSCV

CSCV procedure:

```text
1. Split timeline into folds
2. Use half as in-sample, half as out-of-sample
3. Pick best in-sample variant
4. Rank that variant out-of-sample
5. Convert rank to logit
6. PBO = share of splits where OOS rank is below median
```

Heuristic thresholds:

```text
DSR / PSR:
  > 0.95 strong
  0.80-0.95 interesting
  < 0.80 weak

PBO:
  < 10-20% promising
  20-40% fragile
  > 40-50% likely overfit
```

Implementation roadmap:

```text
V1:
  research_log
  returns_matrix export
  PSR vs 0 and empirical SR threshold
  simple CSCV/PBO
  parameter sensitivity heatmap

V1.5:
  DSR
  effective trial count
  CSCV logit-rank histogram
  PBO report

V2:
  DSR/PBO by regime and strategy family
```

---

## Drift Threshold Calibration

Thresholds should come from:

```text
reference baseline
expected variability
action cost
```

Sample-size rules:

```text
< 30 trades:
  Watch only for performance metrics

30-50 trades:
  Warning possible, avoid retirement

50-100 trades:
  Critical allowed with multi-signal confirmation

100+ trades:
  full drift tiering more meaningful
```

Candidate thresholds:

```text
Data Drift:
  ws_lag > 10s = Warning
  ws_lag > 30s = Critical / PAUSED
  spread > 2x baseline for 5m = Warning
  spread > 3x baseline = Pause entries

Execution Drift:
  slippage > 2x modeled over 20+ fills = Warning
  slippage > 3x modeled = Critical
  fill_rate < baseline - 20pp over 30+ orders = Warning
  order_reject_rate > 2% = Critical
  unexpected position = Emergency

Performance Drift:
  PF < 1.1 over 50+ trades = Warning
  PF < 1.0 over 50+ trades = Critical
  expectancy < 0 over 50+ trades = Critical
  live drawdown > Monte Carlo p95 = Emergency
```

Rule:

```text
Hard risk/state violations bypass statistics.
Performance drift requires minimum sample size and multi-signal confirmation.
```

---

## Framework Spike Plan

Common test spec:

```text
Symbol: BTC/USDT
Timeframe: 1h
Period: 2022-01-01 to 2024-12-31
Initial capital: 10,000 USDT
Market type: spot, long-only
Strategy: EMA crossover
Fast EMA: 20
Slow EMA: 100
Fee: 0.1%
Slippage: 0.05% basic, 0.1% conservative
Execution: next candle open
Benchmark: buy-and-hold BTC
```

Spikes:

```text
Spike A: Freqtrade, 2-3 days
Spike B: VectorBT, 1-2 days
Spike C: Custom Mini Engine, 3-5 days
Spike D: NautilusTrader, 3-5 days
Optional E: Jesse, 1-2 days
```

Required outputs:

```text
setup_notes.md
strategy_code/
backtest_summary.json
trades.csv
equity_curve.csv
orders_or_fills.csv
benchmark_comparison.json
limitations.md
time_spent.md
decision_notes.md
```

Decision:

```text
Primary core:
  Freqtrade vs Custom vs Nautilus

Research lab:
  VectorBT likely useful regardless

Validation helper:
  Jesse if Monte Carlo/export is strong
```

---

## Order Type To Signal Urgency Mapping

Strategy should emit urgency, not raw order type.

Urgency enum:

```text
PASSIVE
NORMAL
TIME_SENSITIVE
URGENT_EXIT
EMERGENCY
ATOMIC
PROTECTIVE
```

Mapping:

| Urgency | Example | Order Type |
|---|---|---|
| PASSIVE | grid entry, slow rebalance | post-only limit / limit GTC |
| NORMAL | EMA entry, DCA buy | limit near bid/ask with timeout |
| TIME_SENSITIVE | breakout, regime switch | limit IOC / aggressive limit |
| URGENT_EXIT | stop condition, risk reduce | market / IOC limit |
| EMERGENCY | kill switch, critical risk | market exit / flatten by policy |
| ATOMIC | arbitrage leg | FOK limit |
| PROTECTIVE | stop-loss, take-profit | exchange-side stop/TP/OCO |

V1 rules:

```text
DCA / EMA entry:
  NORMAL -> limit near best bid/ask with timeout
  fallback skip, not market chase

Grid entry:
  PASSIVE -> post-only limit if supported
  cancel if range/regime invalidated

Trend exit:
  NORMAL/TIME_SENSITIVE -> limit IOC or market depending slippage

Stop loss:
  PROTECTIVE/URGENT_EXIT -> exchange-side stop-market if supported

Kill switch:
  EMERGENCY -> cancel entries, then market/IOC exit only if policy says flatten
```

ExecutionPlanner chooses order type using:

- urgency
- liquidity/spread/slippage
- risk state
- position state
- exchange capabilities

---

## Paper Broker Implementation

PaperBroker is a live deployment rehearsal layer, not just BacktestBroker with live prices.

It shares:

```text
BrokerInterface
events
RiskManager
PortfolioLedger
```

It simulates:

- virtual balances
- open orders
- order lifecycle
- market/limit/stop fills
- fees
- spread
- slippage
- latency
- partial fills
- order timeout
- precision/min notional

Fill models:

```text
Market buy = ask * (1 + slippage + impact)
Market sell = bid * (1 - slippage - impact)

Limit buy fills if ask <= limit_price
Limit sell fills if bid >= limit_price

Post-only buy cancels/rejects if price >= current ask
Post-only sell cancels/rejects if price <= current bid
```

Latency model:

```text
signal_time
submit_time = signal_time + decision_latency + network_latency
ack_time = submit_time + exchange_ack_latency
fill_eligible_after = ack_time
```

V1 scope:

```text
Live ticker/bookTicker input
Virtual balances
Market + limit + post-only + stop-market simulation
GTC/IOC/FOK basics
Fee model
Spread/slippage model
Order timeout
Partial fill by volume cap
Ledger integration
Startup recovery test
Telegram/status alerts
Execution quality export
```
