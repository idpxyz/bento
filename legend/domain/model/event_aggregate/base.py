from typing import TypeVar, Generic, Optional, List, Dict, Any, Type
from idp.framework.domain.event import DomainEvent
from abc import ABC, abstractmethod
from idp.framework.domain.model.aggregate import AggregateRoot, Identifier

T = TypeVar('T')
ID = TypeVar('ID')

class EventSourcedAggregateRoot(AggregateRoot, ABC):
    """事件溯源聚合根基类"""

    def __init__(self, id: Identifier):
        super().__init__(id=id)
        self._version = -1  # 初始版本为-1，表示新创建的聚合根
        self.events: List[DomainEvent] = []

    def get_id(self) -> ID:
        """获取聚合根ID"""
        return self.id
    
    def get_events(self) -> List[DomainEvent]:
        """获取聚合根事件"""
        return self.events
    
    def clear_events(self) -> None:
        """清除聚合根事件"""
        self.events = []
        
    def mutate(self, event: DomainEvent) -> None:
        """处理事件"""
        self.apply(event)
        self.events.append(event)
        
    def apply(self, event: DomainEvent) -> None:
        """应用事件"""
        pass
    
    def get_uncommitted_events(self) -> List[DomainEvent]:
        """获取未提交的事件"""
        return self.events
    
    def clear_uncommitted_events(self) -> None:
        """清除未提交的事件"""
        self.events = []
    
    def load_from_history(self, events: List[DomainEvent]) -> None:
        """从历史事件中加载聚合根状态"""
        for event in events:
            self.apply_event(event, is_new=False)
            
    def get_version(self) -> int:
        """获取版本号"""
        return self._version
    
    def get_changes(self) -> List[DomainEvent]:
        """获取变更"""
        return self.events

    def get_changes_as_dict(self) -> List[Dict[str, Any]]:
        """获取变更字典"""
        return [event.to_dict() for event in self.events]
    
    def get_changes_as_json(self) -> str:
        """获取变更JSON"""
        return json.dumps(self.get_changes_as_dict())

    def apply_event(self, event: DomainEvent, is_new: bool = True) -> None:
        """应用事件到聚合根状态"""
        # 调用具体的事件处理方法
        event_type = type(event).__name__
        handler_method = f"apply_{event_type}"
        
        if hasattr(self, handler_method) and callable(getattr(self, handler_method)):
            getattr(self, handler_method)(event)
        else:
            raise ValueError(f"No handler method found for event type {event_type}")
        
        # 如果是新事件，添加到未提交事件列表
        if is_new:
            self.add_domain_event(event)
        
        # 增加版本
        self.increment_version()

    @classmethod
    def create_from_events(cls, id: Identifier, events: List[DomainEvent]) -> 'EventSourcedAggregateRoot':
        """从事件历史创建聚合根"""
        aggregate = cls(id)
        aggregate.load_from_history(events)
        return aggregate
