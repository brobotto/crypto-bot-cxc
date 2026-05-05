from decimal import Decimal
from pathlib import Path

import pytest

from crypto_bot_cxc.data import GapPolicy, load_ohlcv_events


def test_load_ohlcv_events_from_csv(tmp_path: Path) -> None:
    path = tmp_path / "btcusdt_1h.csv"
    path.write_text(
        "\n".join(
            [
                "timestamp,open,high,low,close,volume",
                "2024-01-01T00:00:00Z,100,110,90,105,1000",
                "2024-01-01T01:00:00Z,105,115,95,110,1200",
            ]
        ),
        encoding="utf-8",
    )

    events = load_ohlcv_events(path, symbol="BTC/USDT", timeframe="1h")

    assert len(events) == 2
    assert events[0].symbol == "BTC/USDT"
    assert events[0].close == Decimal("105")
    assert events[0].timestamp.isoformat() == "2024-01-01T00:00:00+00:00"
    assert events[0].is_closed is True


def test_load_ohlcv_events_rejects_unsorted_timestamps(tmp_path: Path) -> None:
    path = tmp_path / "btcusdt_1h.csv"
    path.write_text(
        "\n".join(
            [
                "timestamp,open,high,low,close,volume",
                "2024-01-01T01:00:00Z,105,115,95,110,1200",
                "2024-01-01T00:00:00Z,100,110,90,105,1000",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="strictly increasing"):
        load_ohlcv_events(path, symbol="BTC/USDT", timeframe="1h")


def test_load_ohlcv_events_rejects_timeframe_gaps(tmp_path: Path) -> None:
    path = tmp_path / "btcusdt_1h.csv"
    path.write_text(
        "\n".join(
            [
                "timestamp,open,high,low,close,volume",
                "2024-01-01T00:00:00Z,100,110,90,105,1000",
                "2024-01-01T02:00:00Z,105,115,95,110,1200",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="timestamp gap"):
        load_ohlcv_events(path, symbol="BTC/USDT", timeframe="1h")


def test_load_ohlcv_events_forward_fills_timeframe_gaps_when_explicit(tmp_path: Path) -> None:
    path = tmp_path / "btcusdt_1h.csv"
    path.write_text(
        "\n".join(
            [
                "timestamp,open,high,low,close,volume",
                "2024-01-01T00:00:00Z,100,110,90,105,1000",
                "2024-01-01T02:00:00Z,105,115,95,110,1200",
            ]
        ),
        encoding="utf-8",
    )

    events = load_ohlcv_events(
        path,
        symbol="BTC/USDT",
        timeframe="1h",
        gap_policy=GapPolicy.FORWARD_FILL,
    )

    assert len(events) == 3
    assert events[1].timestamp.isoformat() == "2024-01-01T01:00:00+00:00"
    assert events[1].open == Decimal("105")
    assert events[1].high == Decimal("105")
    assert events[1].low == Decimal("105")
    assert events[1].close == Decimal("105")
    assert events[1].volume == Decimal("0")
