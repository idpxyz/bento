"""
核心配置模块，提供配置管理的基础设施
"""

from idp.framework.infrastructure.config.core.base import (
    ConfigSection,
    ConfigSource,
    ConfigurationError,
)
from idp.framework.infrastructure.config.core.manager import (
    ConfigManager,
    ConfigRegistry,
    config_manager,
)
from idp.framework.infrastructure.config.core.provider import (
    ConfigProvider,
    ProviderRegistry,
)

__all__ = [
    "ConfigSection",
    "ConfigurationError",
    "ConfigSource",
    "ConfigManager",
    "config_manager",
    "ConfigRegistry",
    "ConfigProvider",
    "ProviderRegistry",
] 