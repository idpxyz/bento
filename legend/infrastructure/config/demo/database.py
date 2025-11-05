"""
数据库配置示例

本示例展示如何：
1. 定义数据库配置模型
2. 使用不同环境的数据库配置
3. 从YAML文件和环境变量加载配置
4. 创建数据库连接池实例
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg
from pydantic import BaseModel, Field, field_validator

from idp.framework.infrastructure.config.core import ConfigManager
from idp.framework.infrastructure.config.providers import EnvProvider
from idp.framework.infrastructure.config.providers.yaml import YamlProvider

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========== 1. 定义数据库配置模型 ==========

class DatabaseType(str, Enum):
    """数据库类型枚举"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"


class DatabasePoolConfig(BaseModel):
    """数据库连接池配置"""
    min_size: int = Field(1, description="最小连接数", ge=1)
    max_size: int = Field(10, description="最大连接数", ge=1)
    max_queries: int = Field(50000, description="每个连接的最大查询数", ge=1000)
    max_inactive_connection_lifetime: float = Field(
        300.0, description="不活跃连接的最大生命周期（秒）", ge=1.0
    )
    timeout: float = Field(30.0, description="获取连接的超时时间（秒）", ge=0)
    recycle: int = Field(3600, description="连接回收时间（秒）", ge=0)
    pre_ping: bool = Field(True, description="是否在使用前进行连接检查")
    echo: bool = Field(False, description="是否打印SQL语句")

    @field_validator("max_size")
    @classmethod
    def max_size_must_be_greater_than_min_size(cls, v, info):
        min_size = info.data.get("min_size")
        if min_size is not None and v < min_size:
            raise ValueError(f"max_size ({v}) 必须大于等于 min_size ({min_size})")
        return v


class DatabaseCredentials(BaseModel):
    """数据库凭证配置"""
    username: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")


class DatabaseConnection(BaseModel):
    """数据库连接配置"""
    host: str = Field(..., description="数据库主机地址")
    port: int = Field(5432, description="数据库端口", gt=0, lt=65536)
    database: str = Field(..., description="数据库名称")
    db_schema: str = Field("public", description="数据库模式")
    ssl_mode: Optional[str] = Field("disable", description="SSL模式：disable, require, verify-ca, verify-full")
    application_name: Optional[str] = Field(None, description="应用程序名称")


class ReadReplicaConnection(DatabaseConnection):
    """只读副本连接配置"""
    username: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")


class ReadWriteConfig(BaseModel):
    """读写分离配置"""
    enable_read_write_split: bool = Field(False, description="是否启用读写分离")
    read_write_ratio: float = Field(0.7, description="读写比例", ge=0, le=1)
    read_replicas: List[ReadReplicaConnection] = Field(default_factory=list, description="只读副本列表")
    auto_failover: bool = Field(True, description="是否自动故障转移")
    failover_retry_interval: int = Field(5, description="故障转移重试间隔（秒）", ge=1)


class MonitorConfig(BaseModel):
    """监控配置"""
    enable_metrics: bool = Field(True, description="是否启用指标收集")
    metrics_interval: int = Field(60, description="指标收集间隔（秒）", ge=1)
    slow_query_threshold: float = Field(1.0, description="慢查询阈值（秒）", ge=0)
    enable_query_logging: bool = Field(False, description="是否启用查询日志")
    log_slow_queries: bool = Field(True, description="是否记录慢查询")
    log_queries: bool = Field(False, description="是否记录所有查询")


class EnvironmentDatabaseConfig(BaseModel):
    """环境特定的数据库配置"""
    type: Optional[DatabaseType] = Field(DatabaseType.POSTGRESQL, description="数据库类型")
    connection: Optional[DatabaseConnection] = None
    credentials: Optional[DatabaseCredentials] = None
    pool: Optional[DatabasePoolConfig] = None
    read_write: Optional[ReadWriteConfig] = None
    monitor: Optional[MonitorConfig] = None
    retry_attempts: Optional[int] = Field(3, description="重试次数", ge=0)
    retry_interval: Optional[float] = Field(1.0, description="重试间隔（秒）", ge=0)
    statement_timeout: Optional[int] = Field(30, description="语句超时时间（秒）", ge=0)
    enable_statement_cache: Optional[bool] = Field(True, description="是否启用语句缓存")
    statement_cache_size: Optional[int] = Field(1000, description="语句缓存大小", ge=0)
    keep_alive: Optional[bool] = Field(True, description="是否保持连接")
    debug_sql: Optional[bool] = Field(False, description="是否启用SQL调试")
    enable_migration: Optional[bool] = Field(True, description="是否启用迁移")
    migration_dir: Optional[str] = Field("migrations", description="迁移目录")


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


async def setup_database_config(env_name: str = "dev") -> EnvironmentDatabaseConfig:
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
        config = await config_manager.register_and_merge([
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
        env_config = config.get_env_config(env_name)
        logger.info(f"  • 类型: {env_config.type}")
        logger.info("  • 连接信息:")
        if env_config.connection:
            logger.info(f"    - 主机: {env_config.connection.host}")
            logger.info(f"    - 端口: {env_config.connection.port}")
            logger.info(f"    - 数据库: {env_config.connection.database}")
            logger.info(f"    - 模式: {env_config.connection.db_schema}")
            logger.info(f"    - SSL模式: {env_config.connection.ssl_mode}")

        if env_config.pool:
            logger.info("  • 连接池:")
            logger.info(f"    - 最小连接数: {env_config.pool.min_size}")
            logger.info(f"    - 最大连接数: {env_config.pool.max_size}")
            logger.info(f"    - 最大查询数: {env_config.pool.max_queries}")
            logger.info(f"    - 超时时间: {env_config.pool.timeout}秒")

        if env_config.monitor:
            logger.info("  • 监控:")
            logger.info(f"    - 启用指标: {env_config.monitor.enable_metrics}")
            logger.info(f"    - 慢查询阈值: {env_config.monitor.slow_query_threshold}秒")
            logger.info(f"    - 记录慢查询: {env_config.monitor.log_slow_queries}")

        return config

    except Exception as e:
        logger.error(f"❌ 加载数据库配置失败: {e}")
        raise


class DatabaseConfig(BaseModel):
    """完整数据库配置，支持环境特定配置"""
    default: EnvironmentDatabaseConfig
    dev: Optional[EnvironmentDatabaseConfig] = None
    test: Optional[EnvironmentDatabaseConfig] = None
    prod: Optional[EnvironmentDatabaseConfig] = None

    def get_connection_string(self) -> str:
        """获取PostgreSQL连接字符串"""
        config = self.get_env_config()
        return (
            f"postgresql://{config.credentials.username}:{config.credentials.password}@"
            f"{config.connection.host}:{config.connection.port}/{config.connection.database}"
        )

    def get_asyncpg_dsn(self) -> str:
        """获取asyncpg格式的DSN"""
        config = self.get_env_config()
        return (
            f"postgres://{config.credentials.username}:{config.credentials.password}@"
            f"{config.connection.host}:{config.connection.port}/{config.connection.database}"
        )

    async def create_connection_pool(self) -> asyncpg.Pool:
        """创建asyncpg连接池"""
        config = self.get_env_config()

        server_settings = {
            "search_path": config.connection.db_schema,
        }

        if config.connection.application_name:
            server_settings["application_name"] = config.connection.application_name

        ssl = None
        if config.connection.ssl_mode and config.connection.ssl_mode.lower() != "disable":
            ssl = True  # 在实际项目中可能需要更复杂的SSL设置

        return await asyncpg.create_pool(
            dsn=self.get_asyncpg_dsn(),
            min_size=config.pool.min_size,
            max_size=config.pool.max_size,
            max_queries=config.pool.max_queries,
            max_inactive_connection_lifetime=config.pool.max_inactive_connection_lifetime,
            timeout=config.pool.timeout,
            command_timeout=config.statement_timeout if config.statement_timeout else 30.0,
            statement_cache_size=config.statement_cache_size if config.enable_statement_cache else 0,
            server_settings=server_settings,
            ssl=ssl
        )


# ========== 4. 主函数 ==========

async def main():
    """主函数"""
    print("📊 数据库配置示例")
    try:
        # 默认使用开发环境
        env_name = os.environ.get("ENV", "dev")

        # 加载配置
        db_config = await setup_database_config(env_name)

        # 确定是否尝试连接数据库
        connect_db = os.environ.get("SKIP_DB_CONNECTION", "true").lower() != "true" or os.environ.get("CONNECT",
                                                                                                      "").lower() == "true"

        if not connect_db:
            # 只加载配置，不尝试连接
            print("\n⏩ 已跳过数据库连接步骤")
            print("💡 若要尝试实际连接，请使用 --connect 参数或设置环境变量: SKIP_DB_CONNECTION=false")

            # 显示连接字符串（隐藏密码）
            env_config = db_config.get_env_config(env_name)
            conn_string = (
                f"postgresql://{env_config.credentials.username}:******@"
                f"{env_config.connection.host}:{env_config.connection.port}/{env_config.connection.database}"
            )
            print(f"\n🔗 连接字符串: {conn_string}")
        else:
            # 显示诊断信息
            print("\n=== 连接数据库 ===")
            print("🔄 准备连接到数据库...")

            env_config = db_config.get_env_config(env_name)
            # 显示详细的连接参数但隐藏密码
            conn_info = {
                "host": env_config.connection.host,
                "port": env_config.connection.port,
                "database": env_config.connection.database,
                "user": env_config.credentials.username,
                "password": "******",
                "max_size": env_config.pool.max_size,
                "min_size": env_config.pool.min_size,
                "ssl": "enabled" if env_config.connection.ssl_mode and env_config.connection.ssl_mode != "disable" else "disabled"
            }
            print(f"🔍 连接参数: {conn_info}")

            try:
                # 创建连接池并执行测试查询
                print("🔄 创建数据库连接池...")
                pool = await db_config.create_connection_pool()
                print("✅ 连接池创建成功")

                # 执行测试查询
                print("\n=== 执行查询 ===")
                async with pool.acquire() as conn:
                    print("🔍 执行 'SELECT version()'...")
                    version = await conn.fetchval("SELECT version()")
                    print(f"✅ PostgreSQL 版本: {version}")

                # 关闭连接池
                await pool.close()
                print("👋 连接池已关闭")

            except Exception as db_error:
                print(f"❌ 数据库连接失败: {db_error}")
                print("\n=== 故障诊断 ===")

                # 获取配置文件路径
                config_dir = Path(__file__).parent / "config"
                config_file = config_dir / "database.yml"

                # 检查是否是连接被拒绝
                if "Connection refused" in str(db_error) or "Connect call failed" in str(db_error):
                    print("🔍 诊断: 连接被拒绝，可能原因:")
                    print(
                        f"  1️⃣ PostgreSQL 服务器未在主机 {env_config.connection.host} 的端口 {env_config.connection.port} 上运行")
                    print("  2️⃣ 防火墙阻止了连接")
                    print("  3️⃣ 配置文件中的连接信息不正确")

                    # 提供解决建议
                    print("\n💡 建议:")
                    print("  • 检查 PostgreSQL 服务是否正在运行:")
                    print("    - 容器内: `pg_isready` 或 `ps aux | grep postgres`")
                    print(f"  • 验证 PostgreSQL 是否监听在端口 {env_config.connection.port}:")
                    print(f"    - `netstat -tuln | grep {env_config.connection.port}`")
                    print("  • 尝试标准 PostgreSQL 端口 5432:")
                    print("    - `python -m idp.framework.infrastructure.config.demo.database --connect --port 5432`")
                    print("  • 检查配置文件的连接信息:")
                    print(f"    - 修改 {config_file} 中的端口和主机信息")

                # 显示详细的异常信息
                import traceback
                print("\n=== 异常详情 ===")
                print(traceback.format_exc())

                # 不重新抛出异常，让程序优雅地继续

        print("\n✨ 示例执行完成")
    except Exception as e:
        print(f"\n❌ 示例执行失败: {str(e)}")
        # 显示完整的异常堆栈跟踪
        import traceback
        print("\n=== 异常详情 ===")
        print(traceback.format_exc())


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="数据库配置示例")
    parser.add_argument("--env", default="dev", help="环境名称")
    parser.add_argument("--connect", action="store_true", help="是否尝试连接数据库")
    parser.add_argument("--print-env", action="store_true", help="打印环境变量映射")
    args = parser.parse_args()

    # 设置连接标志
    if args.connect:
        os.environ["SKIP_DB_CONNECTION"] = "false"

    asyncio.run(main())
