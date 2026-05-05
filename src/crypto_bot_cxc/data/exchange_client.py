from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class OhlcvRow:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


def download_ohlcv(
    *,
    exchange_id: str,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    limit: int = 1000,
) -> list[OhlcvRow]:
    import ccxt  # type: ignore[import-untyped]

    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start/end must be timezone-aware")
    if start >= end:
        raise ValueError("start must be before end")

    exchange_cls = getattr(ccxt, exchange_id)
    exchange = exchange_cls({"enableRateLimit": True})
    since_ms = _to_ms(start.astimezone(UTC))
    end_ms = _to_ms(end.astimezone(UTC))
    rows: list[OhlcvRow] = []

    while since_ms < end_ms:
        raw_rows = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
        if not raw_rows:
            break

        last_ms = since_ms
        for raw in raw_rows:
            row = _parse_raw_row(raw)
            row_ms = _to_ms(row.timestamp)
            if row_ms >= end_ms:
                return rows
            if row_ms >= since_ms:
                rows.append(row)
            last_ms = max(last_ms, row_ms)

        next_since = last_ms + 1
        if next_since <= since_ms:
            break
        since_ms = next_since

    return _dedupe_sorted(rows)


def _parse_raw_row(raw: Any) -> OhlcvRow:
    timestamp_ms, open_, high, low, close, volume = raw
    return OhlcvRow(
        timestamp=datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=UTC),
        open=Decimal(str(open_)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal(str(volume)),
    )


def _to_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _dedupe_sorted(rows: list[OhlcvRow]) -> list[OhlcvRow]:
    by_timestamp = {row.timestamp: row for row in rows}
    return [by_timestamp[timestamp] for timestamp in sorted(by_timestamp)]

