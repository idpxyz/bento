"""SQLAlchemy数据库工厂"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, ClassVar, Optional, TypeVar

from idp.framework.infrastructure.db.config import DatabaseConfig
from idp.framework.infrastructure.db.core.interfaces import (
    ConnectionManager,
    QueryExecutor,
    ReplicaManager,
    SessionManager,
    TransactionManager,
)
from idp.framework.infrastructure.db.sqlalchemy.connection import (
    SQLAlchemyConnectionManager,
)
from idp.framework.infrastructure.db.sqlalchemy.executor import SQLAlchemyQueryExecutor
from idp.framework.infrastructure.db.sqlalchemy.replica import SQLAlchemyReplicaManager
from idp.framework.infrastructure.db.sqlalchemy.session import (
    SQLAlchemySessionManager,
    SQLAlchemyTransactionManager,
)

T = TypeVar('T')
R = TypeVar('R')

class SQLAlchemyDatabaseFactory:
    """SQLAlchemy数据库工厂"""
    
    # 全局实例，用于单例模式
    _instance: ClassVar[Optional['SQLAlchemyDatabaseFactory']] = None
    _instance_lock = asyncio.Lock()
    
    @classmethod
    async def create(cls, config: DatabaseConfig) -> 'SQLAlchemyDatabaseFactory':
        """创建并初始化数据库工厂实例
        
        静态工厂方法，创建并初始化一个新的数据库工厂实例。
        
        Args:
            config: 数据库配置
            
        Returns:
            SQLAlchemyDatabaseFactory: 初始化完成的数据库工厂实例
        """
        factory = cls(config)
        await factory.initialize()
        return factory
    
    @classmethod
    async def get_instance(cls, config: DatabaseConfig) -> 'SQLAlchemyDatabaseFactory':
        """获取或创建数据库工厂的单例实例
        
        如果工厂实例已存在，则返回该实例；否则创建新实例。
        适用于需要跨应用共享同一数据库连接池的场景。
        
        Args:
            config: 数据库配置
            
        Returns:
            SQLAlchemyDatabaseFactory: 数据库工厂单例实例
        """
        async with cls._instance_lock:
            if cls._instance is None:
                cls._instance = await cls.create(config)
            return cls._instance
    
    @classmethod
    @asynccontextmanager
    async def with_factory(cls, config: DatabaseConfig) -> AsyncGenerator['SQLAlchemyDatabaseFactory', None]:
        """创建临时数据库工厂实例的上下文管理器
        
        创建工厂实例，完成后自动清理资源。适用于临时使用场景。
        
        Args:
            config: 数据库配置
            
        Yields:
            SQLAlchemyDatabaseFactory: 数据库工厂实例
        """
        factory = await cls.create(config)
        try:
            yield factory
        finally:
            await factory.cleanup()
    
    def __init__(self, config: DatabaseConfig) -> None:
        """初始化数据库工厂
        
        Args:
            config: 数据库配置
        """
        self._config = config
        self._connection_manager: Optional[ConnectionManager] = None
        self._session_manager: Optional[SessionManager] = None
        self._transaction_manager: Optional[TransactionManager] = None
        self._query_executor: Optional[QueryExecutor] = None
        self._replica_manager: Optional[ReplicaManager] = None
        self._initialized = False
        
    async def initialize(self) -> None:
        """初始化数据库组件"""
        if self._initialized:
            return
            
        # 创建连接管理器
        self._connection_manager = SQLAlchemyConnectionManager(self._config)
        await self._connection_manager.initialize()
        
        # 创建会话管理器
        self._session_manager = SQLAlchemySessionManager(self._connection_manager)
        
        # 创建事务管理器
        self._transaction_manager = SQLAlchemyTransactionManager(self._session_manager)
        
        # 创建查询执行器
        self._query_executor = SQLAlchemyQueryExecutor(self._session_manager)
        
        # 创建副本管理器
        if self._config.read_write.enable_read_write_split:
            self._replica_manager = SQLAlchemyReplicaManager(
                self._config,
                self._connection_manager
            )
            await self._replica_manager.initialize_replicas()
            
        self._initialized = True
        
    async def cleanup(self) -> None:
        """清理数据库资源"""
        if self._connection_manager:
            await self._connection_manager.cleanup()
            self._initialized = False
            
    def get_connection_manager(self) -> ConnectionManager:
        """获取连接管理器"""
        if not self._initialized:
            raise RuntimeError("Database components not initialized")
        return self._connection_manager
        
    def get_session_manager(self) -> SessionManager:
        """获取会话管理器"""
        if not self._initialized:
            raise RuntimeError("Database components not initialized")
        return self._session_manager
        
    def get_transaction_manager(self) -> TransactionManager:
        """获取事务管理器"""
        if not self._initialized:
            raise RuntimeError("Database components not initialized")
        return self._transaction_manager
        
    def get_query_executor(self) -> QueryExecutor[T, R]:
        """获取查询执行器"""
        if not self._initialized:
            raise RuntimeError("Database components not initialized")
        return self._query_executor
        
    def get_replica_manager(self) -> Optional[ReplicaManager]:
        """获取副本管理器
        
        Returns:
            Optional[ReplicaManager]: 副本管理器，如果未启用读写分离则返回None
        """
        if not self._initialized:
            raise RuntimeError("Database components not initialized")
        return self._replica_manager
        
    @property
    def connection_manager(self) -> ConnectionManager:
        """连接管理器属性"""
        return self.get_connection_manager()
        
    @property
    def session_manager(self) -> SessionManager:
        """会话管理器属性"""
        return self.get_session_manager()
        
    @property
    def transaction_manager(self) -> TransactionManager:
        """事务管理器属性"""
        return self.get_transaction_manager()
        
    @property
    def query_executor(self) -> QueryExecutor[T, R]:
        """查询执行器属性"""
        return self.get_query_executor()
        
    @property
    def replica_manager(self) -> Optional[ReplicaManager]:
        """副本管理器属性"""
        return self.get_replica_manager() 
    
