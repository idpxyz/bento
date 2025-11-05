from typing import Any, Dict, Optional

from idp.framework.exception.metadata import (
    ErrorCode,
    ExceptionCategory,
    ExceptionContext,
    ExceptionSeverity,
)


class IDPBaseException(Exception):
    """IDP基础异常类

    所有IDP异常的基类，提供统一的异常处理机制
    """

    def __init__(
        self,
        code: ErrorCode,
        category: ExceptionCategory = ExceptionCategory.APPLICATION,
        severity: ExceptionSeverity = ExceptionSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        cause: Optional[Exception] = None,
        **kwargs
    ):
        """初始化异常

        Args:
            code: 错误码
            category: 异常类别
            severity: 严重程度
            details: 详细信息
            trace_id: 跟踪ID
            cause: 原因异常
            **kwargs: 其他扩展字段
        """
        self.context = ExceptionContext(
            code=code.code,
            message=code.message,
            category=category,
            severity=severity,
            details=details or {},
            trace_id=trace_id,
        )

        self.http_status = code.http_status
        self.__cause__ = cause  # 支持异常链上报、日志

        # 调用父类构造函数，message 也参与默认 __str__ 输出
        super().__init__(code.message)

    def to_dict(self) -> Dict[str, Any]:
        """返回异常上下文的字典形式，用于 API 响应"""
        return self.context.model_dump()

    def __str__(self) -> str:
        """返回异常消息，默认使用 message 字段"""
        return self.context.message
