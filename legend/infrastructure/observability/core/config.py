"""
可观测性配置模型
"""
import os
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

# 导入配置框架
from idp.framework.infrastructure.config.core.manager import ConfigManager
from idp.framework.infrastructure.config.providers.env import EnvProvider
from idp.framework.infrastructure.config.providers.yaml import YamlProvider

from .constants import (
    DB_DURATION_BUCKETS,
    DEFAULT_HISTOGRAM_BUCKETS,
    HTTP_DURATION_BUCKETS,
)


class SentryConfig(BaseModel):
    """Sentry配置"""
    enabled: bool = Field(default=True, description="是否启用Sentry")
    dsn: Optional[str] = Field(default=None, description="Sentry DSN")
    traces_sample_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Sentry追踪采样率"
    )
    max_breadcrumbs: int = Field(default=100, description="最大面包屑数量")
    debug: bool = Field(default=False, description="是否启用调试模式")
    send_default_pii: bool = Field(default=True, description="是否发送个人身份信息")


class OtelConfig(BaseModel):
    """OpenTelemetry配置"""
    enabled: bool = Field(default=False, description="是否启用OpenTelemetry")
    endpoint: Optional[str] = Field(default=None, description="OpenTelemetry Collector地址")


class PostgresCommonConfig(BaseModel):
    """Common PostgreSQL configuration."""
    
    connection: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/metrics",
        description="PostgreSQL connection string"
    )
    schema: str = Field(
        default="observability",
        description="Database schema name"
    )
    retention_days: int = Field(
        default=30,
        description="Number of days to retain data"
    )
    batch_size: int = Field(
        default=100,
        description="Batch size for database operations"
    )
    pool_min_size: int = Field(
        default=1,
        description="Minimum connection pool size"
    )
    pool_max_size: int = Field(
        default=10,
        description="Maximum connection pool size"
    )
    slow_query_threshold: float = Field(
        default=1.0,
        description="Threshold in seconds for slow query logging"
    )


class PostgresMetricsConfig(BaseModel):
    """PostgreSQL metrics configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Whether to enable PostgreSQL metrics"
    )
    common: PostgresCommonConfig = Field(
        default_factory=PostgresCommonConfig,
        description="Common PostgreSQL configuration"
    )
    metrics_table: str = Field(
        default="metrics",
        description="Metrics table name"
    )
    metrics_metadata_table: str = Field(
        default="metric_metadata",
        description="Metrics metadata table name"
    )
    aggregation_interval: float = Field(
        default=60.0,
        description="Interval in seconds for metrics aggregation"
    )


class MetricsConfig(BaseModel):
    """Metrics configuration."""
    
    enabled: bool = Field(
        default=True,
        description="Whether to enable metrics collection"
    )
    recorder_type: str = Field(
        default="MEMORY",
        description="Type of metrics recorder (MEMORY, PROMETHEUS, POSTGRES)"
    )
    service_name: str = Field(
        default="default",
        description="Service name for metrics"
    )
    namespace: str = Field(
        default="app",
        description="Metrics namespace"
    )
    prefix: str = Field(
        default="",
        description="Prefix for metric names",
    )
    aggregation_interval: float = Field(
        default=60.0,
        description="Interval in seconds for metrics aggregation"
    )
    default_labels: Dict[str, str] = Field(
        default_factory=dict,
        description="Default labels to apply to all metrics"
    )
    postgres: Optional[PostgresMetricsConfig] = Field(
        default=None,
        description="PostgreSQL metrics configuration"
    )


class AlertThresholds(BaseModel):
    """告警阈值配置"""
    metrics_processing_duration_seconds: float = Field(default=1.0, description="指标处理时间阈值(秒)")
    dropped_metrics_total: int = Field(default=100, description="丢弃指标数量阈值") 
    http_request_duration_seconds: float = Field(default=5.0, description="HTTP请求时间阈值(秒)")
    db_operation_duration_seconds: float = Field(default=1.0, description="数据库操作时间阈值(秒)")
    error_rate_percent: float = Field(default=5.0, description="错误率阈值(%)")


class AlertConfig(BaseModel):
    """告警配置"""
    enabled: bool = Field(default=True, description="是否启用告警")
    thresholds: AlertThresholds = Field(default_factory=AlertThresholds, description="告警阈值")


class TracingConfig(BaseModel):
    """链路追踪配置"""
    enabled: bool = Field(default=True, description="是否启用链路追踪")
    service_name: str = Field(..., description="服务名称")
    tracer_type: str = Field(default="MEMORY", description="追踪器类型，如MEMORY, SENTRY, POSTGRES")
    sample_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="采样率"
    )
    otel_endpoint: Optional[str] = Field(
        default=None, 
        description="OpenTelemetry Collector 地址"
    )
    sentry_dsn: Optional[str] = Field(
        default=None,
        description="Sentry DSN"
    )
    ignored_paths: List[str] = Field(
        default_factory=lambda: ["/metrics", "/health"],
        description="不进行追踪的路径"
    )
    # PostgreSQL 配置
    postgres_connection: Optional[str] = Field(
        default=None, 
        description="PostgreSQL连接字符串，用于PostgreSQL追踪器"
    )
    postgres_schema: str = Field(
        default="public", 
        description="PostgreSQL Schema名称"
    )
    postgres_spans_table: str = Field(
        default="observability_spans", 
        description="PostgreSQL Span表名"
    )
    postgres_events_table: str = Field(
        default="observability_span_events", 
        description="PostgreSQL Span事件表名"
    )
    postgres_retention_days: int = Field(
        default=30, 
        description="PostgreSQL数据保留天数"
    )
    postgres_flush_interval: float = Field(
        default=5.0, 
        description="PostgreSQL刷新间隔(秒)"
    )


class PostgresObservabilityConfig(BaseModel):
    """PostgreSQL可观测性配置"""
    enabled: bool = Field(default=True, description="是否启用PostgreSQL持久化")
    common: PostgresCommonConfig
    metrics_table: str = Field(default="observability_metrics", description="指标表名")
    metrics_metadata_table: str = Field(default="observability_metric_metadata", description="指标元数据表名")
    spans_table: str = Field(default="observability_spans", description="Span表名")
    span_events_table: str = Field(default="observability_span_events", description="Span事件表名")
    flush_interval: float = Field(default=5.0, description="刷新间隔(秒)")


class ObservabilityConfig(BaseModel):
    """可观测性总配置"""
    env: str = Field(default="dev", description="环境标识")
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)
    tracing: TracingConfig
    postgres: Optional[PostgresObservabilityConfig] = Field(
        default=None,
        description="PostgreSQL持久化配置，设置后将覆盖metrics和tracing中的PostgreSQL配置"
    )
    request_timeout: float = Field(
        default=30.0,
        description="监控数据上报超时时间"
    )
    batch_size: int = Field(
        default=100,
        description="批量上报大小"
    )
    flush_interval: float = Field(
        default=15.0,
        description="强制刷新间隔(秒)"
    )
    
    @model_validator(mode='after')
    def validate_postgres_config(self) -> 'ObservabilityConfig':
        """Validate and configure PostgreSQL settings."""
        if self.postgres and self.postgres.enabled:
            # Initialize metrics postgres config if needed
            if self.metrics.postgres is None:
                self.metrics.postgres = PostgresMetricsConfig()
            
            # Set metrics configuration
            self.metrics.recorder_type = "POSTGRES"
            self.metrics.postgres.common.connection = self.postgres.common.connection
            self.metrics.postgres.common.schema = self.postgres.common.schema
            self.metrics.postgres.metrics_table = self.postgres.metrics_table
            self.metrics.postgres.metrics_metadata_table = self.postgres.metrics_metadata_table
            self.metrics.postgres.common.retention_days = self.postgres.common.retention_days
            
            # Set tracing configuration
            self.tracing.tracer_type = "POSTGRES"
            self.tracing.postgres_connection = self.postgres.common.connection
            self.tracing.postgres_schema = self.postgres.common.schema
            self.tracing.postgres_spans_table = self.postgres.spans_table
            self.tracing.postgres_events_table = self.postgres.span_events_table
            self.tracing.postgres_retention_days = self.postgres.common.retention_days
            self.tracing.postgres_flush_interval = self.postgres.flush_interval
            
        return self

    # 类变量，用于存储配置实例
    _instance: ClassVar[Optional["ObservabilityConfig"]] = None

    @classmethod
    def get_instance(cls) -> "ObservabilityConfig":
        """获取单例实例
        
        Returns:
            ObservabilityConfig: 配置实例
        """
        if cls._instance is None:
            raise RuntimeError("ObservabilityConfig has not been initialized. Call load_config first.")
        return cls._instance

    @classmethod
    async def load_config(cls, env_name: str = "dev", service_name: Optional[str] = None) -> "ObservabilityConfig":
        """从配置系统加载配置
        
        Args:
            env_name: 环境名称
            service_name: 服务名称，如果为None则使用配置中的默认值
            
        Returns:
            ObservabilityConfig: 配置实例
        """
        config_dir = str(Path(__file__).parent.parent.parent.parent / "config")
        
        # 创建配置管理器
        config_manager = ConfigManager()
        
        # 注册提供器并合并配置
        config_dict = await config_manager.register_and_merge([
            YamlProvider(
                namespace="observability",
                file_paths=[os.path.join(config_dir, "observability.yml")],
                required=True,
                env_name=env_name
            ),
            EnvProvider(
                namespace="observability",
                env_name=env_name,
                prefix="OBS",
                config_dir=config_dir
            )
        ])
        
        # 使用模型进行验证
        instance = cls(**config_dict)
        
        # 如果提供了服务名称，则覆盖配置中的值
        if service_name:
            instance.service_name = service_name
            
        # 保存到类变量
        cls._instance = instance
        
        return instance

    @classmethod
    def from_env(cls, service_name: str) -> "ObservabilityConfig":
        """从环境变量加载配置（兼容旧的用法）
        
        Args:
            service_name: 服务名称
            
        Returns:
            ObservabilityConfig: 配置实例
        """
        env_name = os.getenv("APP_ENV", "dev")
        sentry_config = SentryConfig(dsn=os.getenv("SENTRY_DSN"))
        
        instance = cls(
            env=env_name,
            metrics=MetricsConfig(
                enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
                recorder_type=os.getenv("METRICS_RECORDER_TYPE", "PROMETHEUS"),
                prometheus_port=int(os.getenv("PROMETHEUS_PORT", "9090")),
                name_prefix=os.getenv("METRICS_PREFIX", "app"),
                default_labels={
                    "service": service_name,
                    "env": env_name
                },
                aggregation_interval=int(os.getenv("METRICS_AGGREGATION_INTERVAL", "60"))
            ),
            tracing=TracingConfig(
                enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true",
                sample_rate=float(os.getenv("TRACING_SAMPLE_RATE", "1.0")),
                otel_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
                sentry_dsn=os.getenv("SENTRY_DSN"),
                service_name=service_name
            ),
            postgres=PostgresObservabilityConfig(
                enabled=os.getenv("POSTGRES_ENABLED", "false").lower() == "true",
                common=PostgresCommonConfig(
                    connection=os.getenv("POSTGRES_CONNECTION", ""),
                    schema=os.getenv("POSTGRES_SCHEMA", "public"),
                    retention_days=int(os.getenv("POSTGRES_RETENTION_DAYS", "30")),
                    batch_size=int(os.getenv("POSTGRES_BATCH_SIZE", "100"))
                ),
                metrics_table=os.getenv("POSTGRES_METRICS_TABLE", "observability_metrics"),
                metrics_metadata_table=os.getenv("POSTGRES_METRICS_METADATA_TABLE", "observability_metric_metadata"),
                spans_table=os.getenv("POSTGRES_SPANS_TABLE", "observability_spans"),
                span_events_table=os.getenv("POSTGRES_SPAN_EVENTS_TABLE", "observability_span_events"),
                flush_interval=float(os.getenv("POSTGRES_FLUSH_INTERVAL", "5.0"))
            ),
            request_timeout=float(os.getenv("OBSERVABILITY_REQUEST_TIMEOUT", "30.0")),
            batch_size=int(os.getenv("OBSERVABILITY_BATCH_SIZE", "100")),
            flush_interval=float(os.getenv("OBSERVABILITY_FLUSH_INTERVAL", "15.0"))
        )
        
        cls._instance = instance
        return instance
    
    @classmethod
    def from_file(cls, file_path: str) -> "ObservabilityConfig":
        """从配置文件加载配置（兼容旧的用法）
        
        Args:
            file_path: 配置文件路径
            
        Returns:
            ObservabilityConfig: 配置实例
        """
        with open(file_path, "r") as f:
            config_data = yaml.safe_load(f)
        
        instance = cls.model_validate(config_data)
        cls._instance = instance
        return instance 