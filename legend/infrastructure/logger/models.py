"""日志配置模型

This module defines the base configuration models for all logger handlers.
These models provide the foundation for type-safe configuration with validation.
"""

from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class BaseHandlerConfig(BaseModel):
    """基础处理器配置

    所有日志处理器配置的基类，提供共同的基础配置项。

    Attributes:
        enabled: 是否启用此处理器
        level: 日志级别
        queue_size: 处理队列大小
    """
    enabled: bool = Field(
        default=True,
        description="是否启用此处理器"
    )
    level: Union[LogLevel, str] = Field(
        default="INFO",
        description="日志级别"
    )
    queue_size: int = Field(
        default=1000,
        ge=1,
        description="处理队列大小"
    )

    @field_validator("level")
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别是否有效"""
        upper_v = v.upper()
        if upper_v not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid log level: {v}")
        return upper_v

    class Config:
        extra = "forbid"  # 防止意外的配置项
        validate_assignment = True  # 确保赋值时也进行验证


class ConsoleHandlerConfig(BaseHandlerConfig):
    """控制台处理器配置

    控制台日志输出的配置模型。

    Attributes:
        format: 输出格式，支持 json 或 pretty
    """
    format: Literal["json", "pretty"] = Field(
        default="json",
        description="输出格式: json 或 pretty"
    )


class FileHandlerConfig(BaseHandlerConfig):
    """文件处理器配置

    文件日志输出的配置模型。

    Attributes:
        file_path: 日志文件路径
        max_size: 单个日志文件最大大小(字节)
        backup_count: 保留的备份文件数量
    """
    file_path: str = Field(
        ...,  # 必填字段
        description="日志文件路径"
    )
    max_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1024,  # 至少1KB
        description="单个日志文件最大大小(字节)"
    )
    backup_count: int = Field(
        default=5,
        ge=0,
        description="保留的备份文件数量"
    )


class SentryHandlerConfig(BaseHandlerConfig):
    """Sentry处理器配置

    Sentry错误跟踪的配置模型。

    Attributes:
        dsn: Sentry DSN
        environment: 环境名称
    """
    dsn: str = Field(
        default="",  # 改为默认值为空字符串
        description="Sentry DSN"
    )
    environment: str = Field(
        default="production",
        description="环境名称"
    )

    @field_validator("dsn")
    def validate_dsn(cls, v: str, info: Any) -> str:
        """验证DSN格式，仅在启用时验证"""
        if info.data.get("enabled", True) and v and not v.startswith(("http://", "https://")):
            raise ValueError("Invalid Sentry DSN format")
        return v


class LogstashHandlerConfig(BaseHandlerConfig):
    """Logstash处理器配置

    Logstash日志收集的配置模型。

    Attributes:
        host: Logstash主机地址
        port: Logstash端口
        timeout: 连接超时时间(秒)
    """
    host: str = Field(
        ...,  # 必填字段
        description="Logstash主机地址"
    )
    port: int = Field(
        ...,  # 必填字段
        gt=0,
        lt=65536,
        description="Logstash端口"
    )
    timeout: float = Field(
        default=5.0,
        gt=0,
        description="连接超时时间(秒)"
    )


class KafkaHandlerConfig(BaseHandlerConfig):
    """Kafka处理器配置

    Kafka消息队列的配置模型。

    Attributes:
        bootstrap_servers: Kafka服务器地址列表
        topic: 日志主题
        client_id: 客户端ID
        compression_type: 压缩类型
        batch_size: 批处理大小
    """
    bootstrap_servers: str = Field(
        ...,  # 必填字段
        description="Kafka服务器地址列表"
    )
    topic: str = Field(
        ...,  # 必填字段
        description="日志主题"
    )
    client_id: Optional[str] = Field(
        default=None,
        description="客户端ID"
    )
    compression_type: Literal["gzip", "snappy", "lz4", "zstd"] = Field(
        default="gzip",
        description="压缩类型"
    )
    batch_size: int = Field(
        default=100,
        gt=0,
        description="批处理大小"
    )

    @field_validator("bootstrap_servers")
    def validate_bootstrap_servers(cls, v: str) -> str:
        """验证服务器地址列表格式"""
        servers = v.split(",")
        if not all(s.strip() for s in servers):
            raise ValueError("Invalid bootstrap servers format")
        return v
