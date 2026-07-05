"""Order timing tracker tests."""

from nautilus_trade.ops.order_timing import OrderTimingTracker


class TestOrderTimingTracker:
    def test_pop_latency_seconds(self) -> None:
        tracker = OrderTimingTracker()
        tracker.record("order-1", 1_000_000_000)
        latency = tracker.pop_latency_seconds("order-1", 2_500_000_000)
        assert latency == 1.5

    def test_missing_submit_ts_returns_none(self) -> None:
        tracker = OrderTimingTracker()
        assert tracker.pop_latency_seconds("missing", 2_000_000_000) is None
