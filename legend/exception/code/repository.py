from idp.framework.exception.metadata import ErrorCode


class RepositoryErrorCode(ErrorCode):
    """Repository 错误码"""
    REPOSITORY_NOT_FOUND = ErrorCode(
        code="410101",
        message="Repository 未找到",
        http_status=404
    )
    
    ENTITY_NOT_FOUND = ErrorCode(
        code="410102",
        message="实体未找到",
        http_status=404
    )
    
    OPTIMISTIC_LOCK_ERROR = ErrorCode(
        code="410103",
        message="乐观锁冲突",
        http_status=409
    )
    
    CONFLICT = ErrorCode(
        code="410104",
        message="冲突",
        http_status=409
    )

    CREATE_FAILED = ErrorCode(
        code="410105",
        message="创建失败",
        http_status=500
    )

    
    