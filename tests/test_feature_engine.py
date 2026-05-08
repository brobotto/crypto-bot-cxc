from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pandas as pd  # type: ignore[import-untyped]
import pytest

from crypto_bot_cxc.data.feature_engine import (
    build_feature_snapshots,
    calc_adx,
    calc_atr,
    calc_bb_width,
    calc_ema,
    update_ema,
)
from crypto_bot_cxc.events import MarketDataEvent


def test_update_ema_matches_pandas_ewm_adjust_false() -> None:
    closes = [Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4"), Decimal("5")]
    fast_period = 2
    slow_period = 4
    previous_fast: Decimal | None = None
    previous_slow: Decimal | None = None
    samples = 0
    fast_values: list[float] = []
    slow_values: list[float] = []

    for close in closes:
        state = update_ema(
            close=close,
            previous_fast=previous_fast,
            previous_slow=previous_slow,
            fast_period=fast_period,
            slow_period=slow_period,
            samples=samples,
        )
        previous_fast = state.fast
        previous_slow = state.slow
        samples = state.samples
        fast_values.append(float(state.fast))
        slow_values.append(float(state.slow))

    frame = pd.Series([float(close) for close in closes])

    assert fast_values == pytest.approx(frame.ewm(span=fast_period, adjust=False).mean().to_list())
    assert slow_values == pytest.approx(frame.ewm(span=slow_period, adjust=False).mean().to_list())


def test_calc_ema_matches_pandas_ewm_adjust_false() -> None:
    closes = [Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4"), Decimal("5")]
    values = [float(value) for value in calc_ema(closes, period=3)]
    expected = pd.Series([float(close) for close in closes]).ewm(span=3, adjust=False).mean()

    assert values == pytest.approx(expected.to_list())


def test_update_ema_seeds_to_first_close_and_increments_samples() -> None:
    state = update_ema(
        close=Decimal("100"),
        previous_fast=None,
        previous_slow=None,
        fast_period=10,
        slow_period=20,
        samples=5,
    )

    assert state.fast == Decimal("100")
    assert state.slow == Decimal("100")
    assert state.samples == 6


def test_update_ema_period_one_equals_latest_close() -> None:
    state = update_ema(
        close=Decimal("42"),
        previous_fast=Decimal("10"),
        previous_slow=Decimal("20"),
        fast_period=1,
        slow_period=1,
        samples=0,
    )

    assert state.fast == Decimal("42")
    assert state.slow == Decimal("42")


def test_update_ema_rejects_non_positive_period() -> None:
    with pytest.raises(ValueError, match="period must be positive"):
        update_ema(
            close=Decimal("1"),
            previous_fast=None,
            previous_slow=None,
            fast_period=0,
            slow_period=4,
            samples=0,
        )


def test_calc_atr_uses_true_range_and_wilder_smoothing() -> None:
    highs = [Decimal("10"), Decimal("12"), Decimal("13")]
    lows = [Decimal("9"), Decimal("10"), Decimal("11")]
    closes = [Decimal("9.5"), Decimal("11"), Decimal("12")]

    assert calc_atr(highs, lows, closes, period=2) == [
        Decimal("1"),
        Decimal("1.75"),
        Decimal("1.875"),
    ]


def test_calc_adx_marks_clear_trend_after_warmup() -> None:
    highs = [Decimal(value) for value in ["10", "11", "12", "13", "14", "15"]]
    lows = [Decimal(value) for value in ["9", "10", "11", "12", "13", "14"]]
    closes = [Decimal(value) for value in ["9.5", "10.5", "11.5", "12.5", "13.5", "14.5"]]

    adx = calc_adx(highs, lows, closes, period=3)

    assert adx[:3] == [Decimal("0"), Decimal("0"), Decimal("0")]
    assert adx[-1] > Decimal("50")


def test_calc_bb_width_is_zero_for_flat_prices_and_positive_for_variance() -> None:
    assert calc_bb_width([Decimal("100"), Decimal("100"), Decimal("100")], period=3) == [
        Decimal("0"),
        Decimal("0"),
        Decimal("0"),
    ]

    widths = calc_bb_width([Decimal("100"), Decimal("110"), Decimal("90")], period=3)
    assert widths[:2] == [Decimal("0"), Decimal("0")]
    assert widths[-1] > Decimal("0")


def test_feature_inputs_must_have_matching_lengths() -> None:
    with pytest.raises(ValueError, match="lengths must match"):
        calc_atr([Decimal("10")], [Decimal("9"), Decimal("8")], [Decimal("9")], period=2)


def test_build_feature_snapshots_aligns_features_to_candles() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    events = [
        MarketDataEvent(
            timestamp=start + timedelta(hours=index),
            symbol="BTC/USDT",
            open=Decimal(close),
            high=Decimal(close) + Decimal("1"),
            low=Decimal(close) - Decimal("1"),
            close=Decimal(close),
            volume=Decimal(str((index + 1) * 10)),
            timeframe="1h",
            is_closed=True,
        )
        for index, close in enumerate(["100", "102", "104", "106"])
    ]

    snapshots = build_feature_snapshots(
        events,
        fast_period=2,
        slow_period=3,
        atr_period=2,
        adx_period=2,
        bb_period=2,
        bb_width_ma_period=2,
        volume_ma_period=2,
    )

    assert len(snapshots) == len(events)
    assert snapshots[0].timestamp == events[0].timestamp
    assert snapshots[0].samples == 1
    assert snapshots[-1].samples == 4
    assert snapshots[-1].ema_fast > snapshots[-1].ema_slow
    assert snapshots[0].avg_volume == Decimal("10")
    assert snapshots[-1].avg_volume == Decimal("35")
    assert snapshots[-1].spread == Decimal("0")
