"""数据库错误码模块"""

from xmlrpc.client import UNSUPPORTED_ENCODING

from idp.framework.exception.metadata import ErrorCode


class DatabaseErrorCode:
    """数据库错误码"""
    DATABASE_INITIALIZATION_ERROR = ErrorCode(
        code="400101",
        message="数据库初始化失败",
        http_status=500
    )

    DATABASE_CONFIGURATION_ERROR = ErrorCode(
        code="400102",
        message="数据库配置错误",
        http_status=500
    )

    DATABASE_CONNECTION_ERROR = ErrorCode(
        code="400103",
        message="数据库连接失败",
        http_status=500
    )

    DATABASE_SESSION_ERROR = ErrorCode(
        code="400104",
        message="数据库会话错误",
        http_status=500
    )

    DATABASE_QUERY_ERROR = ErrorCode(
        code="400105",
        message="数据库查询失败",
        http_status=500
    )

    DATABASE_TRANSACTION_ERROR = ErrorCode(
        code="400106",
        message="数据库事务错误",
        http_status=500
    )

    DATABASE_RESOURCE_ERROR = ErrorCode(
        code="400107",
        message="数据库资源错误",
        http_status=500
    )

    DATABASE_CONNECTION_POOL_ERROR = ErrorCode(
        code="400108",
        message="数据库连接池错误",
        http_status=500
    )

    DATABASE_STATEMENT_ERROR = ErrorCode(
        code="400109",
        message="数据库语句错误",
        http_status=500
    )

    DATABASE_RESULT_ERROR = ErrorCode(
        code="400110",
        message="数据库结果错误",
        http_status=500
    )

    DATABASE_CACHE_ERROR = ErrorCode(
        code="400111",
        message="数据库缓存错误",
        http_status=500
    )

    DATABASE_CONNECTION_TIMEOUT_ERROR = ErrorCode(
        code="400112",
        message="数据库连接超时",
        http_status=500
    )

    DATABASE_CONNECTION_REFUSED_ERROR = ErrorCode(
        code="400113",
        message="数据库连接拒绝",
        http_status=500
    )

    DATABASE_CONNECTION_CLOSED_ERROR = ErrorCode(
        code="400114",
        message="数据库连接关闭",
        http_status=500
    )

    DATABASE_CONNECTION_LOST_ERROR = ErrorCode(
        code="400115",
        message="数据库连接丢失",
        http_status=500
    )

    DATABASE_CONNECTION_RECONNECT_ERROR = ErrorCode(
        code="400116",
        message="数据库连接重连失败",
        http_status=500
    )

    DATABASE_NOT_FOUND = ErrorCode(
        code="400117",
        message="数据库实例不存在",
        http_status=404
    )

    DATABASE_NOT_INITIALIZED = ErrorCode(
        code="400118",
        message="数据库未初始化",
        http_status=500
    )

    DATABASE_EXECUTION_ERROR = ErrorCode(
        code="400119",
        message="数据库执行错误",
        http_status=500
    )

    DATABASE_INVALID_REPLICA_INDEX = ErrorCode(
        code="400120",
        message="无效的副本索引",
        http_status=500
    )

    DATABASE_QUERY_TIMEOUT = ErrorCode(
        code="400121",
        message="数据库查询超时",
        http_status=500
    )

    DATABASE_HEALTH_CHECK_TIMEOUT = ErrorCode(
        code="400122",
        message="数据库健康检查超时",
        http_status=500
    )

    DATABASE_OPERATION_FAILED = ErrorCode(
        code="400123",
        message="数据库操作失败",
        http_status=500
    )

    DATABASE_TYPE_NOT_SUPPORTED = ErrorCode(
        code="400124",
        message="数据库类型不支持",
        http_status=500
    )

    DATABASE_SHUTTING_DOWN = ErrorCode(
        code="400125",
        message="数据库正在关闭",
        http_status=503
    )

    UNSUPPORTED_DATABASE_TYPE = ErrorCode(
        code="400126",
        message="不支持的数据库类型",
        http_status=500
    )

    ENGINE_NOT_INITIALIZED = ErrorCode(
        code="400127",
        message="引擎未初始化",
        http_status=500
    )

    TRANSACTION_MANAGER_NOT_INITIALIZED = ErrorCode(
        code="400128",
        message="事务管理器未初始化",
        http_status=500
    )

    REPLICA_INITIALIZATION_ERROR = ErrorCode(
        code="400129",
        message="副本初始化失败",
        http_status=500
    )
    
    