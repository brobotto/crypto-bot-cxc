from datetime import UTC, datetime
from decimal import Decimal

from crypto_bot_cxc.data.exchange_client import OhlcvRow


def test_ohlcv_row_contract() -> None:
    row = OhlcvRow(
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("10"),
    )

    assert row.close == Decimal("105")

