"""Outbox 配置模型 - 支持环境变量和配置文件"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OutboxProjectorConfig:
    """OutboxProjector 配置类

    支持从环境变量和配置文件加载配置参数
    """

    # 批量处理配置
    batch_size: int = 200
    max_concurrent_projectors: int = 5

    # 轮询间隔配置 (秒)
    sleep_busy: float = 0.1  # 有事件时的轮询间隔
    sleep_idle: float = 1.0  # 无事件时的基础间隔
    sleep_idle_max: float = 5.0  # 无事件时的最大间隔
    error_retry_delay: float = 2.0  # 出错后重试间隔

    # 重试配置
    max_retry_attempts: int = 5

    # 指数退避配置
    backoff_multiplier: int = 2
    backoff_base_seconds: int = 5
    backoff_max_exponent: int = 5

    # 状态配置
    status_new: str = "NEW"
    status_sent: str = "SENT"
    status_failed: str = "FAILED"
    status_dead: str = "DEAD"

    # P2-B 性能优化配置
    enable_performance_monitoring: bool = True  # 启用性能监控
    connection_pool_size: int = 20  # 数据库连接池大小
    connection_pool_overflow: int = 10  # 连接池溢出大小
    query_timeout_seconds: int = 30  # 查询超时时间
    batch_commit_size: int = 1000  # 批量提交大小
    status_publishing: str = "PUBLISHING"

    # 多租户配置
    default_tenant_id: str = "default"

    @classmethod
    def from_env(cls, prefix: str = "BENTO_OUTBOX_") -> OutboxProjectorConfig:
        """从环境变量加载配置

        Args:
            prefix: 环境变量前缀

        Returns:
            配置实例

        Example:
            ```bash
            export BENTO_OUTBOX_BATCH_SIZE=500
            export BENTO_OUTBOX_MAX_RETRY_ATTEMPTS=3
            ```
        """
        return cls(
            batch_size=int(os.getenv(f"{prefix}BATCH_SIZE", cls.batch_size)),
            max_concurrent_projectors=int(
                os.getenv(f"{prefix}MAX_CONCURRENT_PROJECTORS", cls.max_concurrent_projectors)
            ),
            sleep_busy=float(os.getenv(f"{prefix}SLEEP_BUSY", cls.sleep_busy)),
            sleep_idle=float(os.getenv(f"{prefix}SLEEP_IDLE", cls.sleep_idle)),
            sleep_idle_max=float(os.getenv(f"{prefix}SLEEP_IDLE_MAX", cls.sleep_idle_max)),
            error_retry_delay=float(os.getenv(f"{prefix}ERROR_RETRY_DELAY", cls.error_retry_delay)),
            max_retry_attempts=int(
                os.getenv(f"{prefix}MAX_RETRY_ATTEMPTS", cls.max_retry_attempts)
            ),
            backoff_multiplier=int(
                os.getenv(f"{prefix}BACKOFF_MULTIPLIER", cls.backoff_multiplier)
            ),
            backoff_base_seconds=int(
                os.getenv(f"{prefix}BACKOFF_BASE_SECONDS", cls.backoff_base_seconds)
            ),
            backoff_max_exponent=int(
                os.getenv(f"{prefix}BACKOFF_MAX_EXPONENT", cls.backoff_max_exponent)
            ),
            status_new=os.getenv(f"{prefix}STATUS_NEW", cls.status_new),
            status_sent=os.getenv(f"{prefix}STATUS_SENT", cls.status_sent),
            status_failed=os.getenv(f"{prefix}STATUS_FAILED", cls.status_failed),
            status_dead=os.getenv(f"{prefix}STATUS_DEAD", cls.status_dead),
            status_publishing=os.getenv(f"{prefix}STATUS_PUBLISHING", cls.status_publishing),
            default_tenant_id=os.getenv(f"{prefix}DEFAULT_TENANT_ID", cls.default_tenant_id),
        )

    @classmethod
    def from_dict(cls, config_dict: dict[str, Any]) -> OutboxProjectorConfig:
        """从字典加载配置，自动进行类型转换

        Args:
            config_dict: 配置字典

        Returns:
            配置实例
        """

        def safe_int(value: Any, default: int) -> int:
            """安全转换为整数"""
            if isinstance(value, int):
                return value
            if isinstance(value, (str, float)):
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return default
            return default

        def safe_float(value: Any, default: float) -> float:
            """安全转换为浮点数"""
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default
            return default

        def safe_str(value: Any, default: str) -> str:
            """安全转换为字符串"""
            if value is None:
                return default
            return str(value)

        return cls(
            batch_size=safe_int(config_dict.get("batch_size"), cls.batch_size),
            max_concurrent_projectors=safe_int(
                config_dict.get("max_concurrent_projectors"), cls.max_concurrent_projectors
            ),
            sleep_busy=safe_float(config_dict.get("sleep_busy"), cls.sleep_busy),
            sleep_idle=safe_float(config_dict.get("sleep_idle"), cls.sleep_idle),
            sleep_idle_max=safe_float(config_dict.get("sleep_idle_max"), cls.sleep_idle_max),
            error_retry_delay=safe_float(
                config_dict.get("error_retry_delay"), cls.error_retry_delay
            ),
            max_retry_attempts=safe_int(
                config_dict.get("max_retry_attempts"), cls.max_retry_attempts
            ),
            backoff_multiplier=safe_int(
                config_dict.get("backoff_multiplier"), cls.backoff_multiplier
            ),
            backoff_base_seconds=safe_int(
                config_dict.get("backoff_base_seconds"), cls.backoff_base_seconds
            ),
            backoff_max_exponent=safe_int(
                config_dict.get("backoff_max_exponent"), cls.backoff_max_exponent
            ),
            status_new=safe_str(config_dict.get("status_new"), cls.status_new),
            status_sent=safe_str(config_dict.get("status_sent"), cls.status_sent),
            status_failed=safe_str(config_dict.get("status_failed"), cls.status_failed),
            status_dead=safe_str(config_dict.get("status_dead"), cls.status_dead),
            status_publishing=safe_str(config_dict.get("status_publishing"), cls.status_publishing),
            default_tenant_id=safe_str(config_dict.get("default_tenant_id"), cls.default_tenant_id),
        )

    def calculate_backoff_delay(self, retry_count: int) -> int:
        """计算指数退避延迟

        Args:
            retry_count: 当前重试次数

        Returns:
            延迟秒数
        """
        exponent = min(retry_count, self.backoff_max_exponent)
        return (self.backoff_multiplier**exponent) * self.backoff_base_seconds

    def to_dict(self) -> dict[str, Any]:
        """转换为字典

        Returns:
            配置字典
        """
        return {
            "batch_size": self.batch_size,
            "max_concurrent_projectors": self.max_concurrent_projectors,
            "sleep_busy": self.sleep_busy,
            "sleep_idle": self.sleep_idle,
            "sleep_idle_max": self.sleep_idle_max,
            "error_retry_delay": self.error_retry_delay,
            "max_retry_attempts": self.max_retry_attempts,
            "backoff_multiplier": self.backoff_multiplier,
            "backoff_base_seconds": self.backoff_base_seconds,
            "backoff_max_exponent": self.backoff_max_exponent,
            "status_new": self.status_new,
            "status_sent": self.status_sent,
            "status_failed": self.status_failed,
            "status_dead": self.status_dead,
            "status_publishing": self.status_publishing,
            "default_tenant_id": self.default_tenant_id,
        }


@dataclass(frozen=True)
class OutboxConfig:
    """Outbox 存储配置"""

    # 表配置
    table_name: str = "outbox"

    # 索引配置
    enable_tenant_status_index: bool = True
    enable_processing_index: bool = True
    enable_topic_index: bool = True
    enable_aggregate_index: bool = True

    # 字段长度限制
    max_topic_length: int = 128
    max_tenant_id_length: int = 64
    max_aggregate_id_length: int = 128
    max_aggregate_type_length: int = 100
    max_schema_id_length: int = 128
    max_routing_key_length: int = 100
    max_error_message_length: int = 500

    @classmethod
    def from_env(cls, prefix: str = "BENTO_OUTBOX_STORAGE_") -> OutboxConfig:
        """从环境变量加载配置"""
        return cls(
            table_name=os.getenv(f"{prefix}TABLE_NAME", cls.table_name),
            enable_tenant_status_index=os.getenv(
                f"{prefix}ENABLE_TENANT_STATUS_INDEX", "true"
            ).lower()
            == "true",
            enable_processing_index=os.getenv(f"{prefix}ENABLE_PROCESSING_INDEX", "true").lower()
            == "true",
            enable_topic_index=os.getenv(f"{prefix}ENABLE_TOPIC_INDEX", "true").lower() == "true",
            enable_aggregate_index=os.getenv(f"{prefix}ENABLE_AGGREGATE_INDEX", "true").lower()
            == "true",
            max_topic_length=int(os.getenv(f"{prefix}MAX_TOPIC_LENGTH", cls.max_topic_length)),
            max_tenant_id_length=int(
                os.getenv(f"{prefix}MAX_TENANT_ID_LENGTH", cls.max_tenant_id_length)
            ),
            max_aggregate_id_length=int(
                os.getenv(f"{prefix}MAX_AGGREGATE_ID_LENGTH", cls.max_aggregate_id_length)
            ),
            max_aggregate_type_length=int(
                os.getenv(f"{prefix}MAX_AGGREGATE_TYPE_LENGTH", cls.max_aggregate_type_length)
            ),
            max_schema_id_length=int(
                os.getenv(f"{prefix}MAX_SCHEMA_ID_LENGTH", cls.max_schema_id_length)
            ),
            max_routing_key_length=int(
                os.getenv(f"{prefix}MAX_ROUTING_KEY_LENGTH", cls.max_routing_key_length)
            ),
            max_error_message_length=int(
                os.getenv(f"{prefix}MAX_ERROR_MESSAGE_LENGTH", cls.max_error_message_length)
            ),
        )


# 全局配置实例（懒加载）
_outbox_projector_config: OutboxProjectorConfig | None = None
_outbox_config: OutboxConfig | None = None


def get_outbox_projector_config() -> OutboxProjectorConfig:
    """获取全局 OutboxProjector 配置"""
    global _outbox_projector_config
    if _outbox_projector_config is None:
        _outbox_projector_config = OutboxProjectorConfig.from_env()
    return _outbox_projector_config


def get_outbox_config() -> OutboxConfig:
    """获取全局 Outbox 存储配置"""
    global _outbox_config
    if _outbox_config is None:
        _outbox_config = OutboxConfig.from_env()
    return _outbox_config


def set_outbox_projector_config(config: OutboxProjectorConfig) -> None:
    """设置全局 OutboxProjector 配置（用于测试）"""
    global _outbox_projector_config
    _outbox_projector_config = config


def set_outbox_config(config: OutboxConfig) -> None:
    """设置全局 Outbox 存储配置（用于测试）"""
    global _outbox_config
    _outbox_config = config
