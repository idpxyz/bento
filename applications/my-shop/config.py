"""Configuration Management

Uses Bento Framework's DatabaseConfig for database settings.
"""

from bento.infrastructure.database import DatabaseConfig
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings"""

    # Application
    app_name: str = "my-shop"
    app_env: str = "development"
    debug: bool = True

    # Database - delegated to Bento's DatabaseConfig
    database_url: str = "sqlite+aiosqlite:///./my_shop.db"
    database_echo: bool = True
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # Logging
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars from parent .env files
    )

    def get_database_config(self) -> DatabaseConfig:
        """Get Bento DatabaseConfig instance from settings."""
        return DatabaseConfig(
            url=self.database_url,
            echo=self.database_echo,
            pool_size=self.database_pool_size,
            max_overflow=self.database_max_overflow,
        )


# Global settings instance
settings = Settings()
