"""配置参数校验 - 确保配置参数的合理性和安全性"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .outbox import OutboxProjectorConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidationIssue:
    """验证问题（错误或警告）"""

    message: str
    field_name: str | None = None
    severity: str = "error"  # "error" or "warning"
    code: str | None = None


@dataclass(frozen=True)
class ValidationRule:
    """配置验证规则"""

    field_name: str
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: list[Any] | None = None
    custom_validator: Callable[[Any], bool] | None = None
    error_message: str | None = None


class ConfigValidator:
    """配置参数验证器

    提供配置参数合理性检查，确保配置值在安全和合理的范围内。
    """

    # 预定义验证规则
    DEFAULT_RULES = [
        # 批量处理参数验证
        ValidationRule(
            field_name="batch_size",
            min_value=1,
            max_value=10000,
            error_message="batch_size 必须在 1-10000 之间",
        ),
        ValidationRule(
            field_name="max_concurrent_projectors",
            min_value=1,
            max_value=50,
            error_message="max_concurrent_projectors 必须在 1-50 之间",
        ),
        # 时间间隔参数验证
        ValidationRule(
            field_name="sleep_busy",
            min_value=0.001,  # 1毫秒
            max_value=10.0,  # 10秒
            error_message="sleep_busy 必须在 0.001-10.0 秒之间",
        ),
        ValidationRule(
            field_name="sleep_idle",
            min_value=0.1,
            max_value=300.0,  # 5分钟
            error_message="sleep_idle 必须在 0.1-300.0 秒之间",
        ),
        ValidationRule(
            field_name="sleep_idle_max",
            min_value=1.0,
            max_value=3600.0,  # 1小时
            error_message="sleep_idle_max 必须在 1.0-3600.0 秒之间",
        ),
        ValidationRule(
            field_name="error_retry_delay",
            min_value=0.1,
            max_value=300.0,
            error_message="error_retry_delay 必须在 0.1-300.0 秒之间",
        ),
        # 重试策略参数验证
        ValidationRule(
            field_name="max_retry_attempts",
            min_value=0,
            max_value=100,
            error_message="max_retry_attempts 必须在 0-100 之间",
        ),
        ValidationRule(
            field_name="backoff_multiplier",
            min_value=1,
            max_value=10,
            error_message="backoff_multiplier 必须在 1-10 之间",
        ),
        ValidationRule(
            field_name="backoff_base_seconds",
            min_value=1,
            max_value=3600,  # 1小时
            error_message="backoff_base_seconds 必须在 1-3600 秒之间",
        ),
        ValidationRule(
            field_name="backoff_max_exponent",
            min_value=0,
            max_value=20,
            error_message="backoff_max_exponent 必须在 0-20 之间",
        ),
        # 字符串字段验证
        ValidationRule(
            field_name="status_new",
            custom_validator=lambda x: len(x.strip()) > 0 and len(x) <= 20,
            error_message="status_new 不能为空且长度不超过20字符",
        ),
        ValidationRule(
            field_name="status_sent",
            custom_validator=lambda x: len(x.strip()) > 0 and len(x) <= 20,
            error_message="status_sent 不能为空且长度不超过20字符",
        ),
        ValidationRule(
            field_name="status_failed",
            custom_validator=lambda x: len(x.strip()) > 0 and len(x) <= 20,
            error_message="status_failed 不能为空且长度不超过20字符",
        ),
        ValidationRule(
            field_name="status_dead",
            custom_validator=lambda x: len(x.strip()) > 0 and len(x) <= 20,
            error_message="status_dead 不能为空且长度不超过20字符",
        ),
        ValidationRule(
            field_name="status_publishing",
            custom_validator=lambda x: len(x.strip()) > 0 and len(x) <= 20,
            error_message="status_publishing 不能为空且长度不超过20字符",
        ),
        ValidationRule(
            field_name="default_tenant_id",
            custom_validator=lambda x: len(x.strip()) > 0 and len(x) <= 64,
            error_message="default_tenant_id 不能为空且长度不超过64字符",
        ),
    ]

    # 逻辑一致性验证规则
    CONSISTENCY_RULES = [
        # 时间间隔逻辑验证
        {
            "name": "sleep_intervals_consistency",
            "validator": lambda config: config.sleep_busy <= config.sleep_idle,
            "message": "sleep_busy 应该小于等于 sleep_idle",
        },
        {
            "name": "sleep_idle_max_consistency",
            "validator": lambda config: config.sleep_idle <= config.sleep_idle_max,
            "message": "sleep_idle 应该小于等于 sleep_idle_max",
        },
        # 批量和并发逻辑验证
        {
            "name": "reasonable_batch_concurrency",
            "validator": lambda config: config.batch_size >= config.max_concurrent_projectors,
            "message": "batch_size 应该大于等于 max_concurrent_projectors 以避免资源浪费",
        },
        # 重试策略逻辑验证
        {
            "name": "backoff_logic_consistency",
            "validator": lambda config: config.backoff_multiplier > 1
            or config.max_retry_attempts <= 1,
            "message": "当 max_retry_attempts > 1 时，backoff_multiplier 应该大于 1",
        },
        # 状态值唯一性验证
        {
            "name": "status_values_uniqueness",
            "validator": lambda config: len(
                set(
                    [
                        config.status_new,
                        config.status_sent,
                        config.status_failed,
                        config.status_dead,
                        config.status_publishing,
                    ]
                )
            )
            == 5,
            "message": "所有状态值必须唯一",
        },
    ]

    def __init__(self, custom_rules: list[ValidationRule] | None = None):
        """初始化验证器

        Args:
            custom_rules: 额外的自定义验证规则
        """
        self.rules = self.DEFAULT_RULES.copy()
        if custom_rules:
            self.rules.extend(custom_rules)

    def validate(self, config: OutboxProjectorConfig, strict: bool = False) -> ValidationResult:
        """验证配置参数

        Args:
            config: 要验证的配置
            strict: 严格模式，警告也视为错误

        Returns:
            验证结果
        """
        result = ValidationResult()

        # 基本参数验证
        for rule in self.rules:
            try:
                self._validate_single_rule(config, rule, result)
            except Exception as e:
                result.add_error(f"验证规则 {rule.field_name} 执行失败: {e}")

        # 逻辑一致性验证
        for consistency_rule in self.CONSISTENCY_RULES:
            try:
                if not consistency_rule["validator"](config):
                    if strict:
                        result.add_error(consistency_rule["message"])
                    else:
                        result.add_warning(consistency_rule["message"])
            except Exception as e:
                result.add_error(f"一致性验证 {consistency_rule['name']} 失败: {e}")

        # 性能警告检查
        self._check_performance_warnings(config, result)

        return result

    def _validate_single_rule(
        self, config: OutboxProjectorConfig, rule: ValidationRule, result: ValidationResult
    ) -> None:
        """验证单个规则"""
        value = getattr(config, rule.field_name, None)

        if value is None:
            result.add_error(f"配置字段 {rule.field_name} 不存在")
            return

        # 范围验证
        if rule.min_value is not None and value < rule.min_value:
            message = (
                rule.error_message or f"{rule.field_name} 值 {value} 小于最小值 {rule.min_value}"
            )
            result.add_error(message)

        if rule.max_value is not None and value > rule.max_value:
            message = (
                rule.error_message or f"{rule.field_name} 值 {value} 大于最大值 {rule.max_value}"
            )
            result.add_error(message)

        # 允许值验证
        if rule.allowed_values is not None and value not in rule.allowed_values:
            message = (
                rule.error_message
                or f"{rule.field_name} 值 {value} 不在允许的值列表中: {rule.allowed_values}"
            )
            result.add_error(message)

        # 自定义验证器
        if rule.custom_validator is not None:
            try:
                if not rule.custom_validator(value):
                    message = rule.error_message or f"{rule.field_name} 值 {value} 未通过自定义验证"
                    result.add_error(message)
            except Exception as e:
                result.add_error(f"{rule.field_name} 自定义验证失败: {e}")

    def _check_performance_warnings(
        self, config: OutboxProjectorConfig, result: ValidationResult
    ) -> None:
        """检查性能相关警告"""

        # 高并发 + 小批量警告
        if config.max_concurrent_projectors > 10 and config.batch_size < 50:
            result.add_warning("高并发 + 小批量可能导致数据库连接池压力，建议增加 batch_size")

        # 极小轮询间隔警告
        if config.sleep_busy < 0.01:  # 10毫秒
            result.add_warning("极小的 sleep_busy 值可能导致高 CPU 使用率")

        # 超大批量警告
        if config.batch_size > 5000:
            result.add_warning("超大 batch_size 可能导致内存压力和长事务")

        # 过多重试警告
        if config.max_retry_attempts > 20:
            result.add_warning("过多重试次数可能导致失败事件长期占用资源")

        # 极长延迟警告
        max_delay = config.calculate_backoff_delay(config.max_retry_attempts)
        if max_delay > 3600:  # 1小时
            result.add_warning(f"最大重试延迟 {max_delay} 秒可能过长，考虑调整退避参数")


class ValidationResult:
    """验证结果类"""

    def __init__(self):
        self.errors: list[ValidationIssue] = []
        self.warnings: list[ValidationIssue] = []

        # 向后兼容：同时保持字符串列表
        self._error_messages: list[str] = []
        self._warning_messages: list[str] = []

    def add_error(
        self, message: str, field_name: str | None = None, code: str | None = None
    ) -> None:
        """添加错误"""
        issue = ValidationIssue(message=message, field_name=field_name, severity="error", code=code)
        self.errors.append(issue)
        self._error_messages.append(message)
        logger.error(f"配置验证错误: {message}")

    def add_warning(
        self, message: str, field_name: str | None = None, code: str | None = None
    ) -> None:
        """添加警告"""
        issue = ValidationIssue(
            message=message, field_name=field_name, severity="warning", code=code
        )
        self.warnings.append(issue)
        self._warning_messages.append(message)
        logger.warning(f"配置验证警告: {message}")

    @property
    def is_valid(self) -> bool:
        """是否验证通过（无错误）"""
        return len(self.errors) == 0

    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0

    def get_summary(self) -> str:
        """获取验证结果摘要"""
        if self.is_valid and not self.has_warnings:
            return "✅ 配置验证通过，无问题"

        summary_parts = []

        if self.errors:
            summary_parts.append(f"❌ {len(self.errors)} 个错误")

        if self.warnings:
            summary_parts.append(f"⚠️ {len(self.warnings)} 个警告")

        return " | ".join(summary_parts)

    def get_detailed_report(self) -> str:
        """获取详细验证报告"""
        lines = [self.get_summary(), ""]

        if self.errors:
            lines.append("❌ 错误:")
            for i, error in enumerate(self.errors, 1):
                field_info = f" ({error.field_name})" if error.field_name else ""
                lines.append(f"   {i}. {error.message}{field_info}")
            lines.append("")

        if self.warnings:
            lines.append("⚠️ 警告:")
            for i, warning in enumerate(self.warnings, 1):
                field_info = f" ({warning.field_name})" if warning.field_name else ""
                lines.append(f"   {i}. {warning.message}{field_info}")

        return "\n".join(lines)


def validate_config(
    config: OutboxProjectorConfig,
    strict: bool = False,
    custom_rules: list[ValidationRule] | None = None,
) -> ValidationResult:
    """便捷的配置验证函数

    Args:
        config: 要验证的配置
        strict: 严格模式
        custom_rules: 自定义验证规则

    Returns:
        验证结果
    """
    validator = ConfigValidator(custom_rules)
    return validator.validate(config, strict)


def assert_valid_config(config: OutboxProjectorConfig) -> None:
    """断言配置有效，否则抛出异常

    Args:
        config: 要验证的配置

    Raises:
        ValueError: 配置无效时
    """
    result = validate_config(config, strict=True)

    if not result.is_valid:
        error_summary = "\n".join(error.message for error in result.errors)
        raise ValueError(f"配置验证失败:\n{error_summary}")


def create_safe_config(**kwargs) -> OutboxProjectorConfig:
    """创建安全的配置，自动验证参数

    Args:
        **kwargs: 配置参数

    Returns:
        验证后的安全配置

    Raises:
        ValueError: 配置参数无效时
    """
    # 先用默认值创建基础配置
    base_config = OutboxProjectorConfig()
    base_dict = base_config.to_dict()

    # 应用用户参数
    base_dict.update(kwargs)

    # 创建新配置
    config = OutboxProjectorConfig.from_dict(base_dict)

    # 验证配置
    assert_valid_config(config)

    return config
