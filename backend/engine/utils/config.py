"""
Configuration management using environment variables.
"""

import os
from typing import List

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Coinbase Advanced Trade
    coinbase_api_key: str = ""
    coinbase_api_secret: str = ""
    coinbase_passphrase: str = ""
    coinbase_sandbox: bool = True

    # Alpaca
    alpaca_api_key: str = ""
    alpaca_secret_key: str = ""
    alpaca_base_url: str = "https://paper-api.alpaca.markets"

    # Trading
    use_market: str = "crypto"  # crypto|stocks
    default_symbol: str = "BTC-USD"
    timeframe: str = "5m"
    risk_per_trade: float = 0.005
    max_daily_loss: float = 0.02
    max_portfolio_exposure: float = 0.4
    symbol_whitelist: str = "BTC-USD,ETH-USD"

    # Database
    database_url: str = "sqlite:///./data/aurora_trader.db"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # Alerts
    slack_webhook_url: str = ""
    email_smtp_server: str = ""
    email_smtp_user: str = ""
    email_smtp_pass: str = ""
    email_alert_to: str = ""

    # Worker
    worker_enabled: bool = False
    worker_check_interval_seconds: int = 300

    model_config = ConfigDict(env_file=".env", case_sensitive=False)

    @property
    def symbols(self) -> List[str]:
        """Parse whitelist into list of symbols."""
        return [s.strip() for s in self.symbol_whitelist.split(",") if s.strip()]


def get_settings() -> Settings:
    """
    Get application settings singleton.

    Returns:
        Settings instance loaded from environment
    """
    return Settings()
