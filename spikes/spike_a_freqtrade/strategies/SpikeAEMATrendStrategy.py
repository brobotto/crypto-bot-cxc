from __future__ import annotations

from datetime import datetime

import pandas as pd
from freqtrade.strategy import IStrategy
from pandas import DataFrame


class SpikeAEMATrendStrategy(IStrategy):
    INTERFACE_VERSION = 3

    can_short = False
    timeframe = "1h"
    startup_candle_count = 100
    process_only_new_candles = True

    minimal_roi = {"0": 100.0}
    stoploss = -0.99
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False

    order_types = {
        "entry": "market",
        "exit": "market",
        "stoploss": "market",
        "stoploss_on_exchange": False,
    }
    order_time_in_force = {"entry": "GTC", "exit": "GTC"}

    fast_period = 20
    slow_period = 100
    risk_per_trade = 0.01

    def custom_stake_amount(
        self,
        pair: str,
        current_time: datetime,
        current_rate: float,
        proposed_stake: float,
        min_stake: float | None,
        max_stake: float,
        leverage: float,
        entry_tag: str | None,
        side: str,
        **kwargs,
    ) -> float:
        stake = max_stake * self.risk_per_trade
        if min_stake is not None:
            stake = max(stake, min_stake)
        return min(stake, max_stake)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = dataframe["close"].ewm(
            span=self.fast_period,
            adjust=False,
        ).mean()
        dataframe["ema_slow"] = dataframe["close"].ewm(
            span=self.slow_period,
            adjust=False,
        ).mean()
        dataframe["samples"] = pd.RangeIndex(start=1, stop=len(dataframe) + 1)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ready = dataframe["samples"] > self.slow_period
        crossed_up = (
            (dataframe["ema_fast"].shift(1) <= dataframe["ema_slow"].shift(1))
            & (dataframe["ema_fast"] > dataframe["ema_slow"])
            & ready
        )
        dataframe.loc[crossed_up, ["enter_long", "enter_tag"]] = (1, "ema_cross_up")
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        ready = dataframe["samples"] > self.slow_period
        crossed_down = (
            (dataframe["ema_fast"].shift(1) >= dataframe["ema_slow"].shift(1))
            & (dataframe["ema_fast"] < dataframe["ema_slow"])
            & ready
        )
        dataframe.loc[crossed_down, ["exit_long", "exit_tag"]] = (1, "ema_cross_down")
        return dataframe
