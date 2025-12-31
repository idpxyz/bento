"""Translation catalog for my-shop application.

This catalog provides translations for:
1. Bento Framework reason codes (覆盖框架默认消息)
2. my-shop business reason codes (业务特定错误码)
"""

CATALOG = {
    "zh-CN": {
        # ========================================
        # Bento Framework Reason Codes (框架错误码)
        # ========================================
        "UNKNOWN_ERROR": "发生未知错误",
        "INVALID_PARAMS": "参数无效",
        "VALIDATION_FAILED": "参数校验失败",
        "NOT_FOUND": "资源不存在",
        "RESOURCE_NOT_FOUND": "资源不存在",
        "CONFLICT": "资源冲突",
        "STATE_CONFLICT": "状态冲突，当前操作不允许",
        "ALREADY_EXISTS": "资源已存在",
        "UNAUTHORIZED": "需要身份认证",
        "FORBIDDEN": "访问被拒绝",
        "RATE_LIMITED": "请求过于频繁",
        "SERVICE_UNAVAILABLE": "服务暂时不可用",
        "DATABASE_ERROR": "数据库操作失败",
        "TIMEOUT": "操作超时",
        "IDEMPOTENCY_CONFLICT": "幂等键冲突",

        # ========================================
        # my-shop Business Reason Codes (业务错误码)
        # ========================================
        # Catalog Context
        "CATEGORY_NOT_FOUND": "分类不存在",
        "CATEGORY_HAS_PRODUCTS": "分类下还有商品，无法删除",
        "PRODUCT_NOT_FOUND": "商品不存在",
        "PRODUCT_OUT_OF_STOCK": "商品库存不足",
        "PRODUCT_INACTIVE": "商品已下架",

        # Identity Context
        "USER_NOT_FOUND": "用户不存在",
        "USER_ALREADY_EXISTS": "用户已存在",
        "INVALID_CREDENTIALS": "用户名或密码错误",
        "EMAIL_ALREADY_EXISTS": "邮箱已被使用",

        # Ordering Context
        "ORDER_NOT_FOUND": "订单不存在",
        "ORDER_CANNOT_BE_CANCELLED": "订单无法取消",
        "ORDER_ALREADY_PAID": "订单已支付",
        "INSUFFICIENT_STOCK": "库存不足",
        "INVALID_ORDER_STATUS": "订单状态无效",

        # Common validation messages with interpolation
        "FIELD_REQUIRED": "字段 {field} 是必需的",
        "FIELD_INVALID": "字段 {field} 格式无效",
        "VALUE_TOO_LONG": "字段 {field} 超过最大长度 {max_length}",
        "VALUE_TOO_SHORT": "字段 {field} 低于最小长度 {min_length}",
        "VALUE_OUT_OF_RANGE": "字段 {field} 超出范围 [{min_value}, {max_value}]",
    },
    "en-US": {
        # ========================================
        # Bento Framework Reason Codes (Framework)
        # ========================================
        "UNKNOWN_ERROR": "Unknown error occurred",
        "INVALID_PARAMS": "Invalid parameters",
        "VALIDATION_FAILED": "Validation failed",
        "NOT_FOUND": "Resource not found",
        "RESOURCE_NOT_FOUND": "Resource not found",
        "CONFLICT": "Resource conflict",
        "STATE_CONFLICT": "State conflict, operation not allowed",
        "ALREADY_EXISTS": "Resource already exists",
        "UNAUTHORIZED": "Authentication required",
        "FORBIDDEN": "Access denied",
        "RATE_LIMITED": "Too many requests",
        "SERVICE_UNAVAILABLE": "Service temporarily unavailable",
        "DATABASE_ERROR": "Database operation failed",
        "TIMEOUT": "Operation timeout",
        "IDEMPOTENCY_CONFLICT": "Idempotency key conflict",

        # ========================================
        # my-shop Business Reason Codes (Business)
        # ========================================
        # Catalog Context
        "CATEGORY_NOT_FOUND": "Category not found",
        "CATEGORY_HAS_PRODUCTS": "Category has products, cannot delete",
        "PRODUCT_NOT_FOUND": "Product not found",
        "PRODUCT_OUT_OF_STOCK": "Product out of stock",
        "PRODUCT_INACTIVE": "Product is inactive",

        # Identity Context
        "USER_NOT_FOUND": "User not found",
        "USER_ALREADY_EXISTS": "User already exists",
        "INVALID_CREDENTIALS": "Invalid username or password",
        "EMAIL_ALREADY_EXISTS": "Email already in use",

        # Ordering Context
        "ORDER_NOT_FOUND": "Order not found",
        "ORDER_CANNOT_BE_CANCELLED": "Order cannot be cancelled",
        "ORDER_ALREADY_PAID": "Order already paid",
        "INSUFFICIENT_STOCK": "Insufficient stock",
        "INVALID_ORDER_STATUS": "Invalid order status",

        # Common validation messages with interpolation
        "FIELD_REQUIRED": "Field {field} is required",
        "FIELD_INVALID": "Field {field} is invalid",
        "VALUE_TOO_LONG": "Field {field} exceeds maximum length {max_length}",
        "VALUE_TOO_SHORT": "Field {field} is below minimum length {min_length}",
        "VALUE_OUT_OF_RANGE": "Field {field} is out of range [{min_value}, {max_value}]",
    },
}
