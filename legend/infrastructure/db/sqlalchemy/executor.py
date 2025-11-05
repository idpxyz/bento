"""SQLAlchemy查询执行器实现"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from sqlalchemy import text

from idp.framework.exception import InfrastructureException
from idp.framework.exception.code.database import DatabaseErrorCode
from idp.framework.infrastructure.db.core.interfaces import (
    QueryExecutor,
    SessionManager,
)
from idp.framework.infrastructure.logger import logger_manager

T = TypeVar('T')
R = TypeVar('R')

logger = logger_manager.get_logger(__name__)

class SQLAlchemyQueryExecutor(QueryExecutor[T, R], Generic[T, R]):
    """SQLAlchemy查询执行器"""
    
    def __init__(self, session_manager: SessionManager) -> None:
        """初始化查询执行器
        
        Args:
            session_manager: 会话管理器
        """
        self._session_manager = session_manager
        
    async def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> R:
        """执行查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            R: 查询结果
            
        Raises:
            InfrastructureException: 当查询执行失败时
        """
        async with self._session_manager.create_session() as session:
            try:
                result = await session.execute(text(query), params or {})
                await session.commit()
                return result
            except Exception as e:
                await session.rollback()
                logger.error(f"Query execution failed: {e}")
                raise self._handle_error(e)
                
    async def execute_many(
        self,
        queries: List[str],
        params: Optional[List[Dict[str, Any]]] = None
    ) -> List[R]:
        """批量执行查询
        
        Args:
            queries: SQL查询语句列表
            params: 查询参数列表
            
        Returns:
            List[R]: 查询结果列表
            
        Raises:
            InfrastructureException: 当查询执行失败时
        """
        async with self._session_manager.create_session() as session:
            async with session.begin():
                try:
                    results = []
                    for i, query in enumerate(queries):
                        query_params = params[i] if params else None
                        result = await session.execute(text(query), query_params or {})
                        results.append(result)
                    return results
                except Exception as e:
                    logger.error(f"Batch query execution failed: {e}")
                    raise self._handle_error(e)
                    
    def _handle_error(self, error: Exception) -> InfrastructureException:
        """处理数据库错误
        
        Args:
            error: 原始错误
            
        Returns:
            InfrastructureException: 包装后的错误
        """
        error_msg = str(error).lower()
        if "connection" in error_msg:
            return InfrastructureException(
                code=DatabaseErrorCode.CONNECTION_ERROR,
                details={"message": str(error)}
            )
        elif "timeout" in error_msg:
            return InfrastructureException(
                code=DatabaseErrorCode.TIMEOUT_ERROR,
                details={"message": str(error)}
            )
        elif "deadlock" in error_msg:
            return InfrastructureException(
                code=DatabaseErrorCode.DEADLOCK_ERROR,
                details={"message": str(error)}
            )
        return InfrastructureException(
            code=DatabaseErrorCode.UNKNOWN_ERROR,
            details={"message": str(error)}
        ) 