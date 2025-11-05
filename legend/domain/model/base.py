"""领域模型基类

提供聚合根和实体的基础实现。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from idp.framework.domain.model.common import DomainEvent


class Entity:
    """实体基类

    提供实体的基本属性和行为。
    """

    def __init__(self, id: Any):
        self.id = id

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class AggregateRoot(Entity):
    """聚合根基类

    提供聚合根的基本属性和行为，包括领域事件的管理。
    """

    def __init__(self, id: Any):
        super().__init__(id)
        self._events: List[DomainEvent] = []
        self._version: int = 0

    @property
    def version(self) -> int:
        """获取聚合根版本号"""
        return self._version

    def raise_event(self, event: DomainEvent) -> None:
        """触发领域事件

        Args:
            event: 领域事件
        """
        self._events.append(event)

    def collect_events(self) -> List[DomainEvent]:
        """收集并清空领域事件

        Returns:
            领域事件列表
        """
        events = self._events[:]
        self._events.clear()
        return events

    def increment_version(self) -> None:
        """增加版本号"""
        self._version += 1

    def apply_event(self, event: DomainEvent) -> None:
        """应用领域事件

        这个方法应该被子类重写，用于处理特定的领域事件。

        Args:
            event: 领域事件
        """
        pass
