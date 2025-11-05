from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class MessageEnvelope(BaseModel):
    """
    所有发送到消息总线的消息都应包装为此结构，便于统一序列化、日志、追踪
    """
    event_type: str = Field(..., description="领域事件类型")
    payload: Dict[str, Any] = Field(..., description="事件体")
    occurred_at: datetime = Field(default_factory=datetime.utcnow, description="事件发生时间")
    source: str = Field(..., description="事件来源模块/服务")
    correlation_id: str = Field(..., description="请求链路追踪 ID")
