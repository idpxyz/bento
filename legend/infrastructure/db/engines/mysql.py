"""MySQL数据库实现模块"""

from typing import Any, Dict, Optional

from sqlalchemy.engine.url import URL

from idp.framework.infrastructure.db.config import (
    ConnectionConfig,
    CredentialsConfig,
)
from idp.framework.infrastructure.logger import logger_manager

from .base import BaseDatabaseEngine

logger = logger_manager.get_logger(__name__)


class MySQLDatabase(BaseDatabaseEngine):
    """MySQL数据库实现"""

    def _create_connection_url(self, conn_config: ConnectionConfig, credentials: Optional[CredentialsConfig] = None) -> URL:
        """创建连接URL
        
        Args:
            conn_config: 连接配置
            credentials: 凭证配置，如果为None则使用self.config.credentials
            
        Returns:
            URL: SQLAlchemy URL对象
        """
        # 如果没有提供凭证，则使用主数据库凭证
        creds = credentials or self.config.credentials
        
        return URL.create(
            "mysql+aiomysql",
            username=creds.username,
            password=creds.password,
            host=conn_config.host,
            port=conn_config.port,
            database=conn_config.database,
            query={"charset": "utf8mb4"}
        )

    def _get_engine_kwargs(self) -> Dict[str, Any]:
        """获取MySQL特定的引擎参数
        
        Returns:
            Dict[str, Any]: 引擎参数
        """
        return {}

    def get_database_type_name(self) -> str:
        """获取数据库类型名称
        
        Returns:
            str: 数据库类型名称
        """
        return "MySQL"