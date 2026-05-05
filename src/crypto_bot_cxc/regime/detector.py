from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from crypto_bot_cxc.regime.models import RegimeState


@dataclass(frozen=True, slots=True)
class RegimeConfig:
    adx_trend_threshold: Decimal
    adx_sideways_threshold: Decimal
    high_vol_multiplier: Decimal
    squeeze_multiplier: Decimal
    min_volume_ratio: Decimal
    max_spread_bps: Decimal


def detect_regime(
    *,
    adx: Decimal,
    ema_fast: Decimal,
    ema_slow: Decimal,
    bb_width: Decimal,
    bb_width_ma: Decimal,
    volume: Decimal,
    avg_volume: Decimal,
    spread: Decimal,
    config: RegimeConfig,
) -> RegimeState:
    """Rule-based V1 regime detector.

    `spread` is expected as a ratio, e.g. 0.001 for 10 bps.
    """
    if spread > config.max_spread_bps / Decimal("10000"):
        return RegimeState.NO_TRADE
    if volume < avg_volume * config.min_volume_ratio:
        return RegimeState.NO_TRADE

    is_high_vol = bb_width > bb_width_ma * config.high_vol_multiplier
    is_squeeze = bb_width < bb_width_ma * config.squeeze_multiplier
    is_uptrend = adx > config.adx_trend_threshold and ema_fast > ema_slow
    is_downtrend = adx > config.adx_trend_threshold and ema_fast < ema_slow
    is_sideways = adx < config.adx_sideways_threshold

    if is_squeeze:
        return RegimeState.BREAKOUT_WATCH
    if is_uptrend:
        return RegimeState.UPTREND_HIGH_VOL if is_high_vol else RegimeState.UPTREND_LOW_VOL
    if is_downtrend:
        return RegimeState.DOWNTREND_HIGH_VOL if is_high_vol else RegimeState.DOWNTREND_LOW_VOL
    if is_sideways:
        return RegimeState.SIDEWAYS_HIGH_VOL if is_high_vol else RegimeState.SIDEWAYS_LOW_VOL
    return RegimeState.NO_TRADE

