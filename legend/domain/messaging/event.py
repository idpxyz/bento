from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Generic, TypeVar


@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    payload: Dict[str, Any]
    occurred_at: datetime
    source: str
    correlation_id: str

class MessageRoutingService:
    """消息路由领域服务"""
    def determine_routing_key(self, event: DomainEvent) -> str:
        pass
