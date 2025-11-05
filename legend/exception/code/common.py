from http import HTTPStatus

from idp.framework.exception.metadata import ErrorCode


# 通用错误码
class CommonErrorCode(ErrorCode):
    # 未知错误
    UNKNOWN_ERROR = ErrorCode("000000", "未知错误", HTTPStatus.INTERNAL_SERVER_ERROR)

    # 参数错误
    INVALID_PARAMS = ErrorCode("000001", "参数错误", HTTPStatus.BAD_REQUEST)

    # 认证错误
    AUTH_ERROR = ErrorCode("000002", "认证错误", HTTPStatus.UNAUTHORIZED)

    # 权限错误
    PERMISSION_ERROR = ErrorCode("000003", "权限错误", HTTPStatus.FORBIDDEN)

    # 资源不存在
    RESOURCE_NOT_FOUND = ErrorCode("000004", "资源不存在", HTTPStatus.NOT_FOUND)

    # 资源已存在
    RESOURCE_ALREADY_EXISTS = ErrorCode("000005", "资源已存在", HTTPStatus.CONFLICT)

    # 资源冲突
    RESOURCE_CONFLICT = ErrorCode("000006", "资源冲突", HTTPStatus.CONFLICT)    

    # 资源已删除
    RESOURCE_DELETED = ErrorCode("000007", "资源已删除", HTTPStatus.GONE)

    # 资源已过期
    RESOURCE_EXPIRED = ErrorCode("000008", "资源已过期", HTTPStatus.GONE)

    # 资源已禁用
    RESOURCE_DISABLED = ErrorCode("000009", "资源已禁用", HTTPStatus.GONE)

    # 资源已锁定
    RESOURCE_LOCKED = ErrorCode("000010", "资源已锁定", HTTPStatus.GONE)
    
    
