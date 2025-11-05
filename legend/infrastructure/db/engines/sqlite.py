"""SQLite数据库实现模块"""

import os
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from sqlalchemy.engine.url import URL

from idp.framework.infrastructure.db.config import (
    ConnectionConfig,
    CredentialsConfig,
)
from idp.framework.infrastructure.logger import logger_manager

from .base import BaseDatabaseEngine

logger = logger_manager.get_logger(__name__)


class SQLiteDatabase(BaseDatabaseEngine):
    """SQLite数据库实现"""

    def _create_connection_url(self, conn_config: ConnectionConfig, credentials: Optional[CredentialsConfig] = None) -> URL:
        """创建连接URL
        
        Args:
            conn_config: 连接配置
            credentials: 凭证配置（SQLite不使用）
            
        Returns:
            URL: SQLAlchemy URL对象
        """
        # 确保数据库目录存在
        db_path = conn_config.database
        if not db_path.startswith(":memory:"):
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

        return URL.create(
            "sqlite+aiosqlite",
            database=db_path
        )

    def _get_engine_kwargs(self) -> Dict[str, Any]:
        """获取SQLite特定的引擎参数
        
        Returns:
            Dict[str, Any]: 引擎参数
        """
        return {}

    def get_database_type_name(self) -> str:
        """获取数据库类型名称
        
        Returns:
            str: 数据库类型名称
        """
        return "SQLite"

    @asynccontextmanager
    async def _get_replica_session(self, index: int):
        """获取指定副本的会话
        
        SQLite不支持读写分离，直接返回普通会话
        
        Args:
            index: 副本索引（SQLite忽略此参数）
            
        Returns:
            AsyncContextManager[AsyncSession]: 异步会话上下文管理器
        """
        async with self.get_session() as session:
            yield session