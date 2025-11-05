"""数据库模块

提供简化的数据库访问接口，将复杂的工厂模式和组件管理隐藏在易用的API后面。
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional, Type, TypeVar, cast

from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from idp.framework.infrastructure.db.config import DatabaseConfig
from idp.framework.infrastructure.db.core.interfaces import (
    ConnectionManager,
    QueryExecutor,
    ReplicaManager,
    SessionManager,
    TransactionManager,
)
from idp.framework.infrastructure.db.sqlalchemy.factory import SQLAlchemyDatabaseFactory

T = TypeVar('T')
R = TypeVar('R')


class Database:
    """数据库访问门面类

    提供一个简单统一的接口访问数据库功能，隐藏底层复杂性。
    """

    _instance = None
    _lock = asyncio.Lock()
    _initialized = False

    @classmethod
    async def initialize(cls, config: DatabaseConfig) -> 'Database':
        """初始化数据库

        创建并初始化数据库实例，推荐在应用启动时调用一次。

        Args:
            config: 数据库配置

        Returns:
            Database: 数据库实例
        """
        async with cls._lock:
            if cls._instance is None:
                factory = await SQLAlchemyDatabaseFactory.create(config)
                cls._instance = cls(factory)
                cls._initialized = True
            return cls._instance

    @classmethod
    async def cleanup(cls) -> None:
        """清理数据库资源

        在应用关闭时调用，释放数据库连接和资源。
        """
        async with cls._lock:
            if cls._instance:
                await cls._instance._factory.cleanup()
                cls._instance = None
                cls._initialized = False

    @classmethod
    def get_instance(cls) -> 'Database':
        """获取已初始化的数据库实例

        Returns:
            Database: 数据库实例

        Raises:
            RuntimeError: 如果数据库尚未初始化
        """
        if cls._instance is None or not cls._initialized:
            raise RuntimeError(
                "Database not initialized. Call Database.initialize() first")
        return cls._instance

    def __init__(self, factory: SQLAlchemyDatabaseFactory) -> None:
        """初始化数据库实例

        Args:
            factory: 数据库工厂实例
        """
        self._factory = factory
        self._config = factory._config  # 保存配置

    @property
    def config(self) -> DatabaseConfig:
        """获取数据库配置

        Returns:
            DatabaseConfig: 数据库配置
        """
        return self._config

    @property
    def is_initialized(self) -> bool:
        """检查数据库是否已初始化

        Returns:
            bool: 是否已初始化
        """
        return self._initialized

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话

        创建并返回一个数据库会话，会在上下文退出时自动提交或回滚。

        Yields:
            AsyncSession: 数据库会话
        """
        async with self._factory.session_manager.create_session() as session:
            yield session

    # 为了向后兼容，添加 get_session 作为 session 的别名
    get_session = session

    @asynccontextmanager
    async def transaction(self, isolation_level: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
        """开始数据库事务

        创建一个事务会话，会在上下文退出时自动提交成功的事务或回滚失败的事务。

        Args:
            isolation_level: 可选的隔离级别

        Yields:
            AsyncSession: 事务会话
        """
        async with self._factory.transaction_manager.transaction(isolation_level) as session:
            yield session

    @asynccontextmanager
    async def read_replica(self) -> AsyncGenerator[AsyncSession, None]:
        """获取读副本会话

        从只读副本获取会话，适用于读取查询。需要启用读写分离。

        Yields:
            AsyncSession: 读副本会话

        Raises:
            RuntimeError: 如果读写分离未启用
        """
        if not self._factory.replica_manager:
            raise RuntimeError("Read-write split is not enabled")

        replica_index = await self._factory.replica_manager.select_replica()
        if replica_index is None:
            # 如果没有可用的副本，回退到主库
            async with self.session() as session:
                yield session
        else:
            async with self._factory.replica_manager.get_replica_session(replica_index) as session:
                yield session

    # 为了向后兼容，添加 get_read_session 作为 read_replica 的别名
    get_read_session = read_replica

    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """执行查询

        执行单个SQL查询并返回结果。

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            Any: 查询结果
        """
        return await self._factory.query_executor.execute(query, params)

    async def execute_many(self, queries: List[str], params: Optional[List[Dict[str, Any]]] = None) -> List[Any]:
        """批量执行查询

        执行多个SQL查询并返回结果列表。

        Args:
            queries: SQL查询语句列表
            params: 查询参数列表

        Returns:
            List[Any]: 查询结果列表
        """
        return await self._factory.query_executor.execute_many(queries, params)

    async def health_check(self) -> bool:
        """检查数据库健康状态

        Returns:
            bool: 数据库是否健康
        """
        return await self._factory.connection_manager.check_health()

    async def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息

        Returns:
            Dict[str, Any]: 包括会话和连接统计信息
        """
        return {
            "sessions": await self._factory.session_manager.get_stats(),
            "connections": await self._factory.connection_manager.get_stats()
        }

    # 直接访问底层组件的属性
    @property
    def connection_manager(self) -> ConnectionManager:
        """获取连接管理器"""
        return self._factory.connection_manager

    @property
    def session_manager(self) -> SessionManager:
        """获取会话管理器"""
        return self._factory.session_manager

    @property
    def transaction_manager(self) -> TransactionManager:
        """获取事务管理器"""
        return self._factory.transaction_manager

    @property
    def query_executor(self) -> QueryExecutor:
        """获取查询执行器"""
        return self._factory.query_executor

    @property
    def replica_manager(self) -> Optional[ReplicaManager]:
        """获取副本管理器"""
        return self._factory.replica_manager

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[AsyncConnection, None]:
        """获取数据库连接

        获取底层数据库连接，适用于需要直接控制事务或执行低级操作的场景。

        Yields:
            AsyncConnection: 数据库连接
        """
        # 使用连接管理器的acquire方法获取连接
        async with self._factory.connection_manager.acquire() as connection:
            yield connection


# 全局数据库实例，提供方便的单例访问模式
db: Optional[Database] = None


async def initialize_database(config: DatabaseConfig) -> Database:
    """初始化全局数据库实例

    Args:
        config: 数据库配置

    Returns:
        Database: 数据库实例
    """
    global db
    db = await Database.initialize(config)
    if not db or not db.is_initialized:
        raise RuntimeError("Failed to initialize database instance")
    return db


async def cleanup_database() -> None:
    """清理全局数据库资源"""
    global db
    if db:
        await Database.cleanup()
        db = None


def get_database() -> Database:
    """获取全局数据库实例

    Returns:
        Database: 全局数据库实例

    Raises:
        RuntimeError: 如果数据库尚未初始化
    """
    global db
    if db is None or not db.is_initialized:
        raise RuntimeError(
            "Database not initialized. Call initialize_database() first")
    return db


@asynccontextmanager
async def session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话

    全局会话访问函数，创建并返回一个数据库会话。

    Yields:
        AsyncSession: 数据库会话
    """
    db = get_database()
    async with db.session() as session:
        yield session


@asynccontextmanager
async def transaction(isolation_level: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
    """开始全局事务

    全局事务访问函数，创建并返回一个事务会话。

    Args:
        isolation_level: 隔离级别

    Yields:
        AsyncSession: 事务会话
    """
    db = get_database()
    async with db.transaction(isolation_level) as session:
        yield session


@asynccontextmanager
async def read_replica() -> AsyncGenerator[AsyncSession, None]:
    """获取全局读副本会话

    全局读副本访问函数，创建并返回一个读副本会话。

    Yields:
        AsyncSession: 读副本会话
    """
    db = get_database()
    async with db.read_replica() as session:
        yield session


@asynccontextmanager
async def connection() -> AsyncGenerator[AsyncConnection, None]:
    """获取全局数据库连接

    全局连接访问函数，创建并返回一个数据库连接。

    Yields:
        AsyncConnection: 数据库连接
    """
    db = get_database()
    async with db.get_connection() as conn:
        yield conn
