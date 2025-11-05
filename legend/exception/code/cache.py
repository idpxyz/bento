from http import HTTPStatus

from idp.framework.exception.metadata import ErrorCode


class CacheErrorCode(ErrorCode):
    CACHE_OPERATION_ERROR = ErrorCode(
        code="300001",
        message="缓存操作失败",
        http_status=HTTPStatus.INTERNAL_SERVER_ERROR
    )
    
    CACHE_MISS = ErrorCode(
        code="300002",
        message="缓存未命中",
        http_status=HTTPStatus.NOT_FOUND
    )
    
    CACHE_EXPIRED = ErrorCode(
        code="300003",
        message="缓存已过期",
        http_status=HTTPStatus.NOT_FOUND
    )
