from idp.framework.exception.metadata import ErrorCode


class DomainExceptionCode:
    """领域异常代码"""
    INVALID_SORT_ORDER = ErrorCode(
        code="311001",
        message="Invalid sort order",
        http_status=400,
    )
    """无效的排序顺序"""
    SORT_ORDER_CONFLICT = ErrorCode(
        code="311002",
        message="Sort order conflict",
        http_status=400,
    )
    """排序顺序冲突"""
    DUPLICATE_SORT_ORDER = ErrorCode(
        code="311003",
        message="Duplicate sort order",
        http_status=400,
    )
    """重复的排序顺序"""
    SORT_ORDER_OUT_OF_RANGE = ErrorCode(
        code="311004",
        message="Sort order out of range",
        http_status=400,
    )
    """排序顺序超出范围"""
    SORT_ORDER_MUST_BE_INTEGER = ErrorCode(
        code="311005",
        message="Sort order must be an integer",
        http_status=400,
    )
    """排序顺序必须是整数"""
    SORT_ORDER_MUST_BE_POSITIVE = ErrorCode(
        code="311006",
        message="Sort order must be positive",
        http_status=400,
    )
    """排序顺序必须是正整数"""
    ENTITY_NOT_FOUND = ErrorCode(
        code="311007",
        message="Entity not found",
        http_status=404,
    )
    """实体不存在"""
    
    
    
    
