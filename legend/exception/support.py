"""异步任务异常处理支持

此模块提供专门的异步任务异常处理功能，适用于FastAPI应用中的后台任务、
定时任务和其他不在请求-响应生命周期内的异步操作。
"""

import asyncio
import contextlib
import functools
import logging
import traceback
from typing import Any, Awaitable, Callable, Dict, Optional, TypeVar

from idp.framework.exception.base import IDPBaseException
from idp.framework.exception.metadata import ErrorCode, ExceptionCategory
from idp.framework.exception.sentry import sentry_reporter

# 类型变量
T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])

# 日志
logger = logging.getLogger("idp.exception.async")


async def handle_background_exception(
    exc: Exception,
    error_code: Optional[ErrorCode] = None,
    category: Optional[ExceptionCategory] = None,
    task_name: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """处理异步后台任务中抛出的异常
    
    此函数负责:
    1. 记录详细日志
    2. 上报Sentry
    3. 可选的自定义处理逻辑
    
    Args:
        exc: 捕获的异常
        error_code: 错误码
        category: 异常类别
        task_name: 任务名称，用于日志和上下文
        details: 附加详情
    """
    # 准备上下文信息
    task_info = task_name or asyncio.current_task().get_name() if asyncio.current_task() else "unknown_task"
    task_details = details or {}
    task_details["task_name"] = task_info
    
    # 获取当前异常的完整堆栈信息
    exc_info = traceback.format_exc()
    
    # 如果是已知的IDP异常，保持原有类别
    if isinstance(exc, IDPBaseException):
        error_code = getattr(exc, "error_code", None)
        category = getattr(exc.context, "category", None)
        
        logger.error(
            f"Background task '{task_info}' failed with {exc.__class__.__name__}: "
            f"{getattr(exc, 'message', str(exc))}"
        )
    else:
        logger.error(
            f"Background task '{task_info}' failed with unexpected error: {str(exc)}\n{exc_info}"
        )
    
    # 上报Sentry
    if error_code:
        await sentry_reporter.report_exception(
            exc=exc,
            category=category,
            tags={"task_name": task_info},
            extras={"details": task_details, "traceback": exc_info}
        )


@contextlib.asynccontextmanager
async def background_task_context(
    task_name: str,
    error_code: Optional[ErrorCode] = None,
):
    """异步后台任务的上下文管理器，提供异常处理
    
    Args:
        task_name: 任务名称
        error_code: 处理异常时使用的错误码，如果是未知异常
        
    Yields:
        无返回值，但在上下文中提供异常处理
        
    Example:
        ```python
        async def process_data_job():
            async with background_task_context("process_data", error_code=CommonErrorCode.TASK_FAILED):
                # 任务代码，异常会被自动处理
                data = await fetch_data()
                await process_data(data)
        ```
    """
    try:
        yield
    except Exception as exc:
        await handle_background_exception(
            exc=exc,
            error_code=error_code,
            task_name=task_name
        )
        # 向上重新抛出异常，让调用者能够感知到失败
        raise


def background_task_handler(
    task_name: Optional[str] = None,
    error_code: Optional[ErrorCode] = None,
) -> Callable[[F], F]:
    """装饰器: 为异步后台任务函数提供统一的异常处理
    
    Args:
        task_name: 任务名称，不提供则使用函数名
        error_code: 处理异常时使用的错误码
        
    Returns:
        装饰后的函数
        
    Example:
        ```python
        @background_task_handler(error_code=CommonErrorCode.TASK_FAILED)
        async def process_daily_data():
            # 任务代码，异常会被自动处理
            await fetch_and_process()
        ```
    """
    def decorator(func: F) -> F:
        # 确保任务名称，默认使用函数名
        nonlocal task_name
        if task_name is None:
            task_name = func.__name__
            
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                # 处理异常，但仍然向上传播
                await handle_background_exception(
                    exc=exc,
                    error_code=error_code,
                    task_name=task_name,
                    details={"args": str(args), "kwargs": str(kwargs)}
                )
                raise
                
        return wrapper  # type: ignore
        
    return decorator


class AsyncTaskExceptionMiddleware:
    """中间件：为异步任务管理器提供统一的异常处理
    
    与BackgroundTasks和CeleryTasks等任务系统集成，确保异常被正确处理。
    
    Example:
        ```python
        # FastAPI后台任务集成
        from fastapi import BackgroundTasks
        
        @app.post("/orders/")
        async def create_order(order: OrderCreate, background_tasks: BackgroundTasks):
            # 创建订单...
            
            # 添加带有异常处理的后台任务
            background_tasks.add_task(
                AsyncTaskExceptionMiddleware.wrap_task(
                    process_order, 
                    task_name="process_new_order",
                    error_code=OrderErrorCode.PROCESSING_FAILED
                ),
                order_id=order.id
            )
            
            return {"order_id": order.id}
        ```
    """
    
    @staticmethod
    def wrap_task(
        task_func: Callable[..., Awaitable[Any]], 
        task_name: Optional[str] = None,
        error_code: Optional[ErrorCode] = None
    ) -> Callable[..., Awaitable[Any]]:
        """封装任务函数，添加异常处理
        
        Args:
            task_func: 原始任务函数
            task_name: 任务名称，默认为函数名
            error_code: 处理异常时使用的错误码
            
        Returns:
            封装后的任务函数
        """
        # 使用装饰器实现
        return background_task_handler(
            task_name=task_name,
            error_code=error_code
        )(task_func)
        
    @staticmethod
    async def execute_task(
        task_func: Callable[..., Awaitable[Any]],
        *args: Any,
        task_name: Optional[str] = None,
        error_code: Optional[ErrorCode] = None,
        **kwargs: Any
    ) -> Any:
        """执行异步任务，附带异常处理
        
        Args:
            task_func: 任务函数
            *args: 位置参数
            task_name: 任务名称，默认为函数名
            error_code: 处理异常时使用的错误码
            **kwargs: 关键字参数
            
        Returns:
            任务执行结果
            
        Raises:
            Exception: 任务失败抛出的异常
        """
        actual_task_name = task_name or task_func.__name__
        
        try:
            return await task_func(*args, **kwargs)
        except Exception as exc:
            await handle_background_exception(
                exc=exc,
                error_code=error_code,
                task_name=actual_task_name,
                details={"args": str(args), "kwargs": str(kwargs)}
            )
            raise 