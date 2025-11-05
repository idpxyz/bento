from http import HTTPStatus

from idp.framework.exception.metadata import ErrorCode


class UserErrorCode(ErrorCode):
    USER_ALREADY_EXISTS = ErrorCode("100101", "用户已存在", HTTPStatus.CONFLICT)

    USER_NOT_FOUND = ErrorCode("100102", "用户未找到", HTTPStatus.NOT_FOUND)
    
    USER_EMAIL_ALREADY_EXISTS = ErrorCode("100103", "用户邮箱已存在", HTTPStatus.CONFLICT)

    USER_PHONE_ALREADY_EXISTS = ErrorCode("100104", "用户手机号已存在", HTTPStatus.CONFLICT)

    USER_USERNAME_ALREADY_EXISTS = ErrorCode("100105", "用户名已存在", HTTPStatus.CONFLICT)
    
    SERVICE_UNAVAILABLE = ErrorCode("100106", "服务不可用", HTTPStatus.SERVICE_UNAVAILABLE)

    OPERATION_FAILED = ErrorCode("100107", "操作失败", HTTPStatus.INTERNAL_SERVER_ERROR)
