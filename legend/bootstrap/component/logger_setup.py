"""日志系统初始化组件

此模块负责初始化日志系统，根据配置创建和启动各种日志处理器。
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from idp.framework.bootstrap.component.setting.logger import LoggerConfigSchema
from idp.framework.infrastructure.config.core.manager import ConfigManager
from idp.framework.infrastructure.config.providers.env import EnvProvider
from idp.framework.infrastructure.config.providers.yaml import YamlProvider
from idp.framework.infrastructure.logger.manager import logger_manager
from idp.framework.infrastructure.logger.processors import (
    ConsoleProcessor,
    FileProcessor,
    KafkaProcessor,
    LogstashProcessor,
    SentryProcessor,
)

__all__ = ['logger_setup', 'logger']


class LoggerSetupError(Exception):
    """日志系统初始化错误"""
    pass


logger = None  # 将在logger_setup中初始化


async def logger_setup(env_name: str = "dev", config_dir: Optional[str] = None) -> None:
    """初始化日志系统

    根据配置初始化并启动日志系统，包括创建各种日志处理器。

    Args:
        env_name: 环境名称，默认为"dev"
        config_dir: 配置文件目录，如果为None则使用默认目录

    Raises:
        LoggerSetupError: 日志系统初始化失败时抛出
    """
    global logger

    try:
        # 确定配置目录
        config_path = Path(config_dir) if config_dir else Path(
            __file__).parent.parent.parent / "config"
        if not config_path.exists():
            raise FileNotFoundError(f"配置目录不存在: {config_path}")

        # 创建配置管理器
        config_manager = ConfigManager()

        # 注册提供器并合并配置
        config_dict = await config_manager.register_and_merge([
            YamlProvider(
                namespace="logger",
                file_paths=[str(config_path / "logger.yml")],
                required=True,
                env_name=env_name
            ),
            EnvProvider(
                namespace="logger",
                env_name=env_name,
                prefix="LOGGER",
                config_dir=str(config_path)
            )
        ], model=LoggerConfigSchema)

        # 创建配置对象
        config = LoggerConfigSchema.model_validate(config_dict)

        # 配置控制台处理器
        if config.console.enabled:
            logger_manager.add_processor(
                ConsoleProcessor(config=config.console))

        # 配置文件处理器
        if config.file.enabled:
            # 确保日志目录存在
            log_dir = os.path.dirname(config.file.file_path)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)

            logger_manager.add_processor(FileProcessor(config=config.file))

        # 配置Kafka处理器
        if config.kafka.enabled:
            try:
                logger_manager.add_processor(
                    KafkaProcessor(config=config.kafka))
            except ImportError:
                logger_manager.get_logger(__name__).warning(
                    "Kafka依赖未安装，跳过Kafka处理器配置",
                    event="kafka_import_error"
                )
            except Exception as e:
                logger_manager.get_logger(__name__).error(
                    "Kafka处理器配置失败",
                    event="kafka_config_error",
                    error=str(e)
                )

        # 配置Logstash处理器
        if config.logstash.enabled:
            try:
                logger_manager.add_processor(
                    LogstashProcessor(config=config.logstash))
            except Exception as e:
                logger_manager.get_logger(__name__).error(
                    "Logstash处理器配置失败",
                    event="logstash_config_error",
                    error=str(e)
                )

        # 配置Sentry处理器
        if config.sentry.enabled and config.sentry.dsn:
            try:
                logger_manager.add_processor(
                    SentryProcessor(config=config.sentry))
            except ImportError:
                logger_manager.get_logger(__name__).warning(
                    "Sentry依赖未安装，跳过Sentry处理器配置",
                    event="sentry_import_error"
                )
            except Exception as e:
                logger_manager.get_logger(__name__).error(
                    "Sentry处理器配置失败",
                    event="sentry_config_error",
                    error=str(e)
                )

        # 如果没有任何处理器被添加，添加默认控制台处理器
        if not logger_manager._processors:
            logger_manager.add_processor(
                ConsoleProcessor(config=config.console))

        # 启动异步处理器
        await logger_manager.start()

        # 获取logger并设置全局上下文
        logger = logger_manager.get_logger(__name__)

        # 输出启动日志
        active_processors = ", ".join(
            f"{p.__class__.__name__}({p.config.level})"
            for p in logger_manager._processors
        )

        logger.info(
            f"✅ 应用日志系统启动 (环境: {env_name}, 处理器: {active_processors})"
        )

    except Exception as e:
        raise LoggerSetupError(f"日志系统初始化失败: {e}") from e


async def get_logger_status() -> Dict[str, Any]:
    """获取日志系统状态

    Returns:
        Dict[str, Any]: 包含处理器状态、队列大小等信息
    """
    return {
        "active_processors": [
            {
                "name": p.__class__.__name__,
                "level": p.config.level,
                "enabled": p.config.enabled
            }
            for p in logger_manager._processors
        ],
        "queue_sizes": {
            p.__class__.__name__: p._queue.qsize() if p._queue else 0
            for p in logger_manager._processors
        }
    }


async def check_logger_health() -> bool:
    """检查日志系统是否健康

    Returns:
        bool: 日志系统是否健康
    """
    return all(
        p._running and not p._queue.full()
        for p in logger_manager._processors
        if p.config.enabled
    )
