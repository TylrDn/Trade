"""Kraken adapter configuration factory.

Builds NautilusTrader Kraken client configs from environment-loaded
settings. Requires ``nautilus_trader[kraken]`` optional extra.
"""

from __future__ import annotations

try:
    from nautilus_trader.adapters.kraken.config import (
        KrakenDataClientConfig,
        KrakenExecutionClientConfig,
    )
    from nautilus_trader.adapters.kraken.factories import (
        KrakenLiveDataClientFactory,
        KrakenLiveExecClientFactory,
    )
except ImportError as exc:
    import nautilus_trader

    _version = getattr(nautilus_trader, "__version__", "unknown")
    raise ImportError(
        f"Kraken adapter unavailable (nautilus_trader={_version}). "
        "Install with: pip install -e '.[dev,kraken]' "
        "(requires nautilus_trader[kraken]>=1.206). "
        "If installed, enum paths may have changed — check NT Kraken integration docs."
    ) from exc

try:
    from nautilus_trader.adapters.kraken.common.enums import (
        KrakenEnvironment,
        KrakenProductType,
    )
except ImportError:
    from nautilus_trader.adapters.kraken.common import (  # type: ignore[no-redef]
        KrakenEnvironment,
        KrakenProductType,
    )

from nautilus_trade.config import adapter_cfg


def _futures_credentials() -> tuple[str, str]:
    if adapter_cfg.kraken_demo:
        return (
            adapter_cfg.kraken_futures_demo_api_key,
            adapter_cfg.kraken_futures_demo_api_secret,
        )
    return adapter_cfg.kraken_futures_api_key, adapter_cfg.kraken_futures_api_secret


def _kraken_environment() -> KrakenEnvironment:
    return KrakenEnvironment.DEMO if adapter_cfg.kraken_demo else KrakenEnvironment.LIVE


def kraken_data_config() -> KrakenDataClientConfig:
    api_key, api_secret = _futures_credentials()
    return KrakenDataClientConfig(
        api_key=api_key or None,
        api_secret=api_secret or None,
        product_type=KrakenProductType.FUTURES,
        environment=_kraken_environment(),
    )


def kraken_exec_config() -> KrakenExecutionClientConfig:
    api_key, api_secret = _futures_credentials()
    return KrakenExecutionClientConfig(
        api_key=api_key or None,
        api_secret=api_secret or None,
        product_type=KrakenProductType.FUTURES,
        environment=_kraken_environment(),
    )


DATA_FACTORY = KrakenLiveDataClientFactory
EXEC_FACTORY = KrakenLiveExecClientFactory
