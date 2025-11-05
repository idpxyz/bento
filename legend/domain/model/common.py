"""领域模型通用类型

提供领域事件等通用类型定义。
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Type


class DomainEvent:
    """领域事件基类

    所有领域事件都应继承此类。
    """

    def __init__(
        self,
        aggregate_type: str,
        aggregate_id: Any,
        event_type: str,
        payload: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ):
        """初始化领域事件

        Args:
            aggregate_type: 聚合类型
            aggregate_id: 聚合ID
            event_type: 事件类型
            payload: 事件数据
            metadata: 元数据
            timestamp: 事件发生时间
        """
        self.aggregate_type = aggregate_type
        self.aggregate_id = aggregate_id
        self.event_type = event_type
        self.payload = payload
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"aggregate_type={self.aggregate_type}, "
            f"aggregate_id={self.aggregate_id}, "
            f"event_type={self.event_type}, "
            f"timestamp={self.timestamp})"
        )
