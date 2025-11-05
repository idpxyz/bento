"""数据库连接管理器实现"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional, Set, Type

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from idp.framework.exception import InfrastructureException
from idp.framework.exception.code.database import DatabaseErrorCode
from idp.framework.infrastructure.db.config import DatabaseConfig, DatabaseType
from idp.framework.infrastructure.db.core.interfaces import (
    ConnectionManager as IConnectionManager,
)
from idp.framework.infrastructure.db.core.interfaces import (
    SessionManager,
    TransactionManager,
)
from idp.framework.infrastructure.db.resilience.errors import (
    ConnectionError,
    DatabaseError,
)
from idp.framework.infrastructure.db.resilience.handler import DatabaseErrorHandler
from idp.framework.infrastructure.db.sqlalchemy.session import (
    SQLAlchemySessionManager,
    SQLAlchemyTransactionManager,
)
from idp.framework.infrastructure.logger import logger_manager

# 避免循环导入
if TYPE_CHECKING:
    from idp.framework.infrastructure.db.engines.base import BaseEngineDatabase
    from idp.framework.infrastructure.db.engines.mysql import MySQLDatabase
    from idp.framework.infrastructure.db.engines.postgres import PostgreSQLDatabase
    from idp.framework.infrastructure.db.engines.sqlite import SQLiteDatabase

logger = logger_manager.get_logger(__name__)


class SQLAlchemyConnectionStats:
    """连接统计信息"""

    def __init__(self) -> None:
        self.total_connections = 0
        self.active_connections = 0
        self.idle_connections = 0
        self.failed_connections = 0
        self.last_error: Optional[str] = None

    def connection_created(self) -> None:
        """记录连接创建"""
        self.total_connections += 1
        self.active_connections += 1

    def connection_released(self) -> None:
        """记录连接释放"""
        self.active_connections -= 1
        self.idle_connections += 1

    def connection_failed(self, error: str) -> None:
        """记录连接失败"""
        self.failed_connections += 1
        self.last_error = error


class SQLAlchemyConnectionPool:
    """SQLAlchemy连接池实现

    提供底层连接池管理，作为SQLAlchemyConnectionManager的实现细节。
    管理数据库连接池和连接获取。
    """

    def __init__(
        self,
        engine: AsyncEngine,
        pool_size: int = 5,
        max_overflow: int = 10
    ):
        """初始化连接池

        Args:
            engine: SQLAlchemy异步引擎
            pool_size: 连接池大小
            max_overflow: 连接池最大溢出连接数
        """
        self._engine = engine
        self._pool_size = pool_size
        self._max_overflow = max_overflow
        self._available_connections: Set[AsyncConnection] = set()
        self._used_connections: Set[AsyncConnection] = set()
        self._initialized = False
        self._closed = False
        self._lock = asyncio.Lock()

    @property
    def is_initialized(self) -> bool:
        """连接池是否已初始化"""
        return self._initialized

    @property
    def is_closed(self) -> bool:
        """连接池是否已关闭"""
        return self._closed

    @property
    def available_connections_count(self) -> int:
        """可用连接数量"""
        return len(self._available_connections)

    @property
    def used_connections_count(self) -> int:
        """已使用连接数量"""
        return len(self._used_connections)

    @property
    def total_connections_count(self) -> int:
        """总连接数量"""
        return self.available_connections_count + self.used_connections_count

    async def initialize(self) -> None:
        """初始化连接池

        创建初始连接池
        """
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            # 创建初始连接池
            for _ in range(self._pool_size):
                try:
                    # Use raw connect method without trying to pass application_name
                    # which should only be in the connection URL
                    conn = await self._engine.connect()
                    self._available_connections.add(conn)
                except Exception as e:
                    logger.error(f"Failed to create initial connection: {e}")

            self._initialized = True
            logger.info(
                f"Connection pool initialized with {len(self._available_connections)} connections")

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[AsyncConnection, None]:
        """获取连接，优先从连接池获取可用连接，若无则创建新连接

        Yields:
            AsyncConnection: 数据库连接

        Raises:
            ConnectionError: 无法获取连接时抛出
        """
        if not self._initialized:
            await self.initialize()

        connection = None
        try:
            # 检查是否有可用连接
            if self._available_connections:
                connection = self._available_connections.pop()
                self._used_connections.add(connection)
                logger.debug(
                    f"Acquired connection from pool. Available: {len(self._available_connections)}")
            # 若全部连接都在使用中但未达到最大连接数，创建新连接
            elif self.total_connections_count < self._pool_size + self._max_overflow:
                try:
                    # 创建新连接，不传递额外参数
                    connection = await self._engine.connect()
                    self._used_connections.add(connection)
                    logger.debug("Created new connection")
                except Exception as e:
                    logger.error(f"Failed to create connection: {str(e)}")
                    raise ConnectionError(
                        f"Failed to create connection: {str(e)}")
            else:
                # 若已达到最大连接数，等待连接释放
                logger.warning(
                    f"Connection pool exhausted. Waiting for available connection.")
                for _ in range(10):  # 最多等待10秒
                    await asyncio.sleep(1)
                    if self._available_connections:
                        connection = self._available_connections.pop()
                        self._used_connections.add(connection)
                        logger.debug("Acquired connection after waiting")
                        break
                else:
                    # 超时后仍无法获取连接
                    raise ConnectionError(
                        f"Connection pool exhausted after 10 seconds")

            yield connection
        finally:
            if connection and connection in self._used_connections:
                await self.release(connection)

    async def cleanup(self) -> None:
        """清理连接资源

        关闭并清理所有连接
        """
        if self._closed:
            return

        async with self._lock:
            if self._closed:
                return

            # 关闭所有已使用连接
            used_connections = list(self._used_connections)
            for conn in used_connections:
                try:
                    await conn.close()
                except Exception as e:
                    logger.error(f"Error closing used connection: {e}")
            self._used_connections.clear()

            # 关闭所有可用连接
            available_connections = list(self._available_connections)
            for conn in available_connections:
                try:
                    await conn.close()
                except Exception as e:
                    logger.error(f"Error closing available connection: {e}")
            self._available_connections.clear()

            self._closed = True
            self._initialized = False
            logger.info("Connection pool closed")

    async def check_health(self, query: str = "SELECT 1") -> bool:
        """检查连接健康状态

        使用给定的查询检查数据库连接是否正常。
        使用独立的连接执行健康检查，避免影响业务事务。

        Args:
            query: 健康检查查询

        Returns:
            bool: 如果数据库连接正常则返回True
        """
        try:
            # 使用独立的连接执行健康检查
            async with self._engine.connect() as connection:
                # 执行简单的健康检查查询
                await connection.execute(text(query))
                return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息

        Returns:
            Dict[str, Any]: 连接池统计信息
        """
        return {
            "available_connections": self.available_connections_count,
            "used_connections": self.used_connections_count,
            "total_connections": self.total_connections_count,
            "pool_size": self._pool_size,
            "max_overflow": self._max_overflow,
            "is_initialized": self._initialized,
            "is_closed": self._closed
        }

    async def release(self, connection: AsyncConnection) -> None:
        """释放连接，将其返回到连接池中

        Args:
            connection: 要释放的数据库连接
        """
        if connection in self._used_connections:
            self._used_connections.remove(connection)

            # 如果连接有效且连接池未满，则加入可用连接池
            if not connection.closed:
                if len(self._available_connections) < self._pool_size:
                    self._available_connections.add(connection)
                    logger.debug(
                        f"Connection returned to pool. Available: {len(self._available_connections)}")
                else:
                    # 连接池已满，关闭多余连接
                    await connection.close()
                    logger.debug("Connection closed (pool full)")
            else:
                logger.warning("Attempted to release closed connection")


class SQLAlchemyConnectionManager(IConnectionManager):
    """连接管理器

    实现ConnectionManager接口，管理数据库连接的获取和释放。
    提供完整的连接池管理、会话管理和事务管理功能。
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """初始化连接管理器

        Args:
            config: 数据库配置
        """
        self._config = config
        self._engine: Optional[AsyncEngine] = None
        self._pool: Optional[SQLAlchemyConnectionPool] = None
        self._session_manager: Optional[SessionManager] = None
        self._transaction_manager: Optional[TransactionManager] = None
        self._initialized = False
        self._closed = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._stats = SQLAlchemyConnectionStats()

    @property
    def engine(self):
        """获取数据库引擎

        Returns:
            BaseEngineDatabase: 数据库引擎实例

        Raises:
            InfrastructureException: 当引擎未初始化时
        """
        if self._engine is None:
            raise InfrastructureException(
                code=DatabaseErrorCode.ENGINE_NOT_INITIALIZED,
                details={"message": "Database engine is not initialized"}
            )
        return self._engine

    @property
    def session_manager(self) -> SessionManager:
        """获取会话管理器

        Returns:
            SessionManager: 会话管理器实例

        Raises:
            InfrastructureException: 当会话管理器未初始化时
        """
        if self._session_manager is None:
            raise InfrastructureException(
                code=DatabaseErrorCode.SESSION_MANAGER_NOT_INITIALIZED,
                details={"message": "Session manager is not initialized"}
            )
        return self._session_manager

    @property
    def transaction_manager(self) -> TransactionManager:
        """获取事务管理器

        Returns:
            TransactionManager: 事务管理器实例

        Raises:
            InfrastructureException: 当事务管理器未初始化时
        """
        if self._transaction_manager is None:
            raise InfrastructureException(
                code=DatabaseErrorCode.TRANSACTION_MANAGER_NOT_INITIALIZED,
                details={"message": "Transaction manager is not initialized"}
            )
        return self._transaction_manager

    async def initialize(self) -> None:
        """初始化连接管理器"""
        try:
            # 动态导入以避免循环引用
            from idp.framework.infrastructure.db.engines.mysql import MySQLDatabase
            from idp.framework.infrastructure.db.engines.postgres import (
                PostgreSQLDatabase,
            )
            from idp.framework.infrastructure.db.engines.sqlite import SQLiteDatabase

            # 数据库类型到引擎实现的映射
            ENGINE_MAPPING = {
                DatabaseType.POSTGRESQL: PostgreSQLDatabase,
                DatabaseType.MYSQL: MySQLDatabase,
                DatabaseType.SQLITE: SQLiteDatabase
            }

            # 获取对应的引擎实现类
            engine_class = ENGINE_MAPPING.get(self._config.type)
            if not engine_class:
                raise InfrastructureException(
                    code=DatabaseErrorCode.UNSUPPORTED_DATABASE_TYPE,
                    details={
                        "message": f"Unsupported database type: {self._config.type}"}
                )

            # 创建引擎实例 - 确保 application_name 已经在 _create_connection_url 方法中处理，
            # 因此不需要在这里单独处理
            self._engine = engine_class(self._config)
            await self._engine.initialize()

            # 初始化连接池
            if self._engine.engine:
                self._pool = SQLAlchemyConnectionPool(
                    engine=self._engine.engine,
                    pool_size=self._config.pool.min_size,
                    max_overflow=self._config.pool.max_overflow
                )
                await self._pool.initialize()

                # 初始化会话管理器（从session.py导入）
                self._session_manager = SQLAlchemySessionManager(self)

                # 初始化事务管理器（从session.py导入）
                self._transaction_manager = SQLAlchemyTransactionManager(
                    self._session_manager)

            # 启动健康检查
            self._health_check_task = asyncio.create_task(
                self._periodic_health_check()
            )

            logger.info(
                f"Connection manager initialized successfully: {self._config.type}")

        except Exception as e:
            logger.error("Failed to initialize connection manager", exc_info=e)
            raise ConnectionError(
                "Failed to initialize connection manager",
                details={"error": str(e)}
            )

    async def cleanup(self) -> None:
        """清理连接资源"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # 清理连接池
        if self._pool:
            await self._pool.cleanup()
            self._pool = None

        if self._engine:
            try:
                await self._engine.cleanup()
                self._engine = None
                logger.info("Connection manager cleaned up successfully")
            except Exception as e:
                logger.error(f"Failed to dispose database engine: {e}")
                raise InfrastructureException(
                    code=DatabaseErrorCode.CLEANUP_ERROR,
                    details={
                        "message": f"Failed to dispose database engine: {str(e)}"}
                )

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[AsyncConnection, None]:
        """获取数据库连接

        优先使用连接池获取连接，如果连接池未初始化则使用引擎直接获取连接。

        Yields:
            AsyncConnection: 数据库连接
        """
        if not self._engine:
            raise RuntimeError("Engine not initialized")

        try:
            if self._pool:
                async with self._pool.acquire() as connection:
                    self._stats.connection_created()
                    yield connection
                    self._stats.connection_released()
            else:
                # 回退到使用引擎直接获取连接
                async with self._engine.connect() as connection:
                    self._stats.connection_created()
                    try:
                        yield connection
                        self._stats.connection_released()
                    except Exception as e:
                        self._stats.connection_failed(str(e))
                        raise ConnectionError(
                            f"Error using connection: {str(e)}")
        except Exception as e:
            self._stats.connection_failed(str(e))
            raise ConnectionError(f"Error getting connection: {str(e)}")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话

        使用会话管理器创建并获取一个新的数据库会话。

        Yields:
            AsyncSession: 数据库会话
        """
        if not self._session_manager:
            raise InfrastructureException(
                code=DatabaseErrorCode.SESSION_MANAGER_NOT_INITIALIZED,
                details={"message": "Session manager is not initialized"}
            )

        async with self._session_manager.create_session() as session:
            yield session

    @asynccontextmanager
    async def transaction(self, isolation_level: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
        """开始事务

        使用事务管理器创建并获取一个新的事务会话。

        Args:
            isolation_level: 事务隔离级别

        Yields:
            AsyncSession: 数据库会话
        """
        if not self._transaction_manager:
            raise InfrastructureException(
                code=DatabaseErrorCode.TRANSACTION_MANAGER_NOT_INITIALIZED,
                details={"message": "Transaction manager is not initialized"}
            )

        async with self._transaction_manager.transaction(isolation_level) as session:
            yield session

    async def check_health(self) -> bool:
        """检查连接健康状态

        Returns:
            bool: 是否健康
        """
        if self._pool:
            try:
                return await self._pool.check_health()
            except Exception as e:
                logger.warning("Health check failed", exc_info=e)
                return False
        elif self._engine:
            try:
                return await self._engine.check_health()
            except Exception as e:
                logger.warning("Health check failed", exc_info=e)
                return False
        else:
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取连接统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = {
            "total_connections": self._stats.total_connections,
            "active_connections": self._stats.active_connections,
            "idle_connections": self._stats.idle_connections,
            "failed_connections": self._stats.failed_connections,
            "last_error": self._stats.last_error
        }

        # 如果有连接池，添加连接池的统计信息
        if self._pool:
            pool_stats = await self._pool.get_stats()
            stats["pool"] = pool_stats

        # 如果有会话管理器，添加会话统计信息
        if self._session_manager:
            session_stats = await self._session_manager.get_stats()
            stats["session"] = session_stats

        return stats

    async def _periodic_health_check(self) -> None:
        """定期检查数据库健康状态

        每隔指定时间检查数据库连接是否健康，用于及早发现问题。
        """
        if not hasattr(self._config, 'health_check_interval') or not self._config.health_check_interval:
            return

        try:
            while True:
                await asyncio.sleep(self._config.health_check_interval)

                try:
                    is_healthy = await self.check_health()
                    if not is_healthy:
                        logger.warning(
                            f"Database health check failed for {self._config.connection.database}"
                        )
                except Exception as e:
                    logger.error(f"Health check error: {e}")
        except asyncio.CancelledError:
            logger.info("Periodic health check task cancelled")

    async def create_engine(self, url: str, pool_config: Optional[Dict[str, Any]] = None) -> AsyncEngine:
        """创建数据库引擎

        Args:
            url: 数据库连接URL
            pool_config: 连接池配置

        Returns:
            AsyncEngine: SQLAlchemy异步引擎
        """
        from sqlalchemy.ext.asyncio import create_async_engine

        # 设置默认连接池配置
        pool_config = pool_config or {}
        pool_size = pool_config.get("pool_size", 5)
        max_overflow = pool_config.get("max_overflow", 10)
        echo = pool_config.get("echo", False)

        # 创建引擎
        engine = create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=echo
        )

        return engine
