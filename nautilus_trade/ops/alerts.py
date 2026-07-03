"""Alert routing for operational events.

Supports Slack (webhook) and PagerDuty (Events API v2).
All calls are fire-and-forget with error suppression to ensure
alert failures never interrupt the trading path.
"""

from __future__ import annotations

import logging
from typing import Literal

import httpx

from nautilus_trade.config import ops_cfg

log = logging.getLogger(__name__)

AlertLevel = Literal["info", "warning", "error", "critical"]

_LEVEL_EMOJI = {
    "info": "ℹ️",
    "warning": "⚠️",
    "error": "❌",
    "critical": "🚨",
}


def send_alert(message: str, level: AlertLevel = "info") -> None:
    """Send an alert to configured channels (non-blocking, errors suppressed)."""
    emoji = _LEVEL_EMOJI.get(level, "")
    full_msg = f"{emoji} [{level.upper()}] {message}"
    log.log(
        logging.CRITICAL if level == "critical" else
        logging.ERROR if level == "error" else
        logging.WARNING if level == "warning" else
        logging.INFO,
        "ALERT: %s",
        full_msg,
    )
    _send_slack(full_msg)
    if level in ("error", "critical"):
        _send_pagerduty(message, level)


def _send_slack(message: str) -> None:
    url = ops_cfg.slack_webhook_url
    if not url:
        return
    try:
        httpx.post(url, json={"text": message}, timeout=5.0)
    except Exception as exc:  # noqa: BLE001
        log.debug("Slack alert failed (non-critical): %s", exc)


def _send_pagerduty(message: str, level: str) -> None:
    key = ops_cfg.pagerduty_integration_key
    if not key:
        return
    try:
        httpx.post(
            "https://events.pagerduty.com/v2/enqueue",
            json={
                "routing_key": key,
                "event_action": "trigger",
                "payload": {
                    "summary": message,
                    "severity": "critical" if level == "critical" else "error",
                    "source": "trade-system",
                },
            },
            timeout=5.0,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("PagerDuty alert failed (non-critical): %s", exc)
