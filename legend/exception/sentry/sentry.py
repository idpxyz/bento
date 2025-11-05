from typing import Any, Dict, Optional

import sentry_sdk
from fastapi import Request

from idp.framework.core.config import exception_settings
from idp.framework.exception.metadata import ErrorCode, ExceptionCategory
from idp.framework.exception.sentry.sampler import ExceptionSampler


class SentryReporter:
    def __init__(
        self,
        enabled: bool = True,
        environment: str = "dev",
        project: str = "idp-gatekeeper",
        default_level: str = "error"
    ):
        self.enabled = enabled
        self.environment = environment
        self.project = project
        self.level = default_level
        self.sampler = ExceptionSampler()

    async def report_exception(
        self,
        exc: Exception,
        category: Optional[ExceptionCategory] = None,
        request: Optional[Request] = None,
        tags: Optional[Dict[str, str]] = None,
        extras: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        level: Optional[str] = None,
    ):
        if not self.enabled or (category and not self.sampler.should_report(category)):
            return

        try:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("environment", self.environment)
                scope.set_tag("project", self.project)

                if user_id:
                    scope.user = {"id": user_id}
                    scope.set_tag("user_id", user_id)

                if tags:
                    for k, v in tags.items():
                        scope.set_tag(k, v)

                if extras:
                    for k, v in extras.items():
                        scope.set_extra(k, v)

                if request:
                    trace_id = trace_id or getattr(request.state, "trace_id", None)
                    scope.set_tag("path", request.url.path)
                    scope.set_tag("method", request.method)

                if trace_id:
                    scope.set_tag("trace_id", trace_id)

                if hasattr(exc, "__cause__") and exc.__cause__:
                    scope.set_extra("caused_by", repr(exc.__cause__))

                scope.level = level or self.level
                sentry_sdk.capture_exception(exc)
        except Exception as sentry_err:
            print(f"[SentryReporter ERROR] Sentry failed: {sentry_err}")

    async def report_from_error_code(
        self,
        error_code: ErrorCode,
        category: ExceptionCategory,
        request: Optional[Request] = None,
        extra: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        exception: Optional[Exception] = None,
        user_id: Optional[str] = None,
    ):
        exc = exception or Exception(error_code.message)
        await self.report_exception(
            exc=exc,
            category=category,
            request=request,
            trace_id=trace_id,
            user_id=user_id,
            tags={"error_code": error_code.code, "category": category.value},
            extras=extra,
        )


# 全局实例（可注入）
sentry_reporter = SentryReporter(
    enabled=exception_settings.EXCEPTION_SENTRY_ENABLED,
    environment=exception_settings.EXCEPTION_ENVIRONMENT,
    project=exception_settings.EXCEPTION_PROJECT,
)
