from typing import Any, Optional

from pydantic import BaseModel

# 通用成功响应模型

class Success(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None

    class Config:
        schema_extra = {
            "example": {"code": 0, "message": "success", "data": None}
        }
