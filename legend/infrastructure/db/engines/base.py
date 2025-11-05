"""数据库引擎基础实现模块"""

import asyncio
import random
import uuid
from abc import abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, Optional

from sqlalchemy import text
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from idp.framework.exception import InfrastructureException
from idp.framework.exception.code import DatabaseErrorCode
from idp.framework.infrastructure.db.config import (
    ConnectionConfig,
    CredentialsConfig,
    DatabaseConfig,
)
from idp.framework.infrastructure.db.core.connection_draining import (
    ConnectionDrainingError,
    connection_tracker,
)
from idp.framework.infrastructure.db.core.context import in_transaction
from idp.framework.infrastructure.db.core.interfaces import ConnectionManager, Database
from idp.framework.infrastructure.logger import logger_manager

logger = logger_manager.get_logger(__name__)


class BaseDatabaseEngine(Database):
    """SQLAlchemy引擎基础数据库实现"""

    def __init__(self, config: DatabaseConfig):
        """初始化基础数据库
        
        Args:
            config: 数据库配置
        """
        super().__init__(config)
        self._engine = None
        self._session_factory = None
        self._read_engines = {}
        self._read_session_factories = {}
        self._health_check_lock = asyncio.Lock()
        self._connection_manager = None  # 将在initialize中初始化

    @property
    def engine(self):
        """获取数据库引擎实例"""
        return self._engine

    @property
    def connection_manager(self) -> Optional[ConnectionManager]:
        """获取连接管理器实例
        
        Returns:
            Optional[ConnectionManager]: 连接管理器实例
        """
        return self._connection_manager

    @abstractmethod
    def _create_connection_url(self, conn_config: ConnectionConfig, credentials: Optional[CredentialsConfig] = None) -> URL:
        """创建连接URL
        
        Args:
            conn_config: 连接配置
            credentials: 凭证配置，如果为None则使用self.config.credentials
            
        Returns:
            URL: SQLAlchemy URL对象
        """
        pass

    @abstractmethod
    def _get_engine_kwargs(self) -> Dict[str, Any]:
        """获取特定引擎的额外参数
        
        Returns:
            Dict[str, Any]: 引擎的额外参数
        """
        return {}

    def get_database_type_name(self) -> str:
        """获取数据库类型名称
        
        Returns:
            str: 数据库类型名称
        """
        return self.config.type.name.lower()

    async def initialize(self) -> None:
        """初始化数据库连接"""
        if self.is_initialized:
            return

        try:
            # 创建主数据库引擎
            engine_kwargs = self._get_engine_kwargs()

            # 确保connect_args存在
            if "connect_args" not in engine_kwargs:
                engine_kwargs["connect_args"] = {}
                
            # 确保server_settings存在
            if "connect_args" in engine_kwargs and "server_settings" not in engine_kwargs["connect_args"]:
                engine_kwargs["connect_args"]["server_settings"] = {}
                
            # 注意：不要在connect_args中直接设置enable_tz_aware_timestamps，而是在server_settings中设置timezone
            if "connect_args" in engine_kwargs and "server_settings" in engine_kwargs["connect_args"]:
                engine_kwargs["connect_args"]["server_settings"]["timezone"] = "UTC"
                
            # 创建引擎
            self._engine = create_async_engine(
                self._create_connection_url(self.config.connection, self.config.credentials),
                pool_size=self.config.pool.min_size,
                max_overflow=self.config.pool.max_overflow,
                pool_timeout=self.config.pool.timeout,
                pool_recycle=self.config.pool.recycle,
                pool_pre_ping=self.config.pool.pre_ping,
                echo=self.config.pool.echo,
                **engine_kwargs
            )

            self._session_factory = async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            # 如果启用读写分离，创建只读副本引擎
            if self.config.read_write.enable_read_write_split:
                for i, replica_config in enumerate(self.config.read_write.read_replicas):
                    replica_engine = create_async_engine(
                        self._create_connection_url(replica_config.connection, replica_config.credentials),
                        pool_size=self.config.pool.min_size,
                        max_overflow=self.config.pool.max_overflow,
                        pool_timeout=self.config.pool.timeout,
                        pool_recycle=self.config.pool.recycle,
                        pool_pre_ping=self.config.pool.pre_ping,
                        echo=self.config.pool.echo,
                        **engine_kwargs
                    )

                    self._read_engines[i] = replica_engine
                    self._read_session_factories[i] = async_sessionmaker(
                        bind=replica_engine,
                        class_=AsyncSession,
                        expire_on_commit=False
                    )

            # 初始化连接管理器（如果有）
            if hasattr(self, '_initialize_connection_manager'):
                self._connection_manager = await self._initialize_connection_manager()

            self._initialized = True
            logger.info(
                f"Initialized {self.get_database_type_name()} connection to {self.config.connection.host or ''}:"
                f"{self.config.connection.port or ''}/{self.config.connection.database}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize {self.get_database_type_name()} connection: {e}")
            raise

    async def cleanup(self) -> None:
        """清理数据库资源
        
        实现优雅的连接耗尽:
        1. 停止接受新连接
        2. 等待现有连接完成（或超时）
        3. 关闭数据库连接池
        """
        if not self.is_initialized:
            return

        try:
            if self.config.enable_draining:
                draining_mode = self.config.draining_mode
                draining_timeout = self.config.draining_timeout
                
                logger.info(
                    f"Starting connection draining process for {self.get_database_type_name()} database: "
                    f"mode={draining_mode}, timeout={draining_timeout}s"
                )
                
                # 开始耗尽过程，停止接受新连接
                await connection_tracker.begin_shutdown()
                
                # 根据耗尽模式执行不同策略
                if draining_mode == "graceful":
                    # 优雅耗尽: 等待现有连接完成，超时后继续
                    connections_closed = await connection_tracker.wait_for_connections_to_close(draining_timeout)
                    if connections_closed:
                        logger.info("All active connections completed successfully")
                    else:
                        active_count = await connection_tracker.get_connection_count()
                        logger.warning(
                            f"Connection draining timed out after {draining_timeout}s, "
                            f"{active_count} active connections remain"
                        )
                elif draining_mode == "force":
                    # 强制耗尽: 立即关闭所有连接
                    await connection_tracker.force_close_all()
                    logger.warning("Forced all connections to close immediately")
                # immediate 模式不等待，直接进行下一步关闭数据库连接
            
            # 清理连接管理器（如果有）
            if self._connection_manager:
                await self._connection_manager.cleanup()
                self._connection_manager = None
            
            # 清理主引擎
            if self._engine:
                await self._engine.dispose()

            # 清理副本引擎
            for engine in self._read_engines.values():
                await engine.dispose()

            self._engine = None
            self._session_factory = None
            self._read_engines.clear()
            self._read_session_factories.clear()
            self._initialized = False

            logger.info(f"Cleaned up {self.get_database_type_name()} connections")
        except Exception as e:
            logger.error(f"Failed to cleanup {self.get_database_type_name()} connections: {e}")
            raise
        finally:
            # 重置连接追踪器状态，以便系统可以在需要时重新初始化
            if self.config.enable_draining:
                await connection_tracker.reset()

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取主数据库会话，并跟踪连接"""
        if not self.is_initialized:
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_NOT_INITIALIZED,
                details={"message": "Database not initialized"}
            )
        
        # 使用连接追踪器包装会话
        try:
            async with connection_tracker.track_connection("session") as conn_id:
                async with self._session_factory() as session:
                    # 设置事务上下文
                    token = in_transaction.set(True)
                    try:
                        # 添加连接信息到会话信息中
                        session.info["connection_id"] = conn_id
                        session.info["tracking_start"] = datetime.utcnow()
                        
                        yield session
                        await session.commit()
                    except Exception as e:
                        await session.rollback()
                        raise
                    finally:
                        in_transaction.reset(token)
        except ConnectionDrainingError:
            # 如果系统正在关闭，抛出特定的错误
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_SHUTTING_DOWN,
                details={"message": "Database is shutting down, no new connections allowed"}
            )

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[AsyncConnection, None]:
        """获取数据库连接
        
        获取一个新的数据库连接。
        
        Yields:
            AsyncConnection: 数据库连接
        
        Raises:
            InfrastructureException: 当连接失败时抛出
        """
        if not self._engine:
            raise InfrastructureException(
                code=DatabaseErrorCode.ENGINE_NOT_INITIALIZED,
                details={"message": "Engine not initialized"}
            )
            
        try:
            connection = await self._engine.connect()
            try:
                # 在使用连接前，验证连接是有效的
                await connection.execute(text("SELECT 1"))
                yield connection
            finally:
                # Ensure connection is closed even if an exception occurs during use
                try:
                    await connection.close()
                except Exception as close_error:
                    logger.error(f"Error closing connection: {close_error}", exc_info=True)
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}", exc_info=True)
            
            # 添加数据库特定错误信息
            error_details = {"error": str(e)}
            
            # 捕获常见的数据库错误并添加详细信息
            if "connection refused" in str(e).lower():
                error_details["reason"] = "Connection refused - database server may be down"
            elif "authentication failed" in str(e).lower():
                error_details["reason"] = "Authentication failed - invalid credentials"
            elif "timeout" in str(e).lower():
                error_details["reason"] = "Connection timeout - server too busy or network issue"
            elif "already closed" in str(e).lower():
                error_details["reason"] = "Connection already closed"
                
            # 添加数据库类型特定信息
            error_details["database_type"] = self.get_database_type_name()
            error_details["host"] = self.config.connection.host
            error_details["port"] = self.config.connection.port
            error_details["database"] = self.config.connection.database
                
            raise InfrastructureException(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                details=error_details
            ) from e

    @asynccontextmanager
    async def _get_replica_session(self, index: int) -> AsyncGenerator[AsyncSession, None]:
        """获取指定副本的会话，并跟踪连接
        
        Args:
            index: 副本索引
            
        Returns:
            AsyncGenerator[AsyncSession, None]: 异步会话生成器
            
        Raises:
            InfrastructureException: 当副本不可用或会话创建失败时
        """
        if not self.is_initialized:
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_NOT_INITIALIZED,
                details={"message": "Database not initialized"}
            )

        session_factory = self._read_session_factories.get(index)
        if not session_factory:
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_INVALID_REPLICA_INDEX,
                details={"message": f"Read replica {index} is not initialized"}
            )

        try:
            async with connection_tracker.track_connection("replica_session") as conn_id:
                async with session_factory() as session:
                    try:
                        # 添加连接信息到会话信息中
                        session.info["connection_id"] = conn_id
                        session.info["replica_index"] = index
                        session.info["tracking_start"] = datetime.utcnow()
                        
                        yield session
                        await session.commit()
                    except Exception as e:
                        await session.rollback()
                        raise
        except ConnectionDrainingError:
            # 如果系统正在关闭，抛出特定的错误
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_SHUTTING_DOWN,
                details={"message": "Database is shutting down, no new connections allowed"}
            )

    async def _execute_query_impl(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """实际的查询执行实现"""
        async with self.get_session() as session:
            try:
                result = await session.execute(text(query), params or {})
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise

    def _prepare_cached_query(self, query: str):
        """准备缓存的查询"""
        async def _cached_query(params: Optional[Dict[str, Any]] = None):
            return await self._execute_query_impl(query, params)
        return _cached_query

    async def check_health(self) -> bool:
        """检查数据库健康状态"""
        try:
            async with asyncio.timeout(self.config.pool.timeout):
                async with self.get_session() as session:
                    await session.execute(text("SELECT 1"))
                    return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {
            "type": self.get_database_type_name(),
            "initialized": self.is_initialized,
            "pool": {
                "min_size": self.config.pool.min_size,
                "max_size": self.config.pool.min_size + self.config.pool.max_overflow,
                "timeout": self.config.pool.timeout,
                "recycle": self.config.pool.recycle
            },
            "read_replicas": {
                "enabled": self.config.read_write.enable_read_write_split,
                "count": len(self._read_engines) if self._read_engines else 0
            }
        }

        # 添加连接池统计信息
        if self._engine:
            pool = self._engine.pool
            stats["pool"].update({
                "size": pool.size(),
                "checked_out": pool.checkedin(),
                "overflow": pool.overflow()
            })
            
        # 添加连接管理器统计信息（如果有）
        if self._connection_manager:
            stats["connection_manager"] = await self._connection_manager.get_stats()

        return stats

    async def check_pool_health(self) -> Dict[str, bool]:
        """检查所有连接池的健康状态"""
        health_status = {
            "main": await self._check_engine_health(self._engine)
        }

        # 检查副本连接池
        for i, engine in self._read_engines.items():
            health_status[f"replica_{i}"] = await self._check_engine_health(engine)

        return health_status

    async def _check_engine_health(self, engine) -> bool:
        """检查单个引擎的健康状态"""
        if not engine:
            return False

        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Engine health check failed: {e}")
            return False

    async def _select_replica_index(self) -> Optional[int]:
        """根据负载均衡策略选择副本索引
        
        重写基类方法，使用副本管理器的负载均衡策略
        
        Returns:
            Optional[int]: 副本索引，如果没有可用的副本则返回None
        """
        # 如果有副本管理器，使用其实现的负载均衡策略
        if hasattr(self, '_replica_manager') and self._replica_manager:
            return await self._replica_manager.select_replica()
            
        # 否则使用基类的简单轮询实现
        strategy = self.config.read_write.load_balance_strategy
        
        # 获取健康的副本
        healthy_replicas = []
        for i in range(len(self.config.read_write.read_replicas)):
            try:
                # 简单的健康检查
                engine = self._read_engines.get(i)
                if engine:
                    async with engine.connect() as conn:
                        await conn.execute(text("SELECT 1"))
                    healthy_replicas.append(i)
            except Exception:
                # 忽略不健康的副本
                pass
                
        if not healthy_replicas:
            return None
            
        # 根据不同策略选择副本
        if strategy == "random":
            # 随机策略
            return random.choice(healthy_replicas)
        elif strategy == "least_connections":
            # 最少连接策略 (简化实现)
            return healthy_replicas[0]  # 实际应用中需要维护连接计数
        else:
            # 默认轮询策略
            self._read_write_index = (self._read_write_index + 1) % len(healthy_replicas)
            return healthy_replicas[self._read_write_index]
            
    async def _initialize_connection_manager(self) -> Optional[ConnectionManager]:
        """初始化连接管理器
        
        需要子类自己实现具体的连接管理器初始化逻辑
        
        Returns:
            Optional[ConnectionManager]: 连接管理器实例
        """
        return None
