"""Typed configuration for all environments."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class TradeEnv(StrEnum):
    RESEARCH = "research"
    STAGING = "staging"
    PRODUCTION = "production"


class RiskConfig(BaseSettings):
    """Runtime risk limits loaded from environment or .env file."""

    model_config = SettingsConfigDict(env_prefix="RISK_", env_file=".env", extra="ignore")

    max_daily_loss_usd: float = Field(
        default=500.0, description="Max daily drawdown in USD before halt"
    )
    max_position_notional_usd: float = Field(
        default=10_000.0, description="Max single position notional"
    )
    max_leverage: float = Field(default=3.0, description="Max portfolio leverage")
    max_open_orders: int = Field(default=20, description="Max concurrent open orders")
    stale_feed_seconds: int = Field(default=30, description="Seconds before feed considered stale")


class AdapterConfig(BaseSettings):
    """Venue adapter credentials."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    binance_api_key: str = Field(default="", alias="BINANCE_API_KEY")
    binance_api_secret: str = Field(default="", alias="BINANCE_API_SECRET")
    binance_testnet: bool = Field(default=True, alias="BINANCE_TESTNET")

    kraken_api_key: str = Field(default="", alias="KRAKEN_API_KEY")
    kraken_api_secret: str = Field(default="", alias="KRAKEN_API_SECRET")


class OpsConfig(BaseSettings):
    """Observability and alerting config."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    prometheus_port: int = Field(default=8000, alias="PROMETHEUS_PORT")
    slack_webhook_url: str = Field(default="", alias="SLACK_WEBHOOK_URL")
    pagerduty_integration_key: str = Field(default="", alias="PAGERDUTY_INTEGRATION_KEY")
    logfire_token: str = Field(default="", alias="LOGFIRE_TOKEN")


class SystemConfig(BaseSettings):
    """Top-level system config."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    trade_env: TradeEnv = Field(default=TradeEnv.RESEARCH, alias="TRADE_ENV")
    catalog_path: Path = Field(default=Path("./catalog"), alias="CATALOG_PATH")
    nautilus_log_level: str = Field(default="INFO", alias="NAUTILUS_LOG_LEVEL")

    @property
    def is_live(self) -> bool:
        return self.trade_env == TradeEnv.PRODUCTION

    @property
    def is_staging(self) -> bool:
        return self.trade_env == TradeEnv.STAGING

    @property
    def is_research(self) -> bool:
        return self.trade_env == TradeEnv.RESEARCH


# Singletons — import these throughout the codebase
system_cfg = SystemConfig()
risk_cfg = RiskConfig()
adapter_cfg = AdapterConfig()
ops_cfg = OpsConfig()
