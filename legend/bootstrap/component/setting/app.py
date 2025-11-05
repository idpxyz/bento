"""应用配置组件

提供应用配置的访问和管理功能
"""

import os
from typing import List, Optional

from pydantic import BaseModel, Field

from idp.framework.infrastructure.config.core.manager import config_manager
from idp.framework.infrastructure.config.providers.env import EnvProvider
from idp.framework.infrastructure.config.providers.yaml import YamlProvider
from idp.framework.infrastructure.logger import logger_manager

logger = logger_manager.get_logger(__name__)


# ------------------------------------------------------------------
# 子模型定义
# ------------------------------------------------------------------


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False
    proxy_headers: bool = True
    timeout: int = 60


# ------------------------------------------------------------------
# AppConfig
# ------------------------------------------------------------------


# Pydantic v2 config
class AppConfig(BaseModel):
    model_config = {
        "populate_by_name": True,
        "extra": "ignore",  # 忽略未声明字段，防止报错
        "alias_generator": None  # 禁用字段别名生成
    }

    """应用配置模式"""
    env: str = Field(default="dev", description="当前环境")
    debug: bool = Field(default=False, description="是否为调试模式")
    app_name: str = Field(default="IDP Platform",
                          alias="app_name", description="应用名称")
    description: str = Field(default="IDP Platform", description="应用描述")
    version: str = Field(default="1.0.0", description="应用版本")
    timezone: str = Field(default="UTC", description="时区")

    # 服务器配置（嵌套）
    server: ServerConfig = Field(
        default_factory=ServerConfig, description="服务器配置")

    # CORS配置
    cors_enabled: bool = Field(default=True, description="是否启用CORS")
    cors_origins: List[str] = Field(default=["*"], description="允许的源")
    cors_methods: List[str] = Field(default=["*"], description="允许的方法")
    cors_headers: List[str] = Field(default=["*"], description="允许的头部")
    cors_credentials: bool = Field(default=False, description="是否允许凭证")

    # API文档配置
    docs_enabled: bool = Field(default=True, description="是否启用文档")
    docs_url: str = Field(default="/docs", description="文档URL")
    openapi_url: str = Field(default="/openapi.json",
                             description="OpenAPI URL")
    redoc_url: str = Field(default="/redoc", description="ReDoc URL")

    # --- 兼容旧字段访问（只读属性） ----------------------------------

    @property
    def server_host(self) -> str:  # noqa: D401
        return self.server.host

    @property
    def server_port(self) -> int:  # noqa: D401
        return self.server.port

    @property
    def server_workers(self) -> int:  # noqa: D401
        return self.server.workers

    @property
    def server_reload(self) -> bool:  # noqa: D401
        return self.server.reload


async def setup_app_config(env_name: Optional[str] = None, config_dir: Optional[str] = None) -> AppConfig:
    """设置应用配置

    Args:
        env_name: 环境名称
        config_dir: 配置目录路径

    Returns:
        AppConfig: 应用配置
    """
    try:
        # 1. 注册配置段
        config_manager.register_section("app", AppConfig)
        logger.info("✅ [ConfigManager] 已注册配置段: app (类型: AppConfig)")

        # 2. 注册配置提供者
        # 只使用传入的配置目录
        if config_dir:
            yaml_provider = YamlProvider(
                namespace="app",
                file_paths=[os.path.join(config_dir, "app.yml")],
                required=True,
                env_name=env_name or "dev"
            )
            config_manager.register_provider("app", yaml_provider)
            yaml_data = yaml_provider.load()
            logger.info(f"✅ [YamlProvider] 已加载YAML配置: {config_dir}/app.yml")
            logger.debug(f"📋 YAML配置内容: {yaml_data}")

            # 合并default和env配置
            merged_yaml = yaml_data.get('default', {}).copy()
            merged_yaml.update(yaml_data.get(env_name or 'dev', {}))
            logger.debug(f"📋 合并后的YAML配置: {merged_yaml}")

        # 3. 注册环境变量提供者
        env_provider = EnvProvider(
            namespace="app",
            prefix="APP_",
            env_name=env_name or "dev"
        )
        config_manager.register_provider("app", env_provider)
        env_data = env_provider.load()
        logger.debug(f"📋 环境变量配置: {env_data}")

        # 4. 合并配置
        final_config = merged_yaml.copy() if 'merged_yaml' in locals() else {}
        final_config.update(env_data)
        logger.debug(f"📋 最终合并的配置: {final_config}")

        # 5. 创建AppConfig实例
        app_config = AppConfig.model_validate(final_config)
        logger.debug(
            f"🔍 验证后的AppConfig: app_name={app_config.app_name}, description={app_config.description}")
        logger.info("✅ [ConfigManager] 应用配置加载完成")

        return app_config

    except Exception as e:
        logger.error(f"❌ 加载应用配置失败: {e}")
        raise
