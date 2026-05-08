from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from crypto_bot_cxc.broker.backtest_broker import BacktestBroker
from crypto_bot_cxc.data.feature_engine import FeatureSnapshot, build_feature_snapshots
from crypto_bot_cxc.events.models import MarketDataEvent
from crypto_bot_cxc.execution.planner import ExecutionPlanner
from crypto_bot_cxc.ledger.models import Trade
from crypto_bot_cxc.ledger.portfolio_ledger import PortfolioLedger
from crypto_bot_cxc.regime.detector import RegimeConfig, detect_regime
from crypto_bot_cxc.regime.models import RegimeState
from crypto_bot_cxc.risk.manager import RiskManager
from crypto_bot_cxc.strategy.base import BaseStrategy

RegimeProvider = Callable[[MarketDataEvent], RegimeState]


@dataclass(frozen=True, slots=True)
class EquityPoint:
    timestamp: datetime
    equity: Decimal


@dataclass(frozen=True, slots=True)
class RegimePoint:
    timestamp: datetime
    symbol: str
    state: RegimeState


@dataclass(frozen=True, slots=True)
class BacktestResult:
    trades: list[Trade]
    equity_curve: list[EquityPoint]
    final_equity: Decimal
    feature_snapshots: list[FeatureSnapshot] = field(default_factory=list)
    regime_curve: list[RegimePoint] = field(default_factory=list)
    trade_regimes: dict[UUID, RegimeState] = field(default_factory=dict)


class BacktestEngine:
    def __init__(
        self,
        *,
        strategy: BaseStrategy,
        risk_manager: RiskManager,
        planner: ExecutionPlanner,
        broker: BacktestBroker,
        ledger: PortfolioLedger,
        regime_provider: RegimeProvider,
        regime_config: RegimeConfig | None = None,
        warmup_period: int,
        atr_period: int = 14,
        adx_period: int = 14,
        bb_period: int = 20,
        bb_width_ma_period: int = 20,
        volume_ma_period: int = 20,
    ) -> None:
        if warmup_period <= 0:
            raise ValueError("warmup_period must be positive")
        self._strategy = strategy
        self._risk_manager = risk_manager
        self._planner = planner
        self._broker = broker
        self._ledger = ledger
        self._regime_provider = regime_provider
        self._regime_config = regime_config
        self._warmup_period = warmup_period
        self._atr_period = atr_period
        self._adx_period = adx_period
        self._bb_period = bb_period
        self._bb_width_ma_period = bb_width_ma_period
        self._volume_ma_period = volume_ma_period

    def run(self, candles: list[MarketDataEvent]) -> BacktestResult:
        self._strategy.reset()
        feature_snapshots = build_feature_snapshots(
            candles,
            fast_period=self._strategy.fast_period,
            slow_period=self._strategy.slow_period,
            atr_period=self._atr_period,
            adx_period=self._adx_period,
            bb_period=self._bb_period,
            bb_width_ma_period=self._bb_width_ma_period,
            volume_ma_period=self._volume_ma_period,
        )
        equity_curve: list[EquityPoint] = []
        regime_curve: list[RegimePoint] = []
        intent_regimes: dict[UUID, RegimeState] = {}
        trade_regimes: dict[UUID, RegimeState] = {}
        position_entry_regimes: dict[str, RegimeState] = {}

        for candle, features in zip(candles, feature_snapshots, strict=True):
            fills = self._broker.advance_to_candle(candle)
            for fill in fills:
                intent_regime = intent_regimes.get(fill.intent_id, RegimeState.NO_TRADE)
                if fill.side == "BUY":
                    trade_regimes[fill.intent_id] = intent_regime
                else:
                    trade_regimes[fill.intent_id] = position_entry_regimes.get(
                        fill.symbol,
                        intent_regime,
                    )

                self._ledger.on_fill(fill)

                if fill.side == "BUY":
                    position_entry_regimes.setdefault(fill.symbol, trade_regimes[fill.intent_id])
                elif self._ledger.position_quantity(fill.symbol) == 0:
                    position_entry_regimes.pop(fill.symbol, None)

            regime = self._detect_regime(candle, features)
            regime_curve.append(
                RegimePoint(
                    timestamp=candle.timestamp,
                    symbol=candle.symbol,
                    state=regime,
                )
            )

            if features.samples >= self._warmup_period:
                intents = self._strategy.on_candle(
                    candle,
                    ema_fast=features.ema_fast,
                    ema_slow=features.ema_slow,
                    regime=regime,
                )
                for intent in intents:
                    intent_regimes[intent.intent_id] = regime
                    approved = self._risk_manager.validate(
                        intent=intent,
                        portfolio_state=self._ledger.get_state(),
                        current_price=candle.close,
                    )
                    if approved is None:
                        continue
                    order = self._planner.plan(approved, market_price=candle.close)
                    self._broker.submit_order(order)

            equity_curve.append(
                EquityPoint(
                    timestamp=candle.timestamp,
                    equity=self._ledger.equity({candle.symbol: candle.close}),
                )
            )

        final_equity = equity_curve[-1].equity if equity_curve else self._ledger.get_state().cash
        return BacktestResult(
            trades=self._ledger.trades,
            equity_curve=equity_curve,
            final_equity=final_equity,
            feature_snapshots=feature_snapshots,
            regime_curve=regime_curve,
            trade_regimes=trade_regimes,
        )

    def _detect_regime(self, candle: MarketDataEvent, features: FeatureSnapshot) -> RegimeState:
        if self._regime_config is None:
            return self._regime_provider(candle)
        return detect_regime(
            adx=features.adx,
            ema_fast=features.ema_fast,
            ema_slow=features.ema_slow,
            bb_width=features.bb_width,
            bb_width_ma=features.bb_width_ma,
            volume=features.volume,
            avg_volume=features.avg_volume,
            spread=features.spread,
            config=self._regime_config,
        )
