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
    api_port: int = 8007
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
    log_level: str = "DEBUG"  # 改为 DEBUG 以看到更详细的追踪信息

    # Service Discovery
    service_discovery_backend: str = "env"
    service_discovery_timeout: int = 5
    service_discovery_retry: int = 3
    service_discovery_cache_ttl: int = 300

    # Consul settings (if using Consul backend)
    consul_url: str | None = None
    consul_datacenter: str = "dc1"

    # Kubernetes settings (if using Kubernetes backend)
    kubernetes_namespace: str = "default"
    kubernetes_service_suffix: str = "svc.cluster.local"

    # Observability settings
    observability_enabled: bool = True  # 启用 Observability
    observability_provider: str = "otel"  # noop or otel

    # OpenTelemetry settings
    otel_service_name: str = "my-shop"
    otel_trace_exporter: str = "console"  # console, jaeger, otlp - 使用控制台输出
    otel_jaeger_host: str = "localhost"
    otel_jaeger_port: int = 6831
    otel_metrics_exporter: str = "console"  # console, prometheus, otlp - 使用控制台输出
    otel_prometheus_port: int = 9090

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
