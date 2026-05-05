from decimal import Decimal
from typing import TypedDict

from crypto_bot_cxc.regime import RegimeConfig, RegimeState, detect_regime


class RegimeKwargs(TypedDict):
    adx: Decimal
    ema_fast: Decimal
    ema_slow: Decimal
    bb_width: Decimal
    bb_width_ma: Decimal
    volume: Decimal
    avg_volume: Decimal
    spread: Decimal
    config: RegimeConfig


def cfg() -> RegimeConfig:
    return RegimeConfig(
        adx_trend_threshold=Decimal("25"),
        adx_sideways_threshold=Decimal("20"),
        high_vol_multiplier=Decimal("1.5"),
        squeeze_multiplier=Decimal("0.5"),
        min_volume_ratio=Decimal("0.3"),
        max_spread_bps=Decimal("50"),
    )


def base_kwargs() -> RegimeKwargs:
    return {
        "adx": Decimal("30"),
        "ema_fast": Decimal("110"),
        "ema_slow": Decimal("100"),
        "bb_width": Decimal("10"),
        "bb_width_ma": Decimal("10"),
        "volume": Decimal("100"),
        "avg_volume": Decimal("100"),
        "spread": Decimal("0.001"),
        "config": cfg(),
    }


def test_uptrend_low_vol() -> None:
    assert detect_regime(**base_kwargs()) == RegimeState.UPTREND_LOW_VOL


def test_uptrend_high_vol() -> None:
    kwargs = base_kwargs()
    kwargs["bb_width"] = Decimal("20")
    assert detect_regime(**kwargs) == RegimeState.UPTREND_HIGH_VOL


def test_downtrend_low_vol() -> None:
    kwargs = base_kwargs()
    kwargs["ema_fast"] = Decimal("90")
    assert detect_regime(**kwargs) == RegimeState.DOWNTREND_LOW_VOL


def test_downtrend_high_vol() -> None:
    kwargs = base_kwargs()
    kwargs["ema_fast"] = Decimal("90")
    kwargs["bb_width"] = Decimal("20")
    assert detect_regime(**kwargs) == RegimeState.DOWNTREND_HIGH_VOL


def test_sideways_low_vol() -> None:
    kwargs = base_kwargs()
    kwargs["adx"] = Decimal("15")
    assert detect_regime(**kwargs) == RegimeState.SIDEWAYS_LOW_VOL


def test_sideways_high_vol() -> None:
    kwargs = base_kwargs()
    kwargs["adx"] = Decimal("15")
    kwargs["bb_width"] = Decimal("20")
    assert detect_regime(**kwargs) == RegimeState.SIDEWAYS_HIGH_VOL


def test_breakout_watch() -> None:
    kwargs = base_kwargs()
    kwargs["bb_width"] = Decimal("4")
    assert detect_regime(**kwargs) == RegimeState.BREAKOUT_WATCH


def test_no_trade_when_spread_too_wide() -> None:
    kwargs = base_kwargs()
    kwargs["spread"] = Decimal("0.006")
    assert detect_regime(**kwargs) == RegimeState.NO_TRADE


def test_no_trade_when_volume_too_low() -> None:
    kwargs = base_kwargs()
    kwargs["volume"] = Decimal("20")
    assert detect_regime(**kwargs) == RegimeState.NO_TRADE
