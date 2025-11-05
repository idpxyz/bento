"""数据库错误类型定义"""

from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(Enum):
    """错误严重程度分级"""
    NORMAL = "normal"     # 普通错误，可重试
    SEVERE = "severe"     # 严重错误，需要人工介入
    CRITICAL = "critical" # 致命错误，需要立即处理


class DatabaseError(Exception):
    """数据库基础异常类"""
    
    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.NORMAL,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        self.message = message
        self.severity = severity
        self.details = details or {}
        super().__init__(message)


class ConnectionError(DatabaseError):
    """数据库连接错误"""
    
    def __init__(
        self,
        message: str = "Database connection error",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message,
            severity=ErrorSeverity.SEVERE,
            details=details
        )


class QueryError(DatabaseError):
    """查询执行错误"""
    
    def __init__(
        self,
        message: str = "Query execution error",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message,
            severity=ErrorSeverity.NORMAL,
            details=details
        )


class DataCorruptionError(DatabaseError):
    """数据损坏错误"""
    
    def __init__(
        self,
        message: str = "Data corruption detected",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message,
            severity=ErrorSeverity.CRITICAL,
            details=details
        )


class MaxRetriesExceededError(DatabaseError):
    """超过最大重试次数错误"""
    
    def __init__(
        self,
        message: str = "Maximum retry attempts exceeded",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            message,
            severity=ErrorSeverity.SEVERE,
            details=details
        ) 