"""Bento 框架配置模块

提供企业级的配置管理机制，支持：
- 环境变量配置
- 配置文件加载
- 类型安全的配置模型
- 配置参数验证
- 配置热更新
- 预定义配置模板
"""

from .hot_reload import (
    ConfigHotReloader,
    HotReloadableComponent,
    get_hot_reloader,
)
from .outbox import (
    OutboxConfig,
    OutboxProjectorConfig,
    get_outbox_config,
    get_outbox_projector_config,
    set_outbox_config,
    set_outbox_projector_config,
)
from .templates import (
    ConfigTemplates,
    create_config_from_template,
)
from .validation import (
    ConfigValidator,
    ValidationResult,
    ValidationRule,
    assert_valid_config,
    create_safe_config,
    validate_config,
)

__all__ = [
    # 基础配置
    "OutboxConfig",
    "OutboxProjectorConfig",
    "get_outbox_config",
    "get_outbox_projector_config",
    "set_outbox_config",
    "set_outbox_projector_config",
    # 配置模板
    "ConfigTemplates",
    "create_config_from_template",
    # 配置验证
    "ConfigValidator",
    "ValidationResult",
    "ValidationRule",
    "validate_config",
    "assert_valid_config",
    "create_safe_config",
    # 热更新
    "ConfigHotReloader",
    "get_hot_reloader",
    "HotReloadableComponent",
]
