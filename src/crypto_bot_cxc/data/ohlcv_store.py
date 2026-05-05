from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from crypto_bot_cxc.events.models import MarketDataEvent

REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}
DEFAULT_MAX_FORWARD_FILL_CANDLES = 3


class GapPolicy(StrEnum):
    STRICT = "strict"
    FORWARD_FILL = "forward_fill"


def load_ohlcv_events(
    path: Path,
    *,
    symbol: str,
    timeframe: str,
    gap_policy: GapPolicy = GapPolicy.STRICT,
    max_forward_fill_candles: int = DEFAULT_MAX_FORWARD_FILL_CANDLES,
) -> list[MarketDataEvent]:
    """Load OHLCV CSV/Parquet into closed MarketDataEvent objects."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        rows = _read_csv_rows(path)
    elif suffix == ".parquet":
        rows = _read_parquet_rows(path)
    else:
        raise ValueError(f"unsupported OHLCV file extension: {path.suffix}")

    events = [_row_to_event(row, symbol=symbol, timeframe=timeframe) for row in rows]
    return _validate_and_apply_gap_policy(
        events,
        timeframe=timeframe,
        gap_policy=gap_policy,
        max_forward_fill_candles=max_forward_fill_candles,
    )


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    import pandas as pd  # type: ignore[import-untyped]

    frame = pd.read_csv(path)
    _validate_columns(set(frame.columns))
    return list(frame.to_dict(orient="records"))


def _read_parquet_rows(path: Path) -> list[dict[str, Any]]:
    import pandas as pd

    frame = pd.read_parquet(path)
    _validate_columns(set(frame.columns))
    return list(frame.to_dict(orient="records"))


def _validate_columns(columns: set[str]) -> None:
    missing = REQUIRED_COLUMNS - columns
    if missing:
        raise ValueError(f"missing OHLCV columns: {sorted(missing)}")


def _row_to_event(row: dict[str, Any], *, symbol: str, timeframe: str) -> MarketDataEvent:
    return MarketDataEvent(
        timestamp=_parse_timestamp(row["timestamp"]),
        symbol=symbol,
        open=_to_decimal(row["open"]),
        high=_to_decimal(row["high"]),
        low=_to_decimal(row["low"]),
        close=_to_decimal(row["close"]),
        volume=_to_decimal(row["volume"]),
        timeframe=timeframe,
        is_closed=bool(row.get("is_closed", True)),
    )


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, int | float):
        timestamp = value / 1000 if value > 10_000_000_000 else value
        parsed = datetime.fromtimestamp(timestamp, tz=UTC)
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _to_decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _validate_and_apply_gap_policy(
    events: list[MarketDataEvent],
    *,
    timeframe: str,
    gap_policy: GapPolicy,
    max_forward_fill_candles: int,
) -> list[MarketDataEvent]:
    if not events:
        raise ValueError("OHLCV file produced no events")
    if max_forward_fill_candles < 0:
        raise ValueError("max_forward_fill_candles cannot be negative")
    expected_delta = _timeframe_delta(timeframe)
    normalized: list[MarketDataEvent] = []
    previous: datetime | None = None
    previous_event: MarketDataEvent | None = None
    for event in events:
        if previous is not None and event.timestamp <= previous:
            raise ValueError("OHLCV timestamps must be strictly increasing")
        if previous is not None:
            actual_delta = event.timestamp - previous
            if actual_delta != expected_delta:
                if gap_policy == GapPolicy.STRICT:
                    raise ValueError(
                        "OHLCV timestamp gap detected: "
                        f"expected {expected_delta}, got {actual_delta} "
                        f"between {previous.isoformat()} and {event.timestamp.isoformat()}"
                    )
                assert previous_event is not None
                normalized.extend(
                    _forward_fill_gap(
                        previous_event=previous_event,
                        next_event=event,
                        expected_delta=expected_delta,
                        max_fill_candles=max_forward_fill_candles,
                    )
                )
        normalized.append(event)
        previous = event.timestamp
        previous_event = event
    return normalized


def _forward_fill_gap(
    *,
    previous_event: MarketDataEvent,
    next_event: MarketDataEvent,
    expected_delta: timedelta,
    max_fill_candles: int,
) -> list[MarketDataEvent]:
    synthetic_events: list[MarketDataEvent] = []
    timestamp = previous_event.timestamp + expected_delta
    while timestamp < next_event.timestamp:
        if len(synthetic_events) >= max_fill_candles:
            raise ValueError(
                "OHLCV timestamp gap too large to forward-fill: "
                f"more than {max_fill_candles} missing candles between "
                f"{previous_event.timestamp.isoformat()} and {next_event.timestamp.isoformat()}"
            )
        synthetic_events.append(
            MarketDataEvent(
                timestamp=timestamp,
                symbol=previous_event.symbol,
                open=previous_event.close,
                high=previous_event.close,
                low=previous_event.close,
                close=previous_event.close,
                volume=Decimal("0"),
                timeframe=previous_event.timeframe,
                is_closed=True,
            )
        )
        timestamp += expected_delta
    return synthetic_events


def _timeframe_delta(timeframe: str) -> timedelta:
    if timeframe.endswith("m"):
        return timedelta(minutes=int(timeframe[:-1]))
    if timeframe.endswith("h"):
        return timedelta(hours=int(timeframe[:-1]))
    if timeframe.endswith("d"):
        return timedelta(days=int(timeframe[:-1]))
    if timeframe.endswith("w"):
        return timedelta(weeks=int(timeframe[:-1]))
    raise ValueError(f"unsupported timeframe for gap validation: {timeframe}")
