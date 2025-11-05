import logging
import os
from pathlib import Path
from typing import Any, Dict

from infrastructure.config.providers.env import EnvProvider
from infrastructure.config.providers.yaml import YamlProvider

from idp.framework.infrastructure.config.core import ConfigManager
from idp.framework.infrastructure.db.config import DatabaseConfig

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def setup_database_config(env_name: str = "dev", config_dir: str = None) -> DatabaseConfig:
    """设置数据库配置

    Args:
        env_name: 环境名称，默认为 dev

    Returns:
        DatabaseConfig: 数据库配置实例
    """
    logger.info(f"\n🔧 加载数据库配置 (环境: {env_name})")

    try:
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
        ], model=DatabaseConfig)  # 指定模型类型为 DatabaseConfig

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