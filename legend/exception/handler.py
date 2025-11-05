import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from rich import print

# 配置项：是否显示 cause、是否暴露 message
from idp.framework.core.config import exception_settings
from idp.framework.exception.base import IDPBaseException
from idp.framework.exception.metadata import ExceptionCategory
from idp.framework.exception.sentry import sentry_reporter

# 初始化日志
logger = logging.getLogger("idp.exception.handler")


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(IDPBaseException)
    async def handle_app_exception(request: Request, exc: IDPBaseException):
        # 注入 trace_id（如未设置）
        trace_id = getattr(request.state, "trace_id", None)
        if not exc.context.trace_id:
            exc.context.trace_id = trace_id

        category = exc.context.category
        message = f"[{category.value}] {exc.context.code} - {exc.context.message}"

        # ✅ rich 日志输出
        match category:
            case ExceptionCategory.DOMAIN:
                print(f"[bold magenta]{message}[/bold magenta]")
            case ExceptionCategory.APPLICATION:
                print(f"[bold cyan]{message}[/bold cyan]")
            case ExceptionCategory.INFRASTRUCTURE:
                print(f"[bold yellow]{message}[/bold yellow]")
            case ExceptionCategory.INTERFACE:
                print(f"[bold red]{message}[/bold red]")
            case _:
                print(f"[bold]{message}[/bold]")

        if exc.context.details:
            print(f"[dim]Details: {exc.context.details}[/dim]")

        # ✅ cause 打印日志
        if exc.__cause__:
            print(f"[italic red]Caused by: {repr(exc.__cause__)}[/italic red]")

        # ✅ 上报 Sentry（带分类采样），使用异步方法
        try:
            await sentry_reporter.report_exception(
                exc=exc,
                category=category,
                request=request,
                trace_id=trace_id,
                tags={
                    "error_code": exc.context.code,
                    "category": exc.context.category.value,
                },
                extras={"details": exc.context.details}
            )
        except Exception as e:
            logger.error(f"Sentry reporting failed: {e}")

        # ✅ 构造响应内容
        response_data = exc.context.model_dump()

        # 是否隐藏 message（如生产环境）
        if not exception_settings.EXCEPTION_EXPOSE_MESSAGE:
            response_data["message"] = "系统繁忙，请稍后再试"

        # ✅ 调试信息 (只在开发环境)
        # ✅ 开发环境调试日志（强烈建议用 logger.debug 替代 print）
        if exception_settings.EXCEPTION_DEBUG_MODE:
            logger.debug(
                f"[debug] INCLUDE_CAUSE_CONFIG: {exception_settings.EXCEPTION_INCLUDE_CAUSE}")
            logger.debug(f"[debug] EXC CAUSE: {repr(exc.__cause__)}")
            logger.debug(f"[debug] Trace ID: {trace_id}")
            print(
                f"[blue][debug] INCLUDE_CAUSE_CONFIG:[/] {exception_settings.EXCEPTION_INCLUDE_CAUSE}")
            print(f"[blue][debug] EXC CAUSE:[/] {repr(exc.__cause__)}")
        # 是否暴露 cause 到响应体
        if exception_settings.EXCEPTION_INCLUDE_CAUSE and exc.__cause__:
            response_data["caused_by"] = repr(exc.__cause__)

        return JSONResponse(
            status_code=exc.http_status,
            content=response_data
        )
