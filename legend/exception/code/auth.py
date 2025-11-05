from idp.framework.exception.code import ErrorCode
from idp.framework.exception.metadata import ExceptionCategory, ExceptionSeverity


class AuthErrorCode(ErrorCode):
    AUTH_TOKEN_EXPIRED = ErrorCode(
        code="AUTH_TOKEN_EXPIRED",
        message="认证令牌已过期",
        category=ExceptionCategory.AUTHENTICATION,
        severity=ExceptionSeverity.ERROR
    )