from decimal import Decimal

import pandas as pd  # type: ignore[import-untyped]
import pytest

from crypto_bot_cxc.data.feature_engine import update_ema


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
