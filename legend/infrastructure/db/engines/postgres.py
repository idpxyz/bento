"""PostgreSQL数据库引擎"""

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncSession

from idp.framework.exception.classified import InfrastructureException
from idp.framework.exception.code.database import DatabaseErrorCode
from idp.framework.infrastructure.db.config import (
    ConnectionConfig,
    CredentialsConfig,
    DatabaseConfig,
)
from idp.framework.infrastructure.db.core.interfaces import ConnectionManager, Database
from idp.framework.infrastructure.logger import logger_manager

from .base import BaseDatabaseEngine

# 避免循环导入
if TYPE_CHECKING:
    from idp.framework.infrastructure.db.sqlalchemy.connection import (
        SQLAlchemyConnectionManager,
    )

logger = logger_manager.get_logger(__name__)


class PostgreSQLDatabase(BaseDatabaseEngine):
    """PostgreSQL数据库实现"""

    def __init__(self, config: DatabaseConfig):
        """初始化PostgreSQL数据库
        
        Args:
            config: 数据库配置
        """
        super().__init__(config)
        # PostgreSQL特有的配置
        self.replication_lag_threshold = 30  # 复制延迟阈值（秒）
        self._current_replica = -1  # 当前使用的副本索引，从-1开始以便第一次选择时为0
        self._healthy_replicas = []  # 健康的副本列表
        # 用于验证数据库连接
        self._ping_query = "SELECT 1"
        # 用于读写分离的索引
        self._read_write_index = 0

    def _create_connection_url(self, conn_config: ConnectionConfig, credentials: Optional[CredentialsConfig] = None) -> URL:
        """创建PostgreSQL连接URL
        
        Args:
            conn_config: 连接配置
            credentials: 凭证配置，如果为None则使用self.config.credentials
            
        Returns:
            URL: SQLAlchemy URL对象
        """
        creds = credentials or self.config.credentials
        
        # 构建连接URL - 不在URL中包含application_name, 稍后通过connect_args传递
        return URL.create(
            drivername="postgresql+asyncpg",
            username=creds.username if creds else None,
            password=creds.password if creds else None,
            host=conn_config.host,
            port=conn_config.port,
            database=conn_config.database
        )

    def _get_engine_kwargs(self) -> Dict[str, Any]:
        """获取PostgreSQL特有的引擎参数
        
        Returns:
            Dict[str, Any]: 引擎参数
        """
        # 检查是否有command_timeout属性，否则使用默认值
        command_timeout = getattr(self.config.pool, "command_timeout", None) or self.config.pool.timeout * 1000
        
        # 获取应用名称
        application_name = None
        if hasattr(self.config.connection, "application_name") and self.config.connection.application_name:
            application_name = self.config.connection.application_name
        else:
            application_name = "idp_postgres_client"
        
        # 基本连接参数
        connect_args = {
            "server_settings": {
                "statement_timeout": str(self.config.pool.timeout * 1000),
                "lock_timeout": str(self.config.pool.timeout * 500),  # PostgreSQL特有
                "idle_in_transaction_session_timeout": str(self.config.pool.timeout * 2000),  # PostgreSQL特有
                "application_name": application_name,  # 在server_settings中设置应用名称
                "timezone": "UTC"  # 服务器时区设置为UTC
            },
            "command_timeout": command_timeout,  # 移到外层，作为asyncpg特定参数
            "statement_cache_size": 0,  # 禁用语句缓存，避免预编译语句冲突
        }
        
        # 确保asyncpg正确处理时区
        connect_args["server_settings"]["DateStyle"] = "ISO, MDY"
        
        return {
            "isolation_level": "READ COMMITTED",  # 默认隔离级别
            "connect_args": connect_args,
            # 其他 SQLAlchemy 引擎参数
            "json_serializer": None,  # 使用默认的JSON序列化器
            "implicit_returning": True,
            "future": True
        }

    def get_database_type_name(self) -> str:
        """获取数据库类型名称
        
        Returns:
            str: 数据库类型名称
        """
        return "postgresql"

    @asynccontextmanager
    async def _get_replica_session(self, replica_index: int) -> AsyncGenerator[AsyncSession, None]:
        """获取指定副本的会话
        
        Args:
            replica_index: 副本索引
            
        Returns:
            AsyncGenerator[AsyncSession, None]: 异步会话生成器
            
        Raises:
            InfrastructureException: 当副本不可用或会话创建失败时
        """
        if not self.config.read_write.read_replicas or replica_index >= len(self.config.read_write.read_replicas):
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_INVALID_REPLICA_INDEX,
                details={"message": f"Invalid replica index: {replica_index}"}
            )

        session_factory = self._read_session_factories.get(replica_index)
        if not session_factory:
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_NOT_INITIALIZED,
                details={"message": f"Read replica {replica_index} is not initialized"}
            )

        session = session_factory()
        try:
            # Set session to read-only mode for replicas
            await session.execute(text("SET TRANSACTION READ ONLY"))
            await session.execute(text("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY"))
            yield session
        except Exception as e:
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_SESSION_ERROR,
                details={"message": f"Session error: {str(e)}", "replica_index": replica_index}
            ) from e
        finally:
            await session.close()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取主数据库会话
        
        Returns:
            AsyncGenerator[AsyncSession, None]: 异步会话生成器
            
        Raises:
            InfrastructureException: 当会话创建失败时
        """
        if not self._session_factory:
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_NOT_INITIALIZED,
                details={"message": "Database session factory not initialized"}
            )

        session = None
        try:
            session = self._session_factory()
            
            # 只在需要时开始新事务
            if not session.in_transaction():
                await session.begin()
                
            yield session
            
            # 只在事务存在且未提交时提交
            if session.in_transaction():
                await session.commit()
        except Exception as e:
            if session and session.in_transaction():
                await session.rollback()
            logger.error(f"Session error occurred: {str(e)}", exc_info=True)
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_SESSION_ERROR,
                details={"message": f"Session error: {str(e)}"}
            ) from e
        finally:
            if session:
                try:
                    await session.close()
                except Exception as close_error:
                    logger.error(f"Error closing session: {str(close_error)}", exc_info=True)

    async def _check_replica_health(self, replica_index: int) -> bool:
        """PostgreSQL特有的副本健康检查
        
        Args:
            replica_index: 副本索引
            
        Returns:
            bool: 是否健康
        """
        try:
            async with asyncio.timeout(self.config.pool.timeout):
                async with self._get_replica_session(replica_index) as session:
                    # 检查复制延迟
                    result = await session.execute(text("""
                        SELECT CASE 
                            WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() 
                            THEN 0 
                            ELSE EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::INTEGER 
                        END as lag;
                    """))
                    lag = (await result.scalar()) or 0
                    
                    if lag > self.replication_lag_threshold:
                        logger.warning(f"Replica {replica_index} has high replication lag: {lag}s")
                        return False
                        
                    return True
                    
        except asyncio.TimeoutError:
            logger.error(f"Health check timeout for replica {replica_index}")
            return False
        except Exception as e:
            logger.error(f"Health check failed for replica {replica_index}: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取PostgreSQL特有的统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = await super().get_stats()
        postgres_stats = {}
        
        try:
            async with self.get_session() as session:
                # 获取数据库大小
                result = await session.execute(text("""
                    SELECT pg_database_size(current_database()) as db_size;
                """))
                db_size = await result.scalar()
                postgres_stats["database_size_bytes"] = db_size
                
                # 获取活动连接数
                result = await session.execute(text("""
                    SELECT count(*) FROM pg_stat_activity 
                    WHERE datname = current_database();
                """))
                active_connections = await result.scalar()
                postgres_stats["active_connections"] = active_connections
                
                # 获取表统计信息
                result = await session.execute(text("""
                    SELECT schemaname, relname, n_live_tup, n_dead_tup, 
                           last_vacuum, last_autovacuum, last_analyze, last_autoanalyze
                    FROM pg_stat_user_tables;
                """))
                tables = []
                for row in await result.fetchall():
                    tables.append({
                        "schema": row[0],
                        "name": row[1],
                        "live_rows": row[2],
                        "dead_rows": row[3],
                        "last_vacuum": row[4],
                        "last_autovacuum": row[5],
                        "last_analyze": row[6],
                        "last_autoanalyze": row[7]
                    })
                postgres_stats["tables"] = tables
                
        except Exception as e:
            logger.error(f"Failed to collect PostgreSQL stats: {e}")
            postgres_stats["error"] = str(e)
            
        stats["postgres_specific"] = postgres_stats
        return stats

    async def _select_replica(self) -> Optional[int]:
        """选择一个健康的副本
        
        Returns:
            Optional[int]: 副本索引，如果没有健康的副本则返回None
        """
        if not self.config.read_write.read_replicas:
            return None
            
        if not self._replica_manager:
            # 如果没有使用副本管理器，则沿用原来的简单轮询策略
            total_replicas = len(self.config.read_write.read_replicas)
            if total_replicas == 0:
                return None
                
            # 尝试所有副本
            for _ in range(total_replicas):
                self._current_replica = (self._current_replica + 1) % total_replicas
                if await self._check_replica_health(self._current_replica):
                    return self._current_replica
        else:
            # 使用副本管理器的负载均衡策略
            return await self._replica_manager.select_replica()
                
        # 如果没有健康的副本，返回None
        return None

    async def _initialize_connection_manager(self) -> Optional[ConnectionManager]:
        """初始化PostgreSQL连接管理器
        
        Returns:
            ConnectionManager: 连接管理器实例
        """
        if not self.is_initialized:
            return None
            
        # 动态导入以避免循环引用
        from idp.framework.infrastructure.db.sqlalchemy.connection import (
            SQLAlchemyConnectionManager,
        )

        # 创建SQLAlchemy连接管理器
        # 注意：使用与当前数据库相同的配置创建连接管理器
        connection_manager = SQLAlchemyConnectionManager(config=self.config)
        
        # 初始化连接管理器
        await connection_manager.initialize()
        
        return connection_manager

    async def execute_raw_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """执行原始SQL查询
        
        使用连接管理器获取连接并执行查询
        
        Args:
            query: SQL查询字符串
            params: 查询参数
            
        Returns:
            Any: 查询结果
        """
        async with self.get_connection() as conn:
            return await conn.execute(query, parameters=params)

    async def get_postgres_database_version(self) -> str:
        """获取PostgreSQL数据库版本
        
        Returns:
            str: PostgreSQL版本字符串
        """
        query = "SELECT version()"
        try:
            async with self.get_connection() as conn:
                result = await conn.execute(query)
                row = await result.fetchone()
                return row[0] if row else "Unknown"
        except Exception as e:
            logger.error(f"Failed to get PostgreSQL version: {e}")
            return f"Error: {str(e)}"

    async def ensure_timezone_columns(self, table_names: List[str] = None) -> Dict[str, List[str]]:
        """确保表的时间戳列使用带时区类型
        
        此方法检查指定表的时间戳列，如果是不带时区类型，则修改为带时区类型。
        
        Args:
            table_names: 要检查的表名列表，如果为None则检查所有表
            
        Returns:
            Dict[str, List[str]]: 已修改的表名和列名的映射
        """
        result = {"checked": [], "modified": []}
        
        try:
            async with self.get_session() as session:
                # 获取要检查的表
                if not table_names:
                    query = """
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    """
                    result_set = await session.execute(text(query))
                    table_names = [row[0] for row in result_set.fetchall()]
                
                result["checked"] = table_names
                
                # 检查每个表的列类型
                for table_name in table_names:
                    # 获取表的时间戳列
                    query = f"""
                    SELECT column_name, data_type, datetime_precision 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = '{table_name}'
                    AND data_type = 'timestamp without time zone'
                    """
                    result_set = await session.execute(text(query))
                    timestamp_columns = [row[0] for row in result_set.fetchall()]
                    
                    # 修改时间戳列为带时区类型
                    for column_name in timestamp_columns:
                        alter_query = f"""
                        ALTER TABLE {table_name} 
                        ALTER COLUMN {column_name} TYPE timestamp with time zone
                        USING {column_name} AT TIME ZONE 'UTC'
                        """
                        await session.execute(text(alter_query))
                        result["modified"].append(f"{table_name}.{column_name}")
                
                await session.commit()
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to ensure timezone columns: {e}")
            return {"error": str(e), "checked": result["checked"], "modified": result["modified"]}
