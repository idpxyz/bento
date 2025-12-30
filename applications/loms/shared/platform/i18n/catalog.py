def t(locale: str, key: str) -> str:
    """Simple translation function."""
    return CATALOG.get(locale, CATALOG.get("en-US", {})).get(key, key)


CATALOG = {
  "zh-CN": {
    # ========================================
    # Bento Framework Reason Codes (汉化覆盖)
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
    # LOMS Business Reason Codes
    # ========================================
    "IDEMPOTENCY_KEY_MISMATCH": "幂等键冲突：同一幂等键对应的请求内容不一致",
    "ADDRESS_INVALID": "地址信息无效",
    "FORBIDDEN_OPERATION": "无权限执行该操作",
    "INVARIANT_VIOLATION": "领域不变量违反",
    "SHIPMENT_STATE_INVALID": "Shipment 状态不允许该操作",
    "LEG_STATE_INVALID": "Leg 状态不允许该操作",
    "LABEL_ALREADY_VOIDED": "Label 已作废",
    "SHIPMENT_ON_HOLD": "Shipment 处于 Hold 状态",
    "HOLD_NOT_ACTIVE": "Hold 不处于生效状态",
    "LEG_INDEX_GAP": "Leg 序号不连续（index gap）",
    "PROVIDER_TRANSIENT": "服务商暂时性错误，可重试",
    "PROVIDER_PERMANENT": "服务商永久性错误，不可重试",
    "INTEGRATION_UNAVAILABLE": "外部集成不可用，可重试",
    "INTEGRATION_TIMEOUT": "外部集成超时，可重试",
    "RATE_NOT_FOUND": "未找到可用费率",
    "LABEL_FORMAT_UNSUPPORTED": "不支持的面单格式",
    "DOCUMENT_MISSING": "缺少必要单证",
    "DOCUMENT_TYPE_UNSUPPORTED": "不支持的单证类型",
    "CUSTOMS_REJECTED": "海关拒绝",
  },
  "en-US": {
    # Bento Framework codes use default English from framework.json
    # LOMS Business codes:
    "IDEMPOTENCY_KEY_MISMATCH": "Idempotency key mismatch: request content differs",
    "ADDRESS_INVALID": "Address is invalid",
    "FORBIDDEN_OPERATION": "Forbidden operation",
    "INVARIANT_VIOLATION": "Invariant violation",
    "SHIPMENT_STATE_INVALID": "Shipment state invalid for operation",
    "LEG_STATE_INVALID": "Leg state invalid for operation",
    "LABEL_ALREADY_VOIDED": "Label already voided",
    "SHIPMENT_ON_HOLD": "Shipment is on hold",
    "HOLD_NOT_ACTIVE": "Hold is not active",
    "LEG_INDEX_GAP": "Leg index gap",
    "PROVIDER_TRANSIENT": "Provider transient error (retryable)",
    "PROVIDER_PERMANENT": "Provider permanent error",
    "INTEGRATION_UNAVAILABLE": "Integration unavailable (retryable)",
    "INTEGRATION_TIMEOUT": "Integration timeout (retryable)",
    "RATE_NOT_FOUND": "Rate not found",
    "LABEL_FORMAT_UNSUPPORTED": "Label format unsupported",
    "DOCUMENT_MISSING": "Document missing",
    "DOCUMENT_TYPE_UNSUPPORTED": "Document type unsupported",
    "CUSTOMS_REJECTED": "Customs rejected",
  }
}
