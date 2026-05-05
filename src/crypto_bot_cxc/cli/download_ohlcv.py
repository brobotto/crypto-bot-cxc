from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
from pathlib import Path

from crypto_bot_cxc.data import download_ohlcv


def main() -> None:
    args = parse_args()
    rows = download_ohlcv(
        exchange_id=args.exchange,
        symbol=args.symbol,
        timeframe=args.timeframe,
        start=_parse_date(args.start),
        end=_parse_date(args.end),
        limit=args.limit,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp", "open", "high", "low", "close", "volume"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "timestamp": row.timestamp.isoformat().replace("+00:00", "Z"),
                    "open": str(row.open),
                    "high": str(row.high),
                    "low": str(row.low),
                    "close": str(row.close),
                    "volume": str(row.volume),
                }
            )
    print(f"rows={len(rows)} output={args.output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download public OHLCV data through CCXT.")
    parser.add_argument("--exchange", default="binance")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--start", required=True, help="UTC date or datetime, e.g. 2022-01-01")
    parser.add_argument("--end", required=True, help="UTC date or datetime, exclusive")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=1000)
    return parser.parse_args()


def _parse_date(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    if "T" not in normalized:
        normalized = f"{normalized}T00:00:00+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    main()

