# Crypto Trading Bot — Q&A Research Log

> บันทึกคำถามและคำตอบจากการ research ทั้งหมด เรียงตามลำดับการสนทนา

---

## Q1: Trading Bot Crypto มีกี่ประเภท?

**คำถาม:** ในช่วงปีนี้หรือปีที่ผ่านมา trading bot crypto มีกี่ประเภทที่น่าสนใจ มีจุดประสงค์ในการทำงานกี่แบบ และข้อดีข้อเสียของแต่ละแบบคืออะไร

**คำตอบ:** มี 7 ประเภทหลักที่น่าสนใจในปี 2025–2026

### 1. Grid Trading Bot
- **จุดประสงค์:** ทำกำไรจากความผันผวนของราคาในช่วงแคบๆ โดยวาง order ซื้อ-ขายเป็นตาราง (grid)
- **เหมาะกับ:** ตลาด Sideways / Range
- **ข้อดี:** ทำกำไรได้แม้ตลาด sideways, ตั้งค่าครั้งเดียวรันได้นาน, ควบคุม risk ได้ดี
- **ข้อเสีย:** ขาดทุนถ้าราคาหลุดออกนอก grid range, ต้องการทุนพอสมควร, ไม่เหมาะกับตลาดที่มีเทรนด์

### 2. DCA Bot (Dollar-Cost Averaging)
- **จุดประสงค์:** ลดผลกระทบจากความผันผวนด้วยการแบ่งซื้อเป็นงวดๆ สม่ำเสมอ
- **เหมาะกับ:** Bull market / Long-term hold
- **ข้อดี:** เรียบง่าย, ลด emotional trading, เริ่มต้นด้วยทุนน้อย ($50+)
- **ข้อเสีย:** ไม่ maximise กำไรในตลาดขาขึ้น, ยังขาดทุนถ้า asset ร่วงยาว

### 3. Arbitrage Bot
- **จุดประสงค์:** หาประโยชน์จากส่วนต่างราคาระหว่าง exchange
- **เหมาะกับ:** ทุกสภาวะตลาด
- **ข้อดี:** ความเสี่ยงต่ำ ไม่ต้อง predict ทิศทาง, กำไรค่อนข้าง consistent
- **ข้อเสีย:** ต้องใช้ capital สูงมาก, ส่วนต่างราคามักน้อย, ต้องการ execution speed สูง

### 4. Trend Following Bot
- **จุดประสงค์:** ใช้ technical indicator ระบุทิศทางตลาดและเปิดสถานะตาม trend
- **เหมาะกับ:** Bull / Bear trending market
- **ข้อดี:** ทำกำไรได้สูงในตลาดที่มีเทรนด์ชัด, ตัดสินใจด้วย logic
- **ข้อเสีย:** ขาดทุนใน sideways market, Lag จาก indicator

### 5. Market Making Bot
- **จุดประสงค์:** วาง bid/ask ทั้งสองฝั่งเพื่อเก็บ spread
- **เหมาะกับ:** ทุกสภาวะตลาด
- **ข้อดี:** กำไรสม่ำเสมอ, ช่วย exchange ได้ค่า rebate
- **ข้อเสีย:** เสี่ยง inventory risk, ต้องการเงินทุนสูง, ซับซ้อนมาก

### 6. AI / ML Bot
- **จุดประสงค์:** เรียนรู้รูปแบบจากข้อมูลและปรับ strategy อัตโนมัติ
- **เหมาะกับ:** ทุกสภาวะตลาด
- **ข้อดี:** ปรับตัวกับสภาวะที่เปลี่ยนได้ดี, วิเคราะห์ข้อมูลหลายมิติ
- **ข้อเสีย:** ต้องการข้อมูลและ compute สูง, เสี่ยง overfit

### 7. Portfolio Rebalancing Bot
- **จุดประสงค์:** รักษาสัดส่วน portfolio ให้คงที่อัตโนมัติ
- **เหมาะกับ:** Long-term multi-asset hold
- **ข้อดี:** ซื้อถูก-ขายแพงโดยธรรมชาติ, เหมาะกับ long-term investor
- **ข้อเสีย:** ต้องเสีย fee ทุกครั้งที่ rebalance, อาจ cut winner เร็วเกิน

**Key insight:** AI/ML Bot กำลังมาแรงในปี 2025 และ Scale ของตลาดใหญ่ขึ้นมาก Pionex มี monthly trading volume กว่า $60 billion

---

## Q2: แต่ละ bot มีเวลาเล่นของตลาดต่างกัน ต้องทำมากกว่า 1 strategy ไหม?

**คำถาม:** แต่ละ bot ก็มีเวลาเล่นของตลาดที่ต่างกัน เหมือนกับจะต้องทำมากกว่า 1 strategy เลยรึเปล่า

**คำตอบ:** ใช่ — ไม่มี bot ไหนที่ทำงานได้ดีในทุกสภาวะตลาด มี 3 แนวทาง:

### แนวทางที่ 1: Bot เดียว เน้นตลาด
- เลือก 1 bot ที่เข้ากับ style ตัวเอง
- ยอมรับว่าจะ underperform ในบาง phase
- **เหมาะกับ:** มือใหม่

### แนวทางที่ 2: คู่ Bot (แนะนำ)
- Grid 50% + Trend 30% + DCA 20%
- แต่ละ bot ทำงานอิสระ ไม่ขัดกัน
- **เหมาะกับ:** trader ที่ต้องการครอบคลุม 2 สภาวะหลัก

### แนวทางที่ 3: Multi-strategy พร้อม Market Detection
- มี logic ตรวจ phase ตลาด แล้ว activate bot ที่เหมาะสม
- ซับซ้อนมาก ต้องเขียน switching logic ให้ดี
- **เหมาะกับ:** advanced trader

---

## Q3: Bot จะรู้ได้ยังไงว่าตลาดอยู่ในสถานะไหน?

**คำถาม:** สิ่งที่สำคัญมากๆ อย่างหนึ่งก็คือบอทจะรู้ได้ยังไงว่าตอนนี้ตลาดอยู่ในสถานะไหน มีการจับแบบไหนที่น่าสนใจบ้าง และข้อดีข้อเสียของแต่ละแบบ

**คำตอบ:** มี 6 วิธีหลัก แบ่งเป็น 3 tier

### Tier 1 — เริ่มต้นได้เลย

**1. Rule-based Indicators (ADX + BBW + EMA)**
- ADX > 25 = trending, ADX < 20 = sideways
- Bollinger Band Width วัด volatility
- **ข้อดี:** เข้าใจง่าย debug ได้ทันที, ไม่ต้องการข้อมูลมาก
- **ข้อเสีย:** threshold ตายตัว ปรับตัวไม่ได้, ส่งสัญญาณผิดบ่อยช่วง transition

**2. Volatility-based (ATR / BBW)**
- วัดระดับ volatility แยก high vs low regime
- **ข้อดี:** ตรวจจับช่วงก่อน breakout ได้ดี
- **ข้อเสีย:** บอกทิศทางไม่ได้ ต้องใช้ร่วมกับ method อื่น

### Tier 2 — ต้องการความรู้ ML

**3. Hidden Markov Model (HMM)**
- ค้นหา 'สถานะซ่อนเร้น' ของตลาดโดยอัตโนมัติ
- งานวิจัยล่าสุด: 3-state model ดีกว่า 2-state สำหรับ BTC
- **ข้อดี:** ไม่ต้อง set threshold เอง, ให้ probability ของแต่ละ state
- **ข้อเสีย:** ต้อง retrain บ่อย, เป็น lagging โดยธรรมชาติ

**4. ML Classifier (XGBoost / Random Forest)**
- เทรน supervised model จาก feature หลายตัว
- **ข้อดี:** รวม feature หลายตัวพร้อมกัน, accuracy สูงถ้า label ดี
- **ข้อเสีย:** ต้องการ labeled training data ที่ดี, เสี่ยง overfit

### Tier 3 — Advanced

**5. HMM + LSTM Hybrid**
- HMM discover latent regimes, LSTM ทำนาย regime ถัดไป
- แม่นที่สุด แต่ซับซ้อนมากและต้องการ GPU

**6. Sentiment + On-chain Analysis**
- NLP วิเคราะห์ sentiment จาก social media + on-chain data
- **ข้อดี:** จับ sentiment shift ก่อนราคาเคลื่อนไหว
- **ข้อเสีย:** ต้องการ paid API ราคาแพง, noise สูงมาก

**คำแนะนำ:** เริ่มจาก Rule-based (ADX + BBW + EMA) แล้วค่อย upgrade ไป HMM

---

## Q4: Architecture ของ Bot มีแบบไหนบ้าง?

**คำถาม:** Research เรื่อง architecture ของ bot ที่น่าสนใจพร้อมบอกข้อดีข้อเสียของแต่ละแบบ

**คำตอบ:** มี 5 architecture หลัก

### 1. Monolithic (Single Process) — Tier 1
- ทุกอย่างอยู่ใน process เดียว
- **ข้อดี:** เริ่มต้นง่ายเร็ว, debug ง่าย, infrastructure น้อย
- **ข้อเสีย:** ถ้า component crash ทั้งระบบหยุด, scale แยกไม่ได้

### 2. Modular Monolith — Tier 1 (แนะนำ)
- แยก concern เป็น module ชัดเจน แต่รันใน process เดียว
- **ข้อดี:** สมดุลระหว่างความง่ายและ maintainability
- **ข้อเสีย:** ยังมี single point of failure

### 3. Event-Driven Architecture — Tier 2
- Component สื่อสารผ่าน event/message bus แบบ async
- **ข้อดี:** React ต่อ market event ทันที, fault isolation ดี
- **ข้อเสีย:** Debug ยากกว่า, ต้องการ message broker (Redis/Kafka)

### 4. Microservices Architecture — Tier 3
- แต่ละ function เป็น service อิสระ deploy แยก
- **ข้อดี:** Scale แยกได้, fault isolation ดีที่สุด
- **ข้อเสีย:** ซับซ้อนมาก, Overkill สำหรับ bot ส่วนตัว

### 5. Pipeline / Layered Architecture — Tier 1 (นิยมที่สุด)
- ข้อมูลไหลผ่าน layer เป็นลำดับ: Ingest → Feature → Regime → Signal → Risk → Execute
- **ข้อดี:** เข้าใจและ trace ง่าย, เพิ่ม/ลบ layer ได้ง่าย
- **ข้อเสีย:** ถ้า layer หนึ่งช้า ทั้ง pipeline ช้าตาม

---

## Q5: EDA กับ Microservices ต่างกันอย่างไร และ Agent คืออะไร?

**คำถาม:** Event-Driven กับ Microservices มีความคล้ายกันมาก ช่วยอธิบายความแตกต่าง และ 2 อันนี้จะคล้ายๆ การแยกการทำงานเป็น agent หลายตัวรึเปล่า

**คำตอบ:** ทั้ง 3 ตอบคนละคำถาม

| | ถามว่า | ประเภท |
|---|---|---|
| **EDA** | "component คุยกันยังไง" | Communication Pattern |
| **Microservices** | "code อยู่ที่ไหน deploy ยังไง" | Infrastructure |
| **Agent** | "unit ฉลาดแค่ไหน ตัดสินใจเองได้ไหม" | AI Layer |

- **EDA ≠ Microservices:** สามารถใช้ EDA ใน monolith ได้ และ microservices ไม่จำเป็นต้องใช้ event
- **Agent vs Microservice:** microservice เป็น "เครื่องจักรที่รันคำสั่ง" ส่วน agent เป็น "พนักงานที่รู้งาน" มีความตั้งใจและเลือก tool เองได้
- ใน production มักใช้ทั้ง 3 ร่วมกัน

---

## Q6: Risk Management มีอะไรบ้าง?

**คำถาม:** Research risk management

**คำตอบ:** มี 4 layer ที่ต้องทำพร้อมกัน

### Layer 1 — Trade Level

**Position Sizing (สำคัญที่สุด)**
- Fixed %: เสี่ยง 1-2% ต่อ trade เสมอ
- ATR-based: ปรับ size ตาม volatility ปัจจุบัน
- Kelly Criterion: คำนวณ size optimal จาก win rate (ใช้ half-Kelly)
- สูตร: `Position Size = (Capital × Risk%) ÷ (Entry - Stop Loss)`

**Stop-Loss Strategies**
- Fixed %: stop ที่ 3-5% ใต้ entry
- ATR Stop: stop ห่างจาก entry 1.5-3× ATR (แนะนำ)
- Trailing Stop: ขยับตาม price ขึ้น lock profit
- Time-based: ถ้าถือนานเกิน X ชั่วโมงแล้วไม่กำไร ออก

### Layer 2 — Session Level

**Drawdown Control & Circuit Breakers**
- Daily loss limit: หยุดถ้า loss > 3-5% ของ capital วันนั้น
- Peak drawdown limit: หยุดถ้า equity ต่ำกว่า peak > 10-15%
- Consecutive loss counter: pause หลังแพ้ N ไม้ติด
- สูตร recovery: 25% loss ต้องการ 33.3% gain / 50% loss ต้องการ 100% gain

### Layer 3 — Portfolio Level

**Portfolio-level Risk**
- Correlation guard: max 3 positions ทิศทางเดียวกันพร้อมกัน
- Capital reserve: deploy แค่ 50-70% เสมอ
- Strategy diversification: mix trend + grid ดีกว่า long bot 5 ตัว

### Layer 4 — Dynamic / AI

**Volatility-adaptive Risk**
- ATR-scaled stops: stop กว้างขึ้นเมื่อ volatile
- Volatility targeting: ลด size เมื่อ realized vol สูงกว่า target
- Drawdown scaling: ลด size เป็นขั้นบันไดเมื่อ drawdown เพิ่ม
- Regime-aware risk: ปรับ risk param ตาม market regime

**Key insight:** Strategy ที่มี win rate 60% ยังสามารถทำให้ account พังได้ถ้า position sizing ไม่ดี

---

## Q7: Backtesting มีอะไรบ้าง?

**คำถาม:** Research backtesting

**คำตอบ:** มี 3 ด้านหลักที่ต้องเข้าใจ

### วิธีการทดสอบ
1. **Simple Backtest (In-sample):** รัน strategy บน historical data เดิม — เสี่ยง overfit
2. **Walk-forward Testing (แนะนำ):** sliding window, train แล้ว test บน unseen data วนซ้ำ
3. **Monte Carlo Simulation:** สุ่ม permutation ของ trade sequence เพื่อทดสอบ robustness
4. **Paper Trading:** รัน bot กับ real-time market แต่ไม่ใช้เงินจริง

### Bias & Pitfall ที่อันตราย
- **Look-ahead Bias:** bot ใช้ข้อมูลอนาคตโดยไม่รู้ตัว (indicator repainting)
- **Overfitting:** ปรับ parameter จนดีพอดีกับ historical data — ถ้า Sharpe ลด >40% ใน out-of-sample = overfit
- **Survivorship Bias:** test แต่กับ asset ที่ยังมีชีวิตอยู่
- **Data Snooping:** ทดลอง strategy หลายร้อยแบบบน dataset เดิม
- **Transaction Cost Underestimation:** ลืมรวม fee, slippage, latency

### Transaction Cost ที่ต้องจำลอง
- Top-10 coins slippage: 0.05–0.1% / Altcoins: 0.2–0.5%
- API latency: 10-15ms (WebSocket) / 50-200ms (REST)
- **Stress test formula:** fee×2 + slippage×2 + latency 200ms → ถ้ายังกำไร = robust

### Metrics ที่ต้องดู
- Sharpe Ratio: ดี >1.0 / ดีมาก >2.0 (crypto)
- Sortino Ratio: ดีกว่า Sharpe เพราะนับแค่ downside vol
- Calmar Ratio: Annual Return / Max Drawdown (ดี >1.0)
- Profit Factor: Gross Profit / Gross Loss (ต้อง >1.5)
- Max Drawdown: ถ้า >20% ต้องถามตัวเองว่ารับไหว

### Frameworks
- **Freqtrade:** แนะนำสำหรับ crypto bot โดยเฉพาะ
- **VectorBT:** เร็วมากสำหรับ parameter sweep
- **Backtrader:** mature, event-driven
- **QuantConnect:** institutional-grade, cloud-based

---

## Q8: Data Layer & Exchange API มีอะไรบ้าง?

**คำถาม:** Research Data Layer & Exchange API

**คำตอบ:** มี 5 ด้านหลัก

### Data Layer Architecture
- แยก data layer ออกจาก strategy logic อย่างชัดเจน
- Flow: Data Sources → Normalizer → Cache → Strategy Engine
- ทำให้เปลี่ยน exchange ได้โดยไม่แตะ strategy code

### WebSocket vs REST
| | REST | WebSocket |
|---|---|---|
| Latency | 100–300ms | 10–50ms |
| Model | Pull (request/response) | Push (stream) |
| ใช้กับ | Place order, fetch balance | Price feed, order book |
| Pattern | Stateless | Persistent connection |

**Best practice:** WebSocket สำหรับ data + REST สำหรับ orders

### CCXT — Industry Standard
- รองรับ 100+ exchange ผ่าน interface เดียว
- เปลี่ยน exchange แค่เปลี่ยน 1 บรรทัด
- มี CCXT Pro สำหรับ WebSocket (paid สำหรับ commercial)

### Exchange Comparison
| Exchange | เหมาะกับ | จุดเด่น |
|---|---|---|
| Binance | ทุก strategy | Liquidity สูงสุด |
| Bybit | Derivatives | V5 API unified |
| OKX | Spot + Futures | Rate limit ผ่อนปรน |
| Kraken | Advanced algo | REST + WS + FIX |

### Data Types
- **OHLCV:** พื้นฐานสำหรับ indicator ทุกชนิด
- **Order Book:** ต้องการ WebSocket, บอก liquidity จริง
- **Trade Ticks:** precision สูง แต่ข้อมูลใหญ่มาก
- **Funding Rate:** สำคัญมากสำหรับ futures

### Error Handling
- WebSocket Reconnect + Heartbeat ทุก 30-60 วินาที
- Rate Limit Management: track weight ใช้ไป
- Data Anomaly Detection: validate ก่อนส่งให้ strategy
- Structured Logging: JSON format พร้อม timestamp

---

## Q9: Order Execution Engine มีอะไรบ้าง?

**คำถาม:** Research Order Execution Engine

**คำตอบ:** มี 6 ด้านหลัก

### Order Lifecycle
`Signal Validated → Pre-execution Check → Order Submitted → Awaiting Fill → Filled → Failed/Retry`

### Order Types
| Type | Fee | Fill Certainty | เหมาะกับ |
|---|---|---|---|
| Market | Taker (แพงกว่า) | สูงสุด | Stop-loss, urgent exit |
| Limit | Maker (ถูกกว่า) | ไม่แน่นอน | Entry/exit ที่มีเวลา |
| Stop-Limit | Taker | ปานกลาง | Stop-loss, breakout |
| IOC | Taker | Partial fill ได้ | Fast fill ที่ยอม partial |
| FOK | Taker | All or nothing | Arbitrage, atomic |
| OCO | Mix | Auto-cancel pair | TP + SL พร้อมกัน |

### Execution Algorithms (สำหรับ large orders)
- **TWAP:** แบ่งเท่าๆ กัน ส่งทุก interval — ง่าย เหมาะ low-liquidity
- **VWAP:** แบ่งตาม volume profile — เหมาะ large order ที่ต้องการ best price
- **Iceberg:** ซ่อน order size จริง auto-refill — ป้องกัน front-running

### Retry Logic & Partial Fill
- Exponential backoff: 1s → 2s → 4s → max_wait + jitter
- Client Order ID (idempotency key) ป้องกัน duplicate order
- Partial fill: ตัดสินใจว่าจะส่ง order ใหม่สำหรับส่วนที่เหลือหรือ cancel
- Order reconciliation ทุก 60 วินาที

### Slippage Control
- Max slippage tolerance: BTC/ETH 0.1-0.2%, Altcoin 0.3-0.5%
- ใช้ Limit order ก่อน เพราะ maker fee ถูกกว่า taker
- Pre-check order book depth ก่อน market order
- Post-only orders สำหรับ force maker

### Safeguards
- Kill Switch: cancel all + หยุด trading ทันที (auto + manual)
- Price Sanity Check: ราคาห่างจาก current > threshold → skip
- Order Size Cap: max 1-2% ของ portfolio per order
- Trade Frequency Limiter: max orders ต่อนาที

---

## Q10: Security มีอะไรบ้าง?

**คำถาม:** Research Security

**คำตอบ:** มี 5 ด้านหลัก

### API Key Management
- **กฎเหล็ก:** ห้าม enable withdrawal permission บน bot key เด็ดขาด
- แยก key ตามหน้าที่: bot key, dashboard key, data feed key
- Rotate key ทุก 30-90 วัน
- Monitor key usage ทุกวัน

### Permission Levels
| Permission | ความเสี่ยง | คำแนะนำ |
|---|---|---|
| Read-only | ต่ำมาก | ให้ได้ |
| Trade | ปานกลาง | ให้เฉพาะ bot ที่ต้องการ |
| Transfer | สูง | ระวัง |
| Withdraw | สูงสุด | ห้ามให้ bot เด็ดขาด |

### Secure Key Storage
- ❌ อย่าเก็บใน: codebase, GitHub, chat apps, Google Docs, browser localStorage
- ✅ เก็บใน: .env (ไม่ commit), environment variable, HashiCorp Vault, AWS Secrets Manager
- Encryption: AES-256 at rest, TLS 1.3 in transit

### IP Whitelisting & Network Security
- IP whitelist บน exchange — block >99% ของ remote attack
- VPS static IP $3-10/เดือน ทำให้ whitelist ทำงานได้จริง
- SSH key แทน password login บน server
- Firewall: เปิดเฉพาะ port 443 และ 22 (จาก specific IP)

### Code & Infrastructure Security
- ห้าม hardcode key ใน code
- ใส่ .env ใน .gitignore + ใช้ pre-commit hook (git-secrets)
- Subaccount แยกสำหรับ bot — isolate capital
- Max capital limit ใน bot config

### Incident Response Playbook
1. Revoke API key ทั้งหมดทันที
2. Enable withdrawal lock / 2FA re-auth
3. Screenshot และ log ทุก evidence
4. ติดต่อ exchange support ภายใน 1 ชั่วโมง
5. Audit trade history ย้อนหลัง 24-48 ชั่วโมง
6. หา root cause ก่อน create key ใหม่

### Security Checklist ก่อน Deploy
- [ ] ปิด withdrawal permission บน bot key
- [ ] เปิด IP whitelist
- [ ] .env ใน .gitignore
- [ ] Key เก็บใน secrets manager / .env permission 600
- [ ] เปิด withdrawal address whitelist บน exchange
- [ ] เปิด 2FA (authenticator app)
- [ ] Subaccount แยกสำหรับ bot
- [ ] Max capital limit ใน config
- [ ] SSH key แทน password

---

## Q11: Monitoring & Alerting มีอะไรบ้าง?

**คำถาม:** Research Monitoring & Alerting

**คำตอบ:** มี 6 ด้านหลัก

### 3 Pillars of Observability
- **Metrics:** "what is happening?" — P&L, win rate, drawdown, latency
- **Logs:** "what happened exactly?" — trade log, error log, order lifecycle
- **Traces:** "why did it happen?" — signal → fill latency, slow component

### Metrics ที่ต้องติดตาม

**Financial Performance:**
- P&L (realized + unrealized), Win rate, Profit factor
- Sharpe / Sortino ratio (rolling 30d), Max drawdown (real-time)
- Slippage vs backtest

**Execution Quality:**
- Order fill rate, Avg fill latency, Partial fill ratio, Retry rate

**System Health:**
- API latency (p50, p95), WebSocket uptime, CPU/Memory, Error rate

### Alert Tiers
| Tier | Action | ตัวอย่าง |
|---|---|---|
| 🔴 Critical | ภายใน 5 นาที | drawdown >15%, API key error, WebSocket down >5min |
| 🟡 Warning | ภายใน 30 นาที | fill rate <80%, slippage >2× backtest |
| 🔵 Info | Daily review | trade executed, daily P&L |
| ⚪ Silent | Log only | API request/response, heartbeat |

### Alert Channels
- **Telegram Bot:** เร็ว ฟรี แนะนำสำหรับ critical
- **Grafana Alerting:** ตั้ง threshold อัตโนมัติ
- **Email:** เหมาะกับ daily summary และ warning
- **SMS/Phone:** เฉพาะ critical-critical เท่านั้น

### Dashboard & Tools
- **เริ่มต้น:** Structured log + Telegram alert
- **Production:** Prometheus + Grafana + Loki
- **Cloud (paid):** Datadog / New Relic

### Performance Review Cadence
- **ทุกวัน:** P&L + error log (5-10 นาที)
- **ทุกสัปดาห์:** performance vs backtest baseline
- **ทุกเดือน:** rolling Sharpe, profit factor trend
- **ทุกไตรมาส:** walk-forward re-test บน data ล่าสุด

### Strategy Drift Signals
- Sharpe ลด >30% จาก baseline
- Win rate เปลี่ยน >10% โดยไม่มีเหตุผล
- Avg slippage เพิ่ม >2× จาก backtest
- Profit factor ต่ำกว่า 1.0 ต่อเนื่อง >2 สัปดาห์

---

## Q12: Deployment & Infrastructure มีอะไรบ้าง?

**คำถาม:** Research Deployment & Infrastructure

**คำตอบ:** มี 6 ด้านหลัก

### Home Computer vs VPS
- Home: ~95% uptime, dynamic IP, ไม่มี auto-restart — เหมาะแค่ development
- VPS: 99.9-99.999% uptime, static IP, auto-restart — จำเป็นสำหรับ live trading
- ราคา VPS เพียง $5-10/เดือน คุ้มมากเทียบกับ opportunity cost

### Server Location & Latency
- Home internet: 50-200ms latency (inconsistent)
- VPS ใกล้ exchange: 1-10ms
- Co-location: <1ms (HFT เท่านั้น)

**Exchange → Region ที่แนะนำ:**
- Binance EU → Frankfurt/Amsterdam
- Coinbase/Kraken US → US East (Virginia)
- Bybit/OKX → Singapore
- Binance Asia → Tokyo

### VPS Providers
| Provider | ราคา | เหมาะกับ |
|---|---|---|
| Hetzner | €4.5/mo | Binance EU, ราคาถูกสุด |
| DigitalOcean | $6/mo | มือใหม่, UI ง่าย |
| Vultr | $6/mo | Multi-exchange, 25+ locations |
| QuantVPS | $30+/mo | HFT เท่านั้น |

### Process Management & Auto-restart
- **systemd:** แนะนำสำหรับ Python — built-in Linux, stable
- **PM2:** แนะนำสำหรับ Node.js — auto-restart, log management
- **Docker --restart=always:** containerize ทั้งหมด
- **Docker Compose:** manage bot + monitoring พร้อมกัน

### Deployment Workflow
1. Manual deploy + checklist (เริ่มต้น)
2. Deploy script (bash/Makefile) — ลด human error
3. GitHub Actions CI/CD (production)
4. Blue-Green deployment (zero downtime)

**Deployment checklist:**
- [ ] รัน test suite
- [ ] Backup config และ state
- [ ] Close open positions ก่อน major change
- [ ] Deploy ช่วง low-volatility (weekend)
- [ ] ตรวจ log 5 นาทีหลัง restart
- [ ] มี rollback plan

### Recommended Stack ตาม Scale

**Starter ($5-10/mo):** Hetzner/Vultr 2GB + Ubuntu 24 + systemd + .env + Telegram alert

**Intermediate ($15-30/mo):** 4GB RAM + Docker Compose (bot + Prometheus + Grafana) + GitHub Actions

**Advanced ($50+/mo):** Multiple VPS + Blue-green deploy + Full observability stack

**HFT ($300+/mo):** Co-location + Rust/C++ + Dedicated server

**Minimum spec:**
- CPU: 2 vCPU, RAM: 2-4 GB, Storage: 20 GB SSD, OS: Ubuntu 24.04 LTS

---

*บันทึก ณ วันที่ทำ research — ข้อมูลอาจเปลี่ยนแปลงตามพัฒนาการของ ecosystem*
