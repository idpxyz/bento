"""数据库会话管理器实现"""

import logging
import sys
import traceback
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from idp.framework.infrastructure.db.core.interfaces import (
    ConnectionManager,
    SessionManager,
    TransactionManager,
)
from idp.framework.infrastructure.db.resilience.errors import DatabaseError
from idp.framework.infrastructure.logger import logger_manager

logger = logger_manager.get_logger(__name__)


class SQLAlchemySessionStats:
    """会话统计信息"""

    def __init__(self) -> None:
        self.total_sessions = 0
        self.active_sessions = 0
        self.committed_sessions = 0
        self.rolled_back_sessions = 0
        self.failed_sessions = 0

    def session_created(self) -> None:
        """记录会话创建"""
        self.total_sessions += 1
        self.active_sessions += 1

    def session_committed(self) -> None:
        """记录会话提交"""
        self.active_sessions -= 1
        self.committed_sessions += 1

    def session_rolled_back(self) -> None:
        """记录会话回滚"""
        self.active_sessions -= 1
        self.rolled_back_sessions += 1

    def session_failed(self) -> None:
        """记录会话失败"""
        self.active_sessions -= 1
        self.failed_sessions += 1


class SQLAlchemySessionManager(SessionManager):
    """会话管理器

    实现SessionManager接口，负责创建和管理数据库会话的生命周期。
    """

    def __init__(self, connection_manager: ConnectionManager) -> None:
        """初始化会话管理器

        Args:
            connection_manager: 连接管理器
        """
        self._connection_manager = connection_manager
        self._session_factory = sessionmaker(
            class_=AsyncSession,
            expire_on_commit=False
        )
        self._stats = SQLAlchemySessionStats()

    @asynccontextmanager
    async def create_session(self) -> AsyncGenerator[AsyncSession, None]:
        """创建数据库会话

        Yields:
            AsyncSession: 数据库会话
        """
        session = None
        try:
            async with self._connection_manager.acquire() as connection:
                session = self._session_factory(bind=connection)
                self._stats.session_created()
                try:
                    yield session
                    await session.commit()
                    self._stats.session_committed()
                except Exception as e:
                    await session.rollback()
                    self._stats.session_rolled_back()
                    raise
        except Exception as e:
            self._stats.session_failed()
            error_message = f"Session error: {str(e)}"
            error_type = type(e).__name__
            logger.error(
                f"Session error occurred: [{error_type}] {error_message}", exc_info=e)

            # Include more detailed error information
            if hasattr(e, '__cause__') and e.__cause__:
                cause = e.__cause__
                error_message += f" Caused by: [{type(cause).__name__}] {str(cause)}"

            raise DatabaseError(
                error_message,
                details={
                    "error": str(e),
                    "error_type": error_type,
                    "traceback": traceback.format_exc() if 'traceback' in sys.modules else None
                }
            )
        finally:
            if session:
                try:
                    await session.close()
                except Exception as close_error:
                    logger.error(
                        f"Error closing session: {close_error}", exc_info=True)

    async def get_stats(self) -> Dict[str, Any]:
        """获取会话统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "total_sessions": self._stats.total_sessions,
            "active_sessions": self._stats.active_sessions,
            "committed_sessions": self._stats.committed_sessions,
            "rolled_back_sessions": self._stats.rolled_back_sessions,
            "failed_sessions": self._stats.failed_sessions
        }


class SQLAlchemyTransactionManager(TransactionManager):
    """事务管理器

    实现TransactionManager接口，负责管理事务的开始和提交。
    基于会话管理器的能力构建，遵循组合优于继承的原则。
    """

    def __init__(self, session_manager: SQLAlchemySessionManager) -> None:
        """初始化事务管理器

        Args:
            session_manager: 会话管理器
        """
        self._session_manager = session_manager

    @asynccontextmanager
    async def begin(self) -> AsyncGenerator[AsyncSession, None]:
        """开始事务

        Yields:
            AsyncSession: 事务会话
        """
        async with self._session_manager.create_session() as session:
            async with session.begin():
                yield session

    @asynccontextmanager
    async def begin_nested(self) -> AsyncGenerator[AsyncSession, None]:
        """开始嵌套事务

        Yields:
            AsyncSession: 事务会话
        """
        async with self._session_manager.create_session() as session:
            async with session.begin_nested():
                yield session

    @asynccontextmanager
    async def transaction(
        self,
        isolation_level: Optional[str] = None
    ) -> AsyncGenerator[AsyncSession, None]:
        """在指定隔离级别下开始事务

        Args:
            isolation_level: 事务隔离级别

        Yields:
            AsyncSession: 数据库会话
        """
        async with self._session_manager.create_session() as session:
            if isolation_level:
                await session.execute(
                    text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
                )
            async with session.begin():
                yield session
