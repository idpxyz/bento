from loms.shared.platform.errors.error_response import ErrorResponse
from loms.shared.platform.errors.exceptions import AppError
from loms.shared.platform.errors.reason_codes import ReasonCodes
from loms.shared.platform.i18n.renderer import MessageRenderer


class ErrorMapper:
    def __init__(self, reason_codes: ReasonCodes, renderer: MessageRenderer):
        self._rc = reason_codes
        self._renderer = renderer

    def to_http(self, exc: AppError, *, locale: str | None = None):
        if not self._rc.contains(exc.reason_code):
            exc = AppError("VALIDATION_FAILED", "Invalid reason_code emitted by service")

        spec = self._rc.get(exc.reason_code)
        message = self._renderer.render(spec.reason_code, exc.message, locale=locale)

        headers: dict[str, str] = {}
        if spec.retryable and spec.retry_after_hint_seconds:
            headers["Retry-After"] = str(spec.retry_after_hint_seconds)

        body = ErrorResponse(
            code=spec.http_status,
            message=message,
            reason_code=spec.reason_code,
            retryable=spec.retryable,
        )
        return spec.http_status, body, headers
