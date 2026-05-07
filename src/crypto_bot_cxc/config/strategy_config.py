from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from crypto_bot_cxc.broker.backtest_broker import BacktestBrokerConfig
from crypto_bot_cxc.regime.detector import RegimeConfig
from crypto_bot_cxc.risk.manager import RiskConfig
from crypto_bot_cxc.strategy.ema_trend import EMATrendConfig


@dataclass(frozen=True, slots=True)
class StrategySettings:
    primary: str
    symbols: tuple[str, ...]
    timeframe: str
    fast_period: int
    slow_period: int
    warmup_period: int

    def to_ema_trend_config(self) -> EMATrendConfig:
        return EMATrendConfig(fast_period=self.fast_period, slow_period=self.slow_period)


@dataclass(frozen=True, slots=True)
class RiskSettings:
    risk_per_trade: Decimal
    atr_multiplier: Decimal
    daily_loss_limit: Decimal
    max_drawdown: Decimal
    max_open_positions: int
    capital_reserve: Decimal

    def to_risk_config(self) -> RiskConfig:
        return RiskConfig(
            risk_per_trade=self.risk_per_trade,
            max_open_positions=self.max_open_positions,
            capital_reserve=self.capital_reserve,
        )


@dataclass(frozen=True, slots=True)
class ExecutionSettings:
    default_fee_rate: Decimal
    basic_slippage_rate: Decimal
    conservative_slippage_rate: Decimal
    next_candle_execution: bool

    def to_backtest_broker_config(self, *, conservative: bool = False) -> BacktestBrokerConfig:
        slippage_rate = (
            self.conservative_slippage_rate if conservative else self.basic_slippage_rate
        )
        return BacktestBrokerConfig(
            fee_rate=self.default_fee_rate,
            slippage_rate=slippage_rate,
        )


@dataclass(frozen=True, slots=True)
class StrategyConfig:
    strategy: StrategySettings
    regime: RegimeConfig
    risk: RiskSettings
    execution: ExecutionSettings


def load_strategy_config(path: Path) -> StrategyConfig:
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, Mapping):
        raise ValueError("strategy config must be a mapping")

    return StrategyConfig(
        strategy=_load_strategy_settings(_mapping_section(payload, "strategy", required=False)),
        regime=_load_regime_config(_mapping_section(payload, "regime")),
        risk=_load_risk_settings(_mapping_section(payload, "risk")),
        execution=_load_execution_settings(_mapping_section(payload, "execution")),
    )


def _load_strategy_settings(section: Mapping[str, Any]) -> StrategySettings:
    symbols = _string_tuple(section, "symbols", default=("BTC/USDT", "ETH/USDT"))
    return StrategySettings(
        primary=_string_value(section, "primary", default="ema_trend"),
        symbols=symbols,
        timeframe=_string_value(section, "timeframe", default="1h"),
        fast_period=_int_value(section, "fast_period", default=20),
        slow_period=_int_value(section, "slow_period", default=100),
        warmup_period=_int_value(section, "warmup_period", default=100),
    )


def _load_regime_config(section: Mapping[str, Any]) -> RegimeConfig:
    return RegimeConfig(
        adx_trend_threshold=_decimal_value(section, "adx_trend_threshold"),
        adx_sideways_threshold=_decimal_value(section, "adx_sideways_threshold"),
        high_vol_multiplier=_decimal_value(section, "high_vol_multiplier"),
        squeeze_multiplier=_decimal_value(section, "squeeze_multiplier"),
        min_volume_ratio=_decimal_value(section, "min_volume_ratio"),
        max_spread_bps=_decimal_value(section, "max_spread_bps"),
    )


def _load_risk_settings(section: Mapping[str, Any]) -> RiskSettings:
    return RiskSettings(
        risk_per_trade=_decimal_value(section, "risk_per_trade"),
        atr_multiplier=_decimal_value(section, "atr_multiplier"),
        daily_loss_limit=_decimal_value(section, "daily_loss_limit"),
        max_drawdown=_decimal_value(section, "max_drawdown"),
        max_open_positions=_int_value(section, "max_open_positions"),
        capital_reserve=_decimal_value(section, "capital_reserve"),
    )


def _load_execution_settings(section: Mapping[str, Any]) -> ExecutionSettings:
    return ExecutionSettings(
        default_fee_rate=_decimal_value(section, "default_fee_rate"),
        basic_slippage_rate=_decimal_value(section, "basic_slippage_rate"),
        conservative_slippage_rate=_decimal_value(section, "conservative_slippage_rate"),
        next_candle_execution=_bool_value(section, "next_candle_execution"),
    )


def _mapping_section(
    payload: Mapping[str, Any],
    key: str,
    *,
    required: bool = True,
) -> Mapping[str, Any]:
    value = payload.get(key)
    if value is None and not required:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"config section '{key}' must be a mapping")
    return value


def _decimal_value(section: Mapping[str, Any], key: str) -> Decimal:
    value = section.get(key)
    if value is None:
        raise ValueError(f"missing decimal config value: {key}")
    decimal_value = Decimal(str(value))
    if decimal_value < 0:
        raise ValueError(f"decimal config value cannot be negative: {key}")
    return decimal_value


def _int_value(section: Mapping[str, Any], key: str, *, default: int | None = None) -> int:
    value = section.get(key, default)
    if value is None:
        raise ValueError(f"missing integer config value: {key}")
    int_value = int(value)
    if int_value <= 0:
        raise ValueError(f"integer config value must be positive: {key}")
    return int_value


def _bool_value(section: Mapping[str, Any], key: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"boolean config value is required: {key}")
    return value


def _string_value(section: Mapping[str, Any], key: str, *, default: str) -> str:
    value = section.get(key, default)
    if not isinstance(value, str) or not value:
        raise ValueError(f"string config value is required: {key}")
    return value


def _string_tuple(
    section: Mapping[str, Any],
    key: str,
    *,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    value = section.get(key, default)
    if not isinstance(value, list | tuple) or not value:
        raise ValueError(f"non-empty list config value is required: {key}")
    values = tuple(str(item) for item in value)
    if any(not item for item in values):
        raise ValueError(f"list config value cannot contain empty strings: {key}")
    return values
