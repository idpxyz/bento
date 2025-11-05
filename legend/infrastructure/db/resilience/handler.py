"""数据库错误处理器实现"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Type

from idp.framework.infrastructure.db.config import DatabaseConfig
from idp.framework.infrastructure.db.resilience.errors import (
    DatabaseError,
    ErrorSeverity,
    MaxRetriesExceededError,
)

logger = logging.getLogger(__name__)


class ErrorContext:
    """错误上下文"""
    
    def __init__(
        self,
        error: Exception,
        operation: str,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        self.error = error
        self.operation = operation
        self.params = params or {}
        self.timestamp = datetime.utcnow()
        self.retry_count = 0


class DatabaseErrorHandler:
    """数据库错误处理器"""
    
    def __init__(self, config: DatabaseConfig) -> None:
        """初始化错误处理器
        
        Args:
            config: 数据库配置
        """
        self._config = config
        self._error_contexts: Dict[str, ErrorContext] = {}
        
    async def handle_error(
        self,
        error: Exception,
        operation: str,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        """处理数据库错误
        
        Args:
            error: 异常对象
            operation: 操作名称
            params: 操作参数
        """
        # 创建或获取错误上下文
        context_key = self._generate_context_key(operation, params)
        error_context = self._error_contexts.get(
            context_key,
            ErrorContext(error, operation, params)
        )
        
        # 记录错误
        self._log_error(error_context)
        
        try:
            if isinstance(error, DatabaseError):
                await self._handle_database_error(error, error_context)
            else:
                await self._handle_unknown_error(error, error_context)
        except Exception as e:
            logger.exception(
                "Error handling failed",
                extra={
                    "original_error": str(error),
                    "handler_error": str(e)
                }
            )
            raise
            
    async def _handle_database_error(
        self,
        error: DatabaseError,
        context: ErrorContext
    ) -> None:
        """处理数据库特定错误"""
        if error.severity == ErrorSeverity.NORMAL:
            await self._handle_normal_error(error, context)
        elif error.severity == ErrorSeverity.SEVERE:
            await self._handle_severe_error(error, context)
        else:  # CRITICAL
            await self._handle_critical_error(error, context)
            
    async def _handle_normal_error(
        self,
        error: DatabaseError,
        context: ErrorContext
    ) -> None:
        """处理普通错误，支持重试"""
        if context.retry_count < self._config.retry_attempts:
            context.retry_count += 1
            retry_delay = self._calculate_retry_delay(context.retry_count)
            
            logger.info(
                "Retrying operation",
                extra={
                    "operation": context.operation,
                    "retry_count": context.retry_count,
                    "delay": retry_delay
                }
            )
            
            await asyncio.sleep(retry_delay)
            # 重试操作将在调用方进行
        else:
            raise MaxRetriesExceededError(
                f"Operation '{context.operation}' failed after {context.retry_count} retries",
                details={
                    "operation": context.operation,
                    "params": context.params,
                    "last_error": str(error)
                }
            )
            
    async def _handle_severe_error(
        self,
        error: DatabaseError,
        context: ErrorContext
    ) -> None:
        """处理严重错误"""
        logger.error(
            "Severe database error occurred",
            extra={
                "error": str(error),
                "operation": context.operation,
                "params": context.params
            }
        )
        # 这里可以添加告警通知等处理
        raise error
        
    async def _handle_critical_error(
        self,
        error: DatabaseError,
        context: ErrorContext
    ) -> None:
        """处理致命错误"""
        logger.critical(
            "Critical database error occurred",
            extra={
                "error": str(error),
                "operation": context.operation,
                "params": context.params
            }
        )
        # 这里可以添加紧急处理逻辑，如通知运维团队等
        raise error
        
    async def _handle_unknown_error(
        self,
        error: Exception,
        context: ErrorContext
    ) -> None:
        """处理未知错误"""
        logger.error(
            "Unknown database error occurred",
            extra={
                "error": str(error),
                "operation": context.operation,
                "params": context.params
            }
        )
        raise error
        
    def _calculate_retry_delay(self, retry_count: int) -> float:
        """计算重试延迟时间（指数退避）"""
        base_delay = self._config.retry_interval
        max_delay = 60  # 最大延迟60秒
        
        delay = base_delay * (2 ** (retry_count - 1))
        return min(delay, max_delay)
        
    def _generate_context_key(
        self,
        operation: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成错误上下文键"""
        if params:
            param_str = str(sorted(params.items()))
        else:
            param_str = ""
        return f"{operation}:{param_str}"
        
    def _log_error(self, context: ErrorContext) -> None:
        """记录错误日志"""
        logger.error(
            "Database error occurred",
            extra={
                "error": str(context.error),
                "operation": context.operation,
                "params": context.params,
                "retry_count": context.retry_count,
                "timestamp": context.timestamp.isoformat()
            }
        ) 