from typing import Generic, List, TypeVar
from uuid import UUID
import contextvars
from ...event import DomainEvent
from ..entity.base import Entity

T = TypeVar('T', bound='AggregateRoot')

current_uow_ctx = contextvars.ContextVar("current_uow", default=None)

class AggregateRoot(Entity, Generic[T]):
    """
    聚合根基类

    所有聚合根都应继承此类，提供领域事件收集功能
    """

    def __init__(self, id: UUID = None):
        """初始化聚合根

        Args:
            id: 聚合根ID，可选
        """
        super().__init__(id)
        self._uncommitted_events: List[DomainEvent] = []
        self._version: int = 0

    @property
    def version(self) -> int:
        """获取聚合根版本"""
        return self._version

    @version.setter
    def version(self, value: int) -> None:
        """设置聚合根版本"""
        if value < 0:
            raise ValueError("Version cannot be negative")
        self._version = value

    def raise_event(self, event: DomainEvent) -> None:
        """
        添加领域事件

        Args:
            event: 要添加的领域事件
        """
        if not isinstance(event, DomainEvent):
            raise TypeError(f"Expected DomainEvent, got {type(event)}")

        # Set aggregate ID and version on the event if not already set
        if not event.aggregate_id:
            event.aggregate_id = self.id
        if not event.version:
            event.version = self.version + 1

        self._uncommitted_events.append(event)
        self.increment_version()

    def clear_events(self) -> None:
        """清除所有事件"""
        self._uncommitted_events.clear()

    def collect_events(self) -> List[DomainEvent]:
        """
        收集并清除所有未发布的事件

        Returns:
            事件列表
        """
        events = self._uncommitted_events.copy()
        self._uncommitted_events.clear()
        return events

    def get_uncommitted_events(self) -> List[DomainEvent]:
        """获取未提交的领域事件"""
        return self._uncommitted_events.copy()

    def clear_uncommitted_events(self) -> None:
        """清除未提交的领域事件"""
        self._uncommitted_events.clear()

    def apply(self, event: DomainEvent) -> None:
        """
        应用事件到聚合根

        用于事件溯源，子类应重写此方法处理特定事件

        Args:
            event: 要应用的领域事件
        """
        if not isinstance(event, DomainEvent):
            raise TypeError(f"Expected DomainEvent, got {type(event)}")

        # Don't increment version here since raise_event will do it
        self.raise_event(event)

    def increment_version(self) -> None:
        """增加版本号"""
        self._version += 1
