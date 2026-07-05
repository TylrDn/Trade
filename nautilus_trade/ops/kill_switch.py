"""Unified operator kill switch — thin facade over circuit breaker."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nautilus_trade.ops.alerts import send_alert

if TYPE_CHECKING:
    from nautilus_trade.live.runtime import LiveRuntime

log = logging.getLogger(__name__)


class KillSwitch:
    """Trip the shared breaker and record an operator kill event."""

    def __init__(self, runtime: LiveRuntime) -> None:
        self._runtime = runtime

    def trigger(
        self,
        reason: str,
        operator_id: str,
        *,
        recommend_flatten: bool = True,
    ) -> None:
        log.critical("KILL SWITCH triggered by %s: %s", operator_id, reason)
        send_alert(f"KILL SWITCH: {reason} (operator={operator_id})", level="critical")
        self._runtime.record_breaker_trip(f"kill_switch:{reason}")
        self._runtime.event_store.record(
            "kill_switch_triggered",
            {
                "reason": reason,
                "operator": operator_id,
                "recommend_flatten": recommend_flatten,
            },
        )
        if recommend_flatten:
            log.critical(
                "Kill switch recommends emergency flatten via scripts/flatten_all.py"
            )
