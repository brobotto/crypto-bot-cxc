from decimal import Decimal
from pathlib import Path

import pytest

from crypto_bot_cxc.config import load_strategy_config


def test_load_strategy_config_from_project_yaml() -> None:
    config = load_strategy_config(Path("config/strategy_config.yaml"))

    assert config.strategy.primary == "ema_trend"
    assert config.strategy.symbols == ("BTC/USDT", "ETH/USDT")
    assert config.strategy.fast_period == 20
    assert config.strategy.slow_period == 100
    assert config.strategy.warmup_period == 100
    assert config.regime.adx_trend_threshold == Decimal("25")
    assert config.risk.capital_reserve == Decimal("0.4")
    assert config.execution.basic_slippage_rate == Decimal("0.0005")

    risk_config = config.risk.to_risk_config()
    assert risk_config.risk_per_trade == Decimal("0.01")
    assert risk_config.max_open_positions == 3
    assert risk_config.capital_reserve == Decimal("0.4")

    broker_config = config.execution.to_backtest_broker_config()
    assert broker_config.fee_rate == Decimal("0.001")
    assert broker_config.slippage_rate == Decimal("0.0005")

    conservative_broker_config = config.execution.to_backtest_broker_config(conservative=True)
    assert conservative_broker_config.slippage_rate == Decimal("0.001")

    ema_config = config.strategy.to_ema_trend_config()
    assert ema_config.fast_period == 20
    assert ema_config.slow_period == 100


def test_load_strategy_config_rejects_missing_required_section(tmp_path: Path) -> None:
    path = tmp_path / "strategy_config.yaml"
    path.write_text("strategy:\n  primary: ema_trend\n", encoding="utf-8")

    with pytest.raises(ValueError, match="regime"):
        load_strategy_config(path)
