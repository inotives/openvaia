"""Trading toolkit configuration via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5445
    postgres_user: str = "inotives"
    postgres_password: str = ""
    postgres_db: str = "inotives"
    trading_schema: str = "trading_platform"

    # Exchange
    cryptocom_api_key: str = ""
    cryptocom_api_secret: str = ""
    trading_mode: str = "paper"  # paper | live

    # Public poller
    public_poller_interval: int = 60
    public_poller_pairs: str = "CRO/USDT,BTC/USDT"

    # Private poller
    private_poller_interval: int = 60
    private_poller_exchange: str = "cryptocom"

    # TA poller
    ta_poller_interval: int = 60
    ta_daily_hour: int = 2  # UTC hour

    # Archival
    archive_dir: str = "./archive"
    ohlcv_1m_retention_days: int = 30

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def pairs(self) -> list[str]:
        return [p.strip() for p in self.public_poller_pairs.split(",") if p.strip()]

    @property
    def is_paper(self) -> bool:
        return self.trading_mode == "paper"


# Singleton — import this everywhere
settings = Settings()
