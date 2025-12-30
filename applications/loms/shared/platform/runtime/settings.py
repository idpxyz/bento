"""
Application configuration settings with environment variable support.

This module provides type-safe configuration management using Pydantic.
Environment variables take precedence over default values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    url: str = "sqlite+aiosqlite:///./loms.db"
    pool_size: int = 5
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    echo_pool: bool = False

    @field_validator("url")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not any(prefix in v for prefix in ("sqlite", "postgresql", "mysql")):
            raise ValueError("Unsupported database type. Must be sqlite, postgresql, or mysql")
        return v


class OutboxSettings(BaseSettings):
    """Outbox pattern configuration."""

    dispatch_interval_seconds: int = Field(
        2, ge=1, le=60, description="Interval between outbox dispatches"
    )
    batch_size: int = Field(
        50, ge=1, le=1000, description="Maximum number of events to process per batch"
    )
    max_attempts: int = Field(5, ge=1, description="Maximum retry attempts for failed events")
    retry_delay: int = Field(60, ge=1, description="Delay in seconds before retrying failed events")


class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(
        env_prefix="LOMS_APP__", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )
    name: str = "loms-platform-core"
    environment: Literal["dev", "staging", "prod"] = "dev"
    timezone: str = "UTC"
    debug: bool = False
    secret_key: SecretStr = Field(
        default="dev-secret-key-for-local-testing-only-32chars",
        min_length=32,
        description="Secret key for cryptographic operations",
    )
    default_locale: str = "zh-CN"
    allowed_hosts: list[str] = ["*"]
    cors_origins: list[str] = ["*"]
    log_level: str = "INFO"


class ContractSettings(BaseSettings):
    """Contract validation settings."""

    root_dir: Path = Path("contracts")
    validate_requests: bool = True
    validate_responses: bool = True


class Settings(BaseSettings):
    """Application settings container.

    Loads configuration from environment variables with fallback to .env file.
    Environment variables take precedence over .env file values.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=True,
        extra="ignore",
    )

    # Core settings
    app: AppSettings = AppSettings()

    # Database configuration
    database: DatabaseSettings = DatabaseSettings()

    # Outbox configuration
    outbox: OutboxSettings = OutboxSettings()

    # Contract validation
    contracts: ContractSettings = ContractSettings()

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app.environment == "prod"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app.environment == "dev"


# Create settings instance
settings = Settings()

# For backward compatibility
# TODO: Update imports to use settings.app, settings.database, etc.
app_name = settings.app.name
database_url = settings.database.url
contracts_root = str(settings.contracts.root_dir)
outbox_dispatch_interval_seconds = settings.outbox.dispatch_interval_seconds
outbox_dispatch_batch_size = settings.outbox.batch_size
outbox_max_attempts = settings.outbox.max_attempts
default_locale = settings.app.default_locale
