"""预定义配置模板 - 不同环境和场景的最佳实践配置"""

from __future__ import annotations

from typing import Any

from .outbox import OutboxProjectorConfig


class ConfigTemplates:
    """配置模板工厂类

    提供针对不同环境和使用场景的预定义配置模板，
    基于生产环境最佳实践和性能调优经验。
    """

    @staticmethod
    def development() -> OutboxProjectorConfig:
        """开发环境配置模板

        特点：
        - 小批量处理，便于调试
        - 快速失败，便于问题定位
        - 较短重试，避免开发时等待
        - 详细状态跟踪

        Returns:
            适用于开发环境的配置
        """
        return OutboxProjectorConfig(
            # 性能参数 - 偏向调试友好
            batch_size=20,  # 小批量，便于调试
            max_concurrent_projectors=2,  # 限制并发，避免资源竞争
            # 轮询策略 - 快速反应
            sleep_busy=0.1,  # 适中轮询频率
            sleep_idle=1.0,  # 短暂空闲等待
            sleep_idle_max=5.0,  # 较短最大等待
            error_retry_delay=1.0,  # 快速错误重试
            # 重试策略 - 快速失败
            max_retry_attempts=3,  # 少量重试，快速发现问题
            backoff_multiplier=2,  # 标准退避
            backoff_base_seconds=2,  # 较短基础延迟
            backoff_max_exponent=3,  # 限制最大延迟
            # 状态配置 - 标准状态
            status_new="NEW",
            status_sent="SENT",
            status_failed="FAILED",
            status_dead="DEAD",
            status_publishing="PUBLISHING",
            # 租户配置
            default_tenant_id="development",
        )

    @staticmethod
    def testing() -> OutboxProjectorConfig:
        """测试环境配置模板

        特点：
        - 中等批量处理
        - 平衡的性能和稳定性
        - 适中的重试策略
        - 可预测的行为

        Returns:
            适用于测试环境的配置
        """
        return OutboxProjectorConfig(
            # 性能参数 - 平衡配置
            batch_size=50,  # 中等批量
            max_concurrent_projectors=3,  # 适度并发
            # 轮询策略 - 平衡效率
            sleep_busy=0.05,  # 较快轮询
            sleep_idle=2.0,  # 适中空闲等待
            sleep_idle_max=10.0,  # 中等最大等待
            error_retry_delay=2.0,  # 标准错误重试
            # 重试策略 - 适中容错
            max_retry_attempts=5,  # 标准重试次数
            backoff_multiplier=2,  # 标准退避
            backoff_base_seconds=5,  # 标准基础延迟
            backoff_max_exponent=5,  # 标准最大延迟
            # 状态配置 - 标准状态
            status_new="NEW",
            status_sent="SENT",
            status_failed="FAILED",
            status_dead="DEAD",
            status_publishing="PUBLISHING",
            # 租户配置
            default_tenant_id="testing",
        )

    @staticmethod
    def production() -> OutboxProjectorConfig:
        """生产环境配置模板

        特点：
        - 大批量高吞吐量
        - 更多重试保证可靠性
        - 智能资源管理
        - 生产级稳定性

        Returns:
            适用于生产环境的配置
        """
        return OutboxProjectorConfig(
            # 性能参数 - 高吞吐量优化
            batch_size=1000,  # 大批量处理
            max_concurrent_projectors=5,  # 高并发
            # 轮询策略 - 高效能
            sleep_busy=0.01,  # 极快轮询
            sleep_idle=5.0,  # 较长空闲等待
            sleep_idle_max=30.0,  # 长期空闲优化
            error_retry_delay=5.0,  # 较长错误重试
            # 重试策略 - 高可靠性
            max_retry_attempts=10,  # 更多重试
            backoff_multiplier=2,  # 标准退避
            backoff_base_seconds=10,  # 较长基础延迟
            backoff_max_exponent=6,  # 更长最大延迟
            # 状态配置 - 标准状态
            status_new="NEW",
            status_sent="SENT",
            status_failed="FAILED",
            status_dead="DEAD",
            status_publishing="PUBLISHING",
            # 租户配置
            default_tenant_id="production",
        )

    @staticmethod
    def high_throughput() -> OutboxProjectorConfig:
        """高吞吐量场景配置模板

        适用场景：
        - 大量事件处理
        - 批处理作业
        - 数据同步

        Returns:
            优化高吞吐量的配置
        """
        return OutboxProjectorConfig(
            # 性能参数 - 极致吞吐量
            batch_size=2000,  # 超大批量
            max_concurrent_projectors=8,  # 高并发
            # 轮询策略 - 极速处理
            sleep_busy=0.001,  # 毫秒级轮询
            sleep_idle=1.0,  # 短暂空闲
            sleep_idle_max=10.0,  # 限制空闲时间
            error_retry_delay=1.0,  # 快速错误恢复
            # 重试策略 - 快速处理优先
            max_retry_attempts=15,  # 多次重试保证投递
            backoff_multiplier=2,  # 标准退避
            backoff_base_seconds=5,  # 适中基础延迟
            backoff_max_exponent=4,  # 限制最大延迟
            # 状态配置
            status_new="NEW",
            status_sent="SENT",
            status_failed="FAILED",
            status_dead="DEAD",
            status_publishing="PROCESSING",  # 自定义处理中状态
            # 租户配置
            default_tenant_id="high_throughput",
        )

    @staticmethod
    def low_latency() -> OutboxProjectorConfig:
        """低延迟场景配置模板

        适用场景：
        - 实时通知
        - 即时消息
        - 快速响应需求

        Returns:
            优化低延迟的配置
        """
        return OutboxProjectorConfig(
            # 性能参数 - 低延迟优化
            batch_size=10,  # 极小批量，快速处理
            max_concurrent_projectors=10,  # 高并发
            # 轮询策略 - 极速响应
            sleep_busy=0.001,  # 毫秒级轮询
            sleep_idle=0.1,  # 极短空闲
            sleep_idle_max=1.0,  # 极短最大等待
            error_retry_delay=0.1,  # 极快错误重试
            # 重试策略 - 快速失败
            max_retry_attempts=3,  # 少量重试
            backoff_multiplier=2,  # 标准退避倍数
            backoff_base_seconds=1,  # 极短基础延迟
            backoff_max_exponent=3,  # 限制延迟增长
            # 状态配置
            status_new="PENDING",  # 自定义待处理状态
            status_sent="DELIVERED",  # 自定义已投递状态
            status_failed="RETRY",  # 自定义重试状态
            status_dead="FAILED",  # 自定义最终失败状态
            status_publishing="SENDING",  # 自定义发送中状态
            # 租户配置
            default_tenant_id="low_latency",
        )

    @staticmethod
    def resource_conservative() -> OutboxProjectorConfig:
        """资源节约场景配置模板

        适用场景：
        - 资源受限环境
        - 成本优化
        - 后台定时处理

        Returns:
            优化资源使用的配置
        """
        return OutboxProjectorConfig(
            # 性能参数 - 资源节约
            batch_size=100,  # 适中批量
            max_concurrent_projectors=2,  # 低并发
            # 轮询策略 - 节约 CPU
            sleep_busy=0.5,  # 较慢轮询
            sleep_idle=10.0,  # 长空闲等待
            sleep_idle_max=60.0,  # 超长空闲优化
            error_retry_delay=10.0,  # 长错误间隔
            # 重试策略 - 渐进退避
            max_retry_attempts=8,  # 适中重试
            backoff_multiplier=3,  # 更大退避倍数
            backoff_base_seconds=30,  # 较长基础延迟
            backoff_max_exponent=6,  # 很长最大延迟
            # 状态配置
            status_new="NEW",
            status_sent="SENT",
            status_failed="FAILED",
            status_dead="DEAD",
            status_publishing="PUBLISHING",
            # 租户配置
            default_tenant_id="conservative",
        )

    @staticmethod
    def batch_processing() -> OutboxProjectorConfig:
        """批处理场景配置模板

        适用场景：
        - 夜间批处理
        - ETL 作业
        - 大批量数据迁移

        Returns:
            优化批处理的配置
        """
        return OutboxProjectorConfig(
            # 性能参数 - 批处理优化
            batch_size=5000,  # 超大批量
            max_concurrent_projectors=3,  # 适中并发，避免资源争抢
            # 轮询策略 - 稳定处理
            sleep_busy=0.1,  # 稳定轮询
            sleep_idle=30.0,  # 长空闲间隔
            sleep_idle_max=300.0,  # 超长空闲（5分钟）
            error_retry_delay=30.0,  # 长错误间隔
            # 重试策略 - 高容错
            max_retry_attempts=20,  # 大量重试
            backoff_multiplier=2,  # 标准退避
            backoff_base_seconds=60,  # 长基础延迟（1分钟）
            backoff_max_exponent=8,  # 超长最大延迟
            # 状态配置
            status_new="QUEUED",  # 自定义排队状态
            status_sent="PROCESSED",  # 自定义已处理状态
            status_failed="ERROR",  # 自定义错误状态
            status_dead="DISCARDED",  # 自定义丢弃状态
            status_publishing="PROCESSING",  # 自定义处理中状态
            # 租户配置
            default_tenant_id="batch",
        )

    @staticmethod
    def get_template(template_name: str) -> OutboxProjectorConfig:
        """根据名称获取配置模板

        Args:
            template_name: 模板名称

        Returns:
            对应的配置模板

        Raises:
            ValueError: 不支持的模板名称
        """
        templates = {
            "development": ConfigTemplates.development,
            "dev": ConfigTemplates.development,
            "testing": ConfigTemplates.testing,
            "test": ConfigTemplates.testing,
            "production": ConfigTemplates.production,
            "prod": ConfigTemplates.production,
            "high_throughput": ConfigTemplates.high_throughput,
            "high_perf": ConfigTemplates.high_throughput,
            "low_latency": ConfigTemplates.low_latency,
            "realtime": ConfigTemplates.low_latency,
            "resource_conservative": ConfigTemplates.resource_conservative,
            "conservative": ConfigTemplates.resource_conservative,
            "batch_processing": ConfigTemplates.batch_processing,
            "batch": ConfigTemplates.batch_processing,
        }

        factory = templates.get(template_name.lower())
        if not factory:
            available = ", ".join(templates.keys())
            raise ValueError(f"不支持的配置模板: {template_name}. 可用模板: {available}")

        return factory()

    @staticmethod
    def list_templates() -> list[str]:
        """列出所有可用的配置模板

        Returns:
            配置模板名称列表
        """
        return [
            "development",
            "testing",
            "production",
            "high_throughput",
            "low_latency",
            "resource_conservative",
            "batch_processing",
        ]

    @staticmethod
    def describe_template(template_name: str) -> str:
        """获取配置模板描述

        Args:
            template_name: 模板名称

        Returns:
            模板描述信息
        """
        descriptions = {
            "development": "开发环境：小批量、快速失败、调试友好",
            "testing": "测试环境：平衡配置、可预测行为",
            "production": "生产环境：高吞吐量、高可靠性",
            "high_throughput": "高吞吐量：大批量处理、极速轮询",
            "low_latency": "低延迟：小批量、毫秒级响应",
            "resource_conservative": "资源节约：低并发、长间隔",
            "batch_processing": "批处理：超大批量、高容错",
        }

        return descriptions.get(template_name.lower(), "未知模板")


def create_config_from_template(
    template_name: str, overrides: dict[str, Any] | None = None
) -> OutboxProjectorConfig:
    """基于模板创建配置，支持参数覆盖

    Args:
        template_name: 模板名称
        overrides: 要覆盖的配置参数

    Returns:
        自定义配置实例

    Example:
        ```python
        # 基于生产环境模板，但使用更大的批量
        config = create_config_from_template(
            "production",
            {"batch_size": 2000, "default_tenant_id": "my_service"}
        )
        ```
    """
    base_config = ConfigTemplates.get_template(template_name)

    if not overrides:
        return base_config

    # 将配置转换为字典
    config_dict = base_config.to_dict()

    # 应用覆盖参数
    config_dict.update(overrides)

    # 创建新配置实例
    return OutboxProjectorConfig.from_dict(config_dict)
