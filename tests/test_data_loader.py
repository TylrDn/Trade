"""Data loader tests."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("nautilus_trader")

from nautilus_trade.data.loader import load_klines_to_catalog


class TestDataLoader:
    def test_writes_staged_chunks(self, tmp_path: Path) -> None:
        klines = [[1_700_000_000_000, "1", "2", "0.5", "1.5", "10"]]

        with patch("nautilus_trade.data.loader.fetch_klines_page", return_value=klines):
            count = load_klines_to_catalog(
                symbol="BTCUSDT",
                interval="1m",
                start=datetime(2024, 1, 1, tzinfo=timezone.utc),
                end=datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc),
                catalog_path=tmp_path,
            )
        assert count == 1
        assert list((tmp_path / "staging_klines").glob("*.parquet"))
