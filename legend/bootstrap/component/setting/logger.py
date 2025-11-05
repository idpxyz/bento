"""日志配置模块

This module defines the application-specific logger configuration schema,
extending the base configuration models from the infrastructure layer.
"""

import os
from typing import Dict, Optional

from infrastructure.config.core.manager import ConfigManager
from pydantic import BaseModel, ConfigDict, Field

from idp.framework.infrastructure.config.providers import EnvProvider, YamlProvider
from idp.framework.infrastructure.logger.models import (
    ConsoleHandlerConfig,
    FileHandlerConfig,
    KafkaHandlerConfig,
    LogstashHandlerConfig,
    SentryHandlerConfig,
)


class LoggerConfigSchema(BaseModel):
    """应用日志配置模式

    扩展基础日志处理器配置，提供应用级别的配置整合。

    Attributes:
        console: 控制台日志配置
        file: 文件日志配置
        sentry: Sentry日志配置
        logstash: Logstash日志配置
        kafka: Kafka日志配置
    """
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
        json_encoders={
            # 自定义JSON编码器，如果需要的话
        }
    )

    console: ConsoleHandlerConfig = Field(
        default_factory=ConsoleHandlerConfig,
        description="控制台日志配置"
    )
    file: FileHandlerConfig = Field(
        default_factory=lambda: FileHandlerConfig(file_path="logs/app.log"),
        description="文件日志配置"
    )
    sentry: SentryHandlerConfig = Field(
        default_factory=lambda: SentryHandlerConfig(enabled=False, dsn=""),
        description="Sentry日志配置"
    )
    logstash: LogstashHandlerConfig = Field(
        default_factory=lambda: LogstashHandlerConfig(
            enabled=False,
            host="localhost",
            port=5000
        ),
        description="Logstash日志配置"
    )
    kafka: KafkaHandlerConfig = Field(
        default_factory=lambda: KafkaHandlerConfig(
            enabled=False,
            bootstrap_servers="localhost:9092",
            topic="logs"
        ),
        description="Kafka日志配置"
    )


async def setup_logger_config(
    env_name: str = "dev",
    config_dir: Optional[str] = None
) -> LoggerConfigSchema:
    """设置日志配置

    加载并验证日志配置，支持从YAML文件和环境变量加载。

    Args:
        env_name: 环境名称，默认为"dev"
        config_dir: 配置文件目录，如果为None则使用默认目录

    Returns:
        LoggerConfigSchema: 验证后的日志配置对象

    Raises:
        ConfigurationError: 配置加载或验证失败时抛出
    """
    config_manager = ConfigManager()

    # 构建配置提供者列表
    providers = [
        YamlProvider(
            namespace="logger",
            file_paths=[os.path.join(config_dir or "", "logger.yml")],
            required=True,
            env_name=env_name
        ),
        EnvProvider(
            namespace="logger",
            env_name=env_name,
            prefix="LOGGER",
            config_dir=config_dir
        )
    ]

    # 注册并合并配置
    config_dict = await config_manager.register_and_merge(
        providers,
        model=LoggerConfigSchema
    )

    # 创建并验证配置对象
    return LoggerConfigSchema(**config_dict)
