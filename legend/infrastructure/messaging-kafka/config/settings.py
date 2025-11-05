from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class KafkaSettings(BaseSettings):
    bootstrap_servers: str = Field("192.168.8.137:9092", env="KAFKA_BOOTSTRAP_SERVERS")
    security_protocol: str = Field("PLAINTEXT", env="KAFKA_SECURITY_PROTOCOL")
    sasl_mechanism: Optional[str] = Field(None, env="KAFKA_SASL_MECHANISM")
    sasl_username: Optional[str] = Field(None, env="KAFKA_SASL_USERNAME")
    sasl_password: Optional[str] = Field(None, env="KAFKA_SASL_PASSWORD")

    @field_validator("bootstrap_servers")
    def parse_bootstrap_servers(cls, v: str) -> List[str]:
        return v.split(",")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class SchemaRegistrySettings(BaseSettings):
    url: str = Field("http://192.168.8.137:8081", env="SCHEMA_REGISTRY_URL")
    auth_user: Optional[str] = Field(None, env="SCHEMA_REGISTRY_AUTH_USER")
    auth_password: Optional[str] = Field(None, env="SCHEMA_REGISTRY_AUTH_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class ProducerSettings(BaseSettings):
    client_id_prefix: str = Field(
        "message-bus-producer", env="PRODUCER_CLIENT_ID_PREFIX"
    )
    acks: str = Field("all", env="PRODUCER_ACKS")
    compression_type: str = Field("snappy", env="PRODUCER_COMPRESSION_TYPE")
    batch_size: int = Field(16384, env="PRODUCER_BATCH_SIZE")
    linger_ms: int = Field(5, env="PRODUCER_LINGER_MS")
    retries: int = Field(5, env="PRODUCER_RETRIES")
    max_in_flight: int = Field(5, env="PRODUCER_MAX_IN_FLIGHT")
    idempotence: bool = Field(True, env="PRODUCER_IDEMPOTENCE")
    delivery_timeout_ms: int = Field(120000, env="PRODUCER_DELIVERY_TIMEOUT_MS")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class ConsumerSettings(BaseSettings):
    group_id_prefix: str = Field("message-bus-consumer", env="CONSUMER_GROUP_ID_PREFIX")
    auto_offset_reset: str = Field("earliest", env="CONSUMER_AUTO_OFFSET_RESET")
    enable_auto_commit: bool = Field(False, env="CONSUMER_ENABLE_AUTO_COMMIT")
    max_poll_interval_ms: int = Field(300000, env="CONSUMER_MAX_POLL_INTERVAL_MS")
    max_poll_records: int = Field(500, env="CONSUMER_MAX_POLL_RECORDS")
    session_timeout_ms: int = Field(30000, env="CONSUMER_SESSION_TIMEOUT_MS")
    heartbeat_interval_ms: int = Field(10000, env="CONSUMER_HEARTBEAT_INTERVAL_MS")
    isolation_level: str = Field("read_committed", env="CONSUMER_ISOLATION_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class AppSettings(BaseSettings):
    log_level: str = Field("INFO", env="LOG_LEVEL")
    environment: str = Field("development", env="ENVIRONMENT")
    api_port: int = Field(8000, env="API_PORT")
    api_host: str = Field("0.0.0.0", env="API_HOST")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class MonitoringSettings(BaseSettings):
    enable_prometheus: bool = Field(True, env="ENABLE_PROMETHEUS")
    prometheus_port: int = Field(9090, env="PROMETHEUS_PORT")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class RedisSettings(BaseSettings):
    host: str = Field("localhost", env="REDIS_HOST")
    port: int = Field(6379, env="REDIS_PORT")
    password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    db: int = Field(0, env="REDIS_DB")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class DatabaseSettings(BaseSettings):
    host: str = Field("localhost", env="DB_HOST")
    port: int = Field(5432, env="DB_PORT")
    user: str = Field("postgres", env="DB_USER")
    password: str = Field("postgres", env="DB_PASSWORD")
    name: str = Field("message_bus", env="DB_NAME")

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class Settings(BaseSettings):
    kafka: KafkaSettings = KafkaSettings()
    schema_registry: SchemaRegistrySettings = SchemaRegistrySettings()
    producer: ProducerSettings = ProducerSettings()
    consumer: ConsumerSettings = ConsumerSettings()
    app: AppSettings = AppSettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    redis: RedisSettings = RedisSettings()
    database: DatabaseSettings = DatabaseSettings()

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get application settings with caching to avoid repeated loading.

    Returns:
        Settings: Application settings instance
    """
    return Settings()
