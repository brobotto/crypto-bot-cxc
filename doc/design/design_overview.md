# Crypto Trading Bot — Design Overview

> Working reference ระหว่าง implement — เปิดดูเร็ว ไม่ต้องอ่านทั้งหมด
> Detail เต็มอยู่ใน `merged_design_spec.md`

---

## Direction

สร้าง engine ที่ **backtest/paper/live ใช้ logic เดียวกัน** ไม่รีบ live

```
Backtest-first · Spot-only first · Risk-first · Ledger-centric
Modular Monolith · Event-inspired · Unified Broker Interface
```

---

## กฎเหล็ก

```
Strategy ห้ามส่ง order ตรง exchange — ต้องผ่าน Risk Manager
Position เปลี่ยนจาก FillEvent เท่านั้น — ไม่ใช่จาก Signal
Never skip reconciliation — แม้ restart 30 วินาที
Always start PAUSED ก่อน ACTIVE
Decimal ไม่ใช่ float ทุกตัวเลขเงิน
is_closed = True เท่านั้นก่อน generate signal
ห้าม hardcode threshold — ทุกค่าอยู่ใน config
ห้าม enable withdrawal permission บน bot API key
```

---

## Core Flow

```
Data → Feature Engine → Regime Detector → Strategy
  → OrderIntent → Risk Manager → ExecutionPlanner
  → BrokerInterface (BacktestBroker | PaperBroker | LiveBroker)
  → FillEvent → Portfolio Ledger → Monitoring
```

เปลี่ยนแค่ **Broker** ระหว่าง version — ทุกอย่างอื่น code เดิม

Runtime code อยู่ใต้ `src/crypto_bot_cxc/` และไฟล์ config หลักอยู่ที่ `config/strategy_config.yaml`

---

## Version Roadmap

| Version | ชื่อ | เป้าหมาย | สถานะ |
|---------|------|---------|--------|
| V0 | Design + Spikes | prove implementation path | ← ตอนนี้ |
| V1 | Backtest Core | validate strategy + engine | ⬜ |
| V2 | Paper Trading | rehearsal กับ live data | ⬜ |
| V3 | Micro Live 2-5% | real fills, small capital | ⬜ |
| V4 | Controlled Live | scale อย่างมี gate | ⬜ |
| V5 | Multi-Strategy | regime-aware routing | ⬜ |
| V6 | Advanced | futures, AI, Rust (ถ้าจำเป็น) | ⬜ |

---

## Key Decisions

| เรื่อง | ตัดสินแล้ว | หมายเหตุ |
|--------|-----------|---------|
| Market | Spot-only, long-only | Futures V6+ |
| Pairs | BTC/USDT, ETH/USDT | ไม่มี survivorship bias |
| Language | Python default V1-V5 | Rust ผ่าน framework เท่านั้นถ้าจำเป็น |
| Storage | Parquet (OHLCV) + SQLite (ledger) | — |
| Monitoring V1 | structured logs + backtest reports | Telegram/Prometheus เพิ่มใน V2+ |
| DMS | software watchdog | V2+ (V1 ไม่มี live connection) |
| Capital reserve | 40% default | ปรับได้ตาม risk budget |
| Regime thresholds | config เท่านั้น | ห้าม hardcode |
| Exchange | Binance default candidate | compare ก่อน V3 live |
| Framework | รอผล Spike A-D | Custom core เป็น primary candidate |
| Strategy V1 | EMA Trend (primary) | DCA/Grid เป็น benchmark fixtures |

---

## Regime Progression

```
V1  → tag + report (บันทึกทุก trade, ออก regime_performance.csv)
V2  → filter (NO_TRADE, spread แย่, vol สูง)
V3-V4 → risk scaler (ปรับ size/exposure ตาม regime)
V5  → strategy router (เลือก strategy จาก data ไม่ใช่ assumption)
```

---

## Open Decisions (ยังไม่ lock)

```
Framework primary path    → หลัง Spike A-D
Exchange final            → ก่อน V3 (compare Binance/OKX/Kraken)
Strategy V1 parameters    → ภายใน V1 backtest
Strategy-regime mapping   → จาก regime_performance.csv
```

---

## Next Step → V0 Spikes

ดูรายละเอียดใน `implementation_plan.md`

```
Common test spec: BTC/USDT 1h, 2022-2024, EMA 20/100, fee 0.1%
Spike A: Freqtrade     (2-3 วัน)
Spike B: VectorBT      (1-2 วัน)
Spike C: Custom mini   (3-5 วัน) ← required
Spike D: NautilusTrader (3-5 วัน)
Spike E: Jesse free    (1-2 วัน, optional)
```
