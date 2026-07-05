"""Optional observability bootstrap (Logfire). Never raises."""

from __future__ import annotations

import logging

from nautilus_trade.config import ops_cfg

log = logging.getLogger(__name__)


def configure_observability() -> None:
    """Configure Logfire when LOGFIRE_TOKEN is set. Failures degrade gracefully."""
    if not ops_cfg.logfire_token:
        return
    try:
        import logfire  # type: ignore[import-not-found]

        logfire.configure(token=ops_cfg.logfire_token)
        logfire.install_auto_tracing(modules=["nautilus_trade"], min_duration=0.1)
        logging.basicConfig(handlers=[logfire.LogfireLoggingHandler()])
        log.info("Logfire observability configured")
    except Exception as exc:  # noqa: BLE001 — contract: never raise
        log.warning("Logfire bootstrap failed (continuing without): %s", exc)
