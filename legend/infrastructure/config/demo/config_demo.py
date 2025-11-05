"""配置系统示例

本示例展示如何：
1. 使用配置管理器注册和管理配置
2. 从不同来源加载配置
3. 合并和覆盖配置
4. 访问配置值
5. 使用配置变更监听
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from idp.framework.infrastructure.config.core.manager import ConfigManager
from idp.framework.infrastructure.config.providers.env import EnvProvider
from idp.framework.infrastructure.config.providers.yaml import YamlProvider
from idp.framework.infrastructure.database.config.base import DatabaseConfig

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogConfig(BaseModel):
    """日志配置"""
    level: str = Field("INFO", description="日志级别")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )
    file_path: Optional[str] = Field(None, description="日志文件路径")
    max_size: int = Field(10, description="日志文件最大大小(MB)")
    backup_count: int = Field(5, description="保留的备份文件数量")
    console_output: bool = Field(True, description="是否输出到控制台")

    class Config:
        """Pydantic配置"""
        validate_assignment = True  # 在赋值时验证
        extra = "ignore"  # 忽略额外的字段


class AppConfig(BaseModel):
    """应用配置"""
    name: str = Field("IDP", description="应用名称")
    version: str = Field("1.0.0", description="应用版本")
    debug: bool = Field(False, description="是否启用调试模式")
    secret_key: str = Field("default-secret-key", description="应用密钥")
    allowed_hosts: list[str] = Field(default_factory=lambda: ["*"], description="允许的主机列表")

    class Config:
        """Pydantic配置"""
        validate_assignment = True  # 在赋值时验证
        extra = "ignore"  # 忽略额外的字段


def config_change_listener(config: Dict[str, Any]) -> None:
    """配置变更监听器
    
    Args:
        config: 新的配置
    """
    logger.info("配置已更新:")
    for key, value in config.items():
        if isinstance(value, dict):
            logger.info(f"  {key}:")
            for k, v in value.items():
                logger.info(f"    {k}: {v}")
        else:
            logger.info(f"  {key}: {value}")


async def setup_app_config(env_name: str = "dev") -> AppConfig:
    """设置应用配置
    
    Args:
        env_name: 环境名称，默认为 dev
        
    Returns:
        AppConfig: 应用配置实例
    """
    logger.info(f"\n🔧 加载应用配置 (环境: {env_name})")

    try:
        config_dir = str(Path(__file__).parent / "config")

        # 创建配置管理器
        config_manager = ConfigManager()

        # 添加配置变更监听器
        config_manager.add_change_listener("app")

        # 注册提供器并合并配置
        config = await config_manager.register_and_merge([
            YamlProvider(
                namespace="app",
                file_paths=[os.path.join(config_dir, "app.yml")],
                required=True,
                env_name=env_name
            ),
            EnvProvider(
                namespace="app",
                env_name=env_name,
                prefix="APP",
                config_dir=config_dir
            )
        ], model=AppConfig)

        logger.info("✅ 应用配置加载完成")
        logger.info("\n📋 最终配置:")
        logger.info(f"  • 名称: {config['name']}")
        logger.info(f"  • 版本: {config['version']}")
        logger.info(f"  • 调试模式: {config['debug']}")
        logger.info(f"  • 允许的主机: {config['allowed_hosts']}")

        return AppConfig(**config)

    except Exception as e:
        logger.error(f"❌ 加载应用配置失败: {e}")
        raise


async def setup_log_config(env_name: str = "dev") -> LogConfig:
    """设置日志配置
    
    Args:
        env_name: 环境名称，默认为 dev
        
    Returns:
        LogConfig: 日志配置实例
    """
    logger.info(f"\n🔧 加载日志配置 (环境: {env_name})")

    try:
        config_dir = str(Path(__file__).parent / "config")

        # 创建配置管理器
        config_manager = ConfigManager()

        # 添加配置变更监听器
        config_manager.add_change_listener("log", config_change_listener)

        # 注册提供器并合并配置
        config = await config_manager.register_and_merge([
            YamlProvider(
                namespace="log",
                file_paths=[os.path.join(config_dir, "log.yml")],
                required=True,
                env_name=env_name
            ),
            EnvProvider(
                namespace="log",
                env_name=env_name,
                prefix="LOG",
                config_dir=config_dir
            )
        ], model=LogConfig)

        logger.info("✅ 日志配置加载完成")
        logger.info("\n📋 最终配置:")
        logger.info(f"  • 级别: {config['level']}")
        logger.info(f"  • 格式: {config['format']}")
        logger.info(f"  • 文件路径: {config.get('file_path', '未配置')}")
        logger.info(f"  • 最大大小: {config['max_size']}MB")
        logger.info(f"  • 备份数量: {config['backup_count']}")
        logger.info(f"  • 控制台输出: {config['console_output']}")

        return LogConfig(**config)

    except Exception as e:
        logger.error(f"❌ 加载日志配置失败: {e}")
        raise


async def setup_database_config(env_name: str = "dev") -> DatabaseConfig:
    """设置数据库配置
    
    Args:
        env_name: 环境名称，默认为 dev
        
    Returns:
        DatabaseConfig: 数据库配置实例
    """
    logger.info(f"\n🔧 加载数据库配置 (环境: {env_name})")

    try:
        config_dir = str(Path(__file__).parent / "config")

        # 创建配置管理器
        config_manager = ConfigManager()

        # 添加配置变更监听器
        config_manager.add_change_listener("database", config_change_listener)

        # 注册提供器并合并配置
        config_dict = await config_manager.register_and_merge([
            YamlProvider(
                namespace="database",
                file_paths=[os.path.join(config_dir, "database.yml")],
                required=True,
                env_name=env_name
            ),
            EnvProvider(
                namespace="database",
                env_name=env_name,
                prefix="DB",
                config_dir=config_dir
            )
        ])

        logger.info("✅ 数据库配置加载完成")
        logger.info("\n📋 最终配置:")
        logger.info(f"  • 类型: {config_dict.get('type', 'postgresql')}")
        logger.info("  • 连接信息:")
        connection = config_dict.get('connection', {})
        logger.info(f"    - 主机: {connection.get('host', 'localhost')}")
        logger.info(f"    - 端口: {connection.get('port', 5432)}")
        logger.info(f"    - 数据库: {connection.get('database', 'idp')}")
        logger.info(f"    - 模式: {connection.get('db_schema', 'public')}")
        logger.info(f"    - SSL模式: {connection.get('ssl_mode', 'disable')}")

        pool = config_dict.get('pool', {})
        logger.info("  • 连接池:")
        logger.info(f"    - 最小连接数: {pool.get('min_size', 1)}")
        logger.info(f"    - 最大连接数: {pool.get('max_size', 10)}")
        logger.info(f"    - 最大查询数: {pool.get('max_queries', 50000)}")
        logger.info(f"    - 超时时间: {pool.get('timeout', 30)}秒")

        monitor = config_dict.get('monitor', {})
        logger.info("  • 监控:")
        logger.info(f"    - 启用指标: {monitor.get('enable_metrics', True)}")
        logger.info(f"    - 慢查询阈值: {monitor.get('slow_query_threshold', 1.0)}秒")
        logger.info(f"    - 记录慢查询: {monitor.get('log_slow_queries', True)}")

        # 转换为DatabaseConfig对象
        database_config = DatabaseConfig(**config_dict)
        return database_config

    except Exception as e:
        logger.error(f"❌ 加载数据库配置失败: {e}")
        raise


async def main():
    """主函数"""
    logger.info("🚀 配置系统示例")

    try:
        # 获取环境名称
        env_name = os.environ.get("ENV", "dev")
        logger.info(f"🌍 当前环境: {env_name}")

        # 加载各个配置
        app_config = await setup_app_config(env_name)
        log_config = await setup_log_config(env_name)
        db_config = await setup_database_config(env_name)
        print(db_config.get_connection_uri())

        logger.info("\n✨ 示例执行完成")

    except Exception as e:
        logger.error(f"\n❌ 示例执行失败: {e}")
        import traceback
        logger.error("\n=== 异常详情 ===")
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    import argparse

    # 设置命令行参数
    parser = argparse.ArgumentParser(description="配置系统示例程序")
    parser.add_argument("--env", default="dev", help="环境名称 (default: dev)")
    parser.add_argument("--debug", action="store_true", help="显示调试信息")
    args = parser.parse_args()

    # 设置日志级别
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # 设置环境变量
    os.environ["ENV"] = args.env

    # 运行主函数
    asyncio.run(main())
