"""IDP异常处理模块

此模块提供了基于FastAPI的全面异步异常处理功能：

1. 分层异常处理：支持领域、应用、基础设施和接口错误的分类处理
2. 异步友好：所有异常组件都支持异步操作
3. 异常报告：集成Sentry进行异常报告和监控
4. 调试支持：提供详细的错误信息和上下文


主要组件：
- IDPBaseException: 所有IDP异常的基类
- ErrorCode: 错误码定义
- ExceptionCategory: 异常分类枚举
- ExceptionSeverity: 异常严重程度枚举
"""

# 基础异常类型
from idp.framework.exception.base import IDPBaseException
from idp.framework.exception.classified import (
    ApplicationException,
    DomainException,
    InfrastructureException,
    InterfaceException,
)

# 异常处理器
from idp.framework.exception.handler import register_exception_handlers

# 元数据
from idp.framework.exception.metadata import (
    ErrorCode,
    ExceptionCategory,
    ExceptionContext,
    ExceptionSeverity,
)

# Sentry报告
from idp.framework.exception.sentry import sentry_reporter

# 异步任务支持
from idp.framework.exception.support import (
    AsyncTaskExceptionMiddleware,
    background_task_context,
    background_task_handler,
    handle_background_exception,
)

# Swagger集成
from idp.framework.exception.swagger import common_error_response

# 上下文







__all__ = [
    # 基础类
    "IDPBaseException",
    
    # 分类异常
    "DomainException",
    "ApplicationException",
    "InfrastructureException",
    "InterfaceException",
    
    # 元数据
    "ErrorCode",
    "ExceptionCategory",
    "ExceptionSeverity",
    
    # 上下文
    "ExceptionContext",
    
    # 异常处理器
    "register_exception_handlers",
    
    # Swagger
    "common_error_response",
    
    # Sentry
    "sentry_reporter",
    
    # 异步任务
    "background_task_context",
    "background_task_handler",
    "AsyncTaskExceptionMiddleware",
    "handle_background_exception",
] 