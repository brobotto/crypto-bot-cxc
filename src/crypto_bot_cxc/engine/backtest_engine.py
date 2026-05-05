from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from crypto_bot_cxc.broker.backtest_broker import BacktestBroker
from crypto_bot_cxc.data.feature_engine import update_ema
from crypto_bot_cxc.events.models import MarketDataEvent
from crypto_bot_cxc.execution.planner import ExecutionPlanner
from crypto_bot_cxc.ledger.models import Trade
from crypto_bot_cxc.ledger.portfolio_ledger import PortfolioLedger
from crypto_bot_cxc.regime.models import RegimeState
from crypto_bot_cxc.risk.manager import RiskManager
from crypto_bot_cxc.strategy.ema_trend import EMATrendStrategy


@dataclass(frozen=True, slots=True)
class EquityPoint:
    timestamp: datetime
    equity: Decimal


@dataclass(frozen=True, slots=True)
class BacktestResult:
    trades: list[Trade]
    equity_curve: list[EquityPoint]
    final_equity: Decimal


class BacktestEngine:
    def __init__(
        self,
        *,
        strategy: EMATrendStrategy,
        risk_manager: RiskManager,
        planner: ExecutionPlanner,
        broker: BacktestBroker,
        ledger: PortfolioLedger,
        warmup_period: int,
    ) -> None:
        self._strategy = strategy
        self._risk_manager = risk_manager
        self._planner = planner
        self._broker = broker
        self._ledger = ledger
        self._warmup_period = warmup_period

    def run(self, candles: list[MarketDataEvent]) -> BacktestResult:
        previous_fast: Decimal | None = None
        previous_slow: Decimal | None = None
        samples = 0
        equity_curve: list[EquityPoint] = []

        for candle in candles:
            fills = self._broker.advance_to_candle(candle)
            for fill in fills:
                self._ledger.on_fill(fill)

            ema_state = update_ema(
                close=candle.close,
                previous_fast=previous_fast,
                previous_slow=previous_slow,
                fast_period=self._strategy.config.fast_period,
                slow_period=self._strategy.config.slow_period,
                samples=samples,
            )
            previous_fast = ema_state.fast
            previous_slow = ema_state.slow
            samples = ema_state.samples

            if samples >= self._warmup_period:
                intents = self._strategy.on_candle(
                    candle,
                    ema_fast=ema_state.fast,
                    ema_slow=ema_state.slow,
                    regime=RegimeState.UPTREND_LOW_VOL,
                )
                for intent in intents:
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
        )
