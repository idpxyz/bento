from idp.framework.exception.metadata import ErrorCode


class ServiceErrorCode:
    """服务错误码"""
    SERVICE_NOT_FOUND = ErrorCode(
        code="400101",
        message="服务未找到",
        http_status=404
    )
    
    SERVICE_REGISTRATION_ERROR = ErrorCode(
        code="400102",
        message="服务注册失败",
        http_status=500
    )
    
    SERVICE_RESOLUTION_ERROR = ErrorCode(
        code="400103",
        message="服务解析失败",
        http_status=500
    )
    
    SERVICE_UNINITIALIZED = ErrorCode(
        code="400104",
        message="服务未初始化",
        http_status=500
    )
    
    SERVICE_ALREADY_EXISTS = ErrorCode(
        code="400105",
        message="服务已存在",
        http_status=409
    )
    
    SERVICE_INVALID_STATE = ErrorCode(
        code="400106",
        message="服务状态无效",
        http_status=500
    )
    
        