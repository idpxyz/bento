from dataclasses import dataclass
from enum import Enum
from http import HTTPStatus
from typing import Any, Dict, Optional

from pydantic import BaseModel


# 异常分类
class ExceptionCategory(str, Enum):
    DOMAIN = "DOMAIN"
    APPLICATION = "APPLICATION"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    INTERFACE = "INTERFACE"

# 异常严重性
class ExceptionSeverity(str, Enum):
    FATAL = "FATAL"
    ERROR = "ERROR"
    WARNING = "WARNING"

# 错误码
@dataclass(frozen=True)
class ErrorCode:
    code: str
    message: str
    http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR

# 定义统一错误响应模型
class ExceptionContext(BaseModel):
    code: str
    message: str
    category: ExceptionCategory
    severity: ExceptionSeverity = ExceptionSeverity.ERROR
    details: Dict[str, Any] = {}
    trace_id: Optional[str] = None