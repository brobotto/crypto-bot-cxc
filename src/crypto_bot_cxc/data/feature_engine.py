from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from crypto_bot_cxc.events.models import MarketDataEvent


@dataclass(frozen=True, slots=True)
class EmaState:
    fast: Decimal
    slow: Decimal
    samples: int


@dataclass(frozen=True, slots=True)
class FeatureSnapshot:
    timestamp: datetime
    symbol: str
    ema_fast: Decimal
    ema_slow: Decimal
    atr: Decimal
    adx: Decimal
    bb_width: Decimal
    bb_width_ma: Decimal
    volume: Decimal
    avg_volume: Decimal
    spread: Decimal
    samples: int


def update_ema(
    *,
    close: Decimal,
    previous_fast: Decimal | None,
    previous_slow: Decimal | None,
    fast_period: int,
    slow_period: int,
    samples: int,
) -> EmaState:
    fast = _next_ema(close=close, previous=previous_fast, period=fast_period)
    slow = _next_ema(close=close, previous=previous_slow, period=slow_period)
    return EmaState(
        fast=fast,
        slow=slow,
        samples=samples + 1,
    )


def calc_ema(prices: Sequence[Decimal], *, period: int) -> list[Decimal]:
    """Return recursive EMA values equivalent to pandas ewm(adjust=False)."""
    _validate_period(period)
    values: list[Decimal] = []
    previous: Decimal | None = None
    for price in prices:
        previous = _next_ema(close=price, previous=previous, period=period)
        values.append(previous)
    return values


def calc_atr(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    *,
    period: int,
) -> list[Decimal]:
    """Return Wilder-smoothed Average True Range values."""
    _validate_period(period)
    _validate_equal_lengths(highs=highs, lows=lows, closes=closes)
    return _wilder_smooth(_true_ranges(highs, lows, closes), period=period)


def calc_adx(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
    *,
    period: int,
) -> list[Decimal]:
    """Return Wilder-smoothed Average Directional Index values.

    The first `period` values are forced to zero; ADX is most reliable after
    roughly `2 * period` samples, so engine warmup should exceed that.
    """
    _validate_period(period)
    _validate_equal_lengths(highs=highs, lows=lows, closes=closes)
    if not highs:
        return []

    true_ranges = _true_ranges(highs, lows, closes)
    plus_dm, minus_dm = _directional_movements(highs, lows)
    smoothed_tr = _wilder_smooth(true_ranges, period=period)
    smoothed_plus = _wilder_smooth(plus_dm, period=period)
    smoothed_minus = _wilder_smooth(minus_dm, period=period)

    dx_values: list[Decimal] = []
    for true_range, plus, minus in zip(
        smoothed_tr,
        smoothed_plus,
        smoothed_minus,
        strict=True,
    ):
        if true_range <= 0:
            dx_values.append(Decimal("0"))
            continue
        plus_di = plus / true_range * Decimal("100")
        minus_di = minus / true_range * Decimal("100")
        denominator = plus_di + minus_di
        if denominator <= 0:
            dx_values.append(Decimal("0"))
            continue
        dx_values.append(abs(plus_di - minus_di) / denominator * Decimal("100"))

    adx_values = _wilder_smooth(dx_values, period=period)
    return [
        Decimal("0") if index < period else value
        for index, value in enumerate(adx_values)
    ]


def calc_bb_width(
    closes: Sequence[Decimal],
    *,
    period: int,
    std_multiplier: Decimal = Decimal("2"),
) -> list[Decimal]:
    """Return Bollinger Band width as (upper - lower) / middle."""
    _validate_period(period)
    if std_multiplier <= 0:
        raise ValueError("std_multiplier must be positive")

    widths: list[Decimal] = []
    for index in range(len(closes)):
        if index + 1 < period:
            widths.append(Decimal("0"))
            continue
        window = closes[index + 1 - period : index + 1]
        mean = _mean(window)
        if mean <= 0:
            widths.append(Decimal("0"))
            continue
        variance = _mean([(value - mean) ** 2 for value in window])
        std_dev = variance.sqrt()
        widths.append((Decimal("2") * std_multiplier * std_dev) / mean)
    return widths


def build_feature_snapshots(
    events: Sequence[MarketDataEvent],
    *,
    fast_period: int,
    slow_period: int,
    atr_period: int = 14,
    adx_period: int = 14,
    bb_period: int = 20,
    bb_width_ma_period: int = 20,
    volume_ma_period: int = 20,
    spread: Decimal = Decimal("0"),
) -> list[FeatureSnapshot]:
    """Precompute per-candle feature snapshots without looking past each index.

    Backtests without bid/ask data use spread=0, so spread-based NO_TRADE
    filtering is intentionally inactive until richer market data is available.
    """
    closes = [event.close for event in events]
    highs = [event.high for event in events]
    lows = [event.low for event in events]
    volumes = [event.volume for event in events]

    ema_fast = calc_ema(closes, period=fast_period)
    ema_slow = calc_ema(closes, period=slow_period)
    atr = calc_atr(highs, lows, closes, period=atr_period)
    adx = calc_adx(highs, lows, closes, period=adx_period)
    bb_width = calc_bb_width(closes, period=bb_period)
    bb_width_ma = _rolling_mean(bb_width, period=bb_width_ma_period)
    avg_volume = _rolling_mean(volumes, period=volume_ma_period)

    snapshots: list[FeatureSnapshot] = []
    for index, event in enumerate(events):
        snapshots.append(
            FeatureSnapshot(
                timestamp=event.timestamp,
                symbol=event.symbol,
                ema_fast=ema_fast[index],
                ema_slow=ema_slow[index],
                atr=atr[index],
                adx=adx[index],
                bb_width=bb_width[index],
                bb_width_ma=bb_width_ma[index],
                volume=event.volume,
                avg_volume=avg_volume[index],
                spread=spread,
                samples=index + 1,
            )
        )
    return snapshots


def _next_ema(*, close: Decimal, previous: Decimal | None, period: int) -> Decimal:
    _validate_period(period)
    if previous is None:
        return close

    alpha = Decimal("2") / Decimal(period + 1)
    return close * alpha + previous * (Decimal("1") - alpha)


def _true_ranges(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
    closes: Sequence[Decimal],
) -> list[Decimal]:
    ranges: list[Decimal] = []
    for index, (high, low, _close) in enumerate(zip(highs, lows, closes, strict=True)):
        if high < low:
            raise ValueError("high cannot be lower than low")
        if index == 0:
            ranges.append(high - low)
            continue
        previous_close = closes[index - 1]
        ranges.append(
            max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            )
        )
    return ranges


def _directional_movements(
    highs: Sequence[Decimal],
    lows: Sequence[Decimal],
) -> tuple[list[Decimal], list[Decimal]]:
    plus_dm: list[Decimal] = []
    minus_dm: list[Decimal] = []
    for index, (high, low) in enumerate(zip(highs, lows, strict=True)):
        if index == 0:
            plus_dm.append(Decimal("0"))
            minus_dm.append(Decimal("0"))
            continue
        up_move = high - highs[index - 1]
        down_move = lows[index - 1] - low
        plus_dm.append(up_move if up_move > down_move and up_move > 0 else Decimal("0"))
        minus_dm.append(down_move if down_move > up_move and down_move > 0 else Decimal("0"))
    return plus_dm, minus_dm


def _wilder_smooth(values: Sequence[Decimal], *, period: int) -> list[Decimal]:
    _validate_period(period)
    if not values:
        return []

    smoothed: list[Decimal] = []
    previous: Decimal | None = None
    for index, value in enumerate(values):
        if previous is None:
            current = value
        elif index < period:
            current = _mean(values[: index + 1])
        else:
            current = (previous * Decimal(period - 1) + value) / Decimal(period)
        smoothed.append(current)
        previous = current
    return smoothed


def _mean(values: Sequence[Decimal]) -> Decimal:
    if not values:
        raise ValueError("cannot calculate mean of empty values")
    return sum(values, start=Decimal("0")) / Decimal(len(values))


def _rolling_mean(values: Sequence[Decimal], *, period: int) -> list[Decimal]:
    _validate_period(period)
    means: list[Decimal] = []
    for index in range(len(values)):
        start = max(0, index + 1 - period)
        means.append(_mean(values[start : index + 1]))
    return means


def _validate_period(period: int) -> None:
    if period <= 0:
        raise ValueError("period must be positive")


def _validate_equal_lengths(**series: Sequence[Decimal]) -> None:
    lengths = {name: len(values) for name, values in series.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"feature input lengths must match: {lengths}")
