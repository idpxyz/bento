from pydantic import BaseModel, Field

class ErrorResponse(BaseModel):
    code: int = Field(..., description="HTTP映射码（与reason_code对应）")
    message: str = Field(..., description="错误信息（可本地化）")
    reason_code: str = Field(..., description="合同冻结 reason_code")
    retryable: bool = Field(..., description="是否可重试（合同冻结）")
