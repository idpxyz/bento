"""领域事件端口定义。

定义了领域事件系统与外部系统交互的接口(端口)。
这些接口由领域层定义，但由基础设施层实现。
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Awaitable, Dict, List, Type, TypeVar, Optional, Generic
import logging
from ..event import DomainEvent

T = TypeVar('T', bound=DomainEvent)

logger = logging.getLogger("domain.event.ports")

class DomainEventPublisher(Generic[T], ABC):
    """Domain event publisher interface.
    
    This interface defines the contract for publishing domain events.
    """
    
    @abstractmethod
    async def publish(self, event: T) -> None:
        """Publish a single domain event.
        
        Args:
            event: The domain event to publish
        """
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[T]) -> None:
        """Publish multiple domain events in a batch.
        
        Args:
            events: List of domain events to publish
        """
        pass


class DomainEventSubscriber(Generic[T], ABC):
    """Domain event subscriber interface.
    
    This interface defines the contract for subscribing to domain events.
    """
    
    @abstractmethod
    async def subscribe(
        self, 
        event_type: str, 
        handler: Callable[[T], Any],
        group_id: Optional[str] = None
    ) -> None:
        """Subscribe to a specific event type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: The function to call when an event is received
            group_id: Optional consumer group ID
        """
        pass
    
    @abstractmethod
    async def unsubscribe(self, event_type: str) -> None:
        """Unsubscribe from a specific event type.
        
        Args:
            event_type: The type of event to unsubscribe from
        """
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start consuming events."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop consuming events."""
        pass


class EventBusPort(DomainEventPublisher[T], DomainEventSubscriber[T]):
    """事件总线端口
    
    结合了发布和订阅功能的完整事件总线接口。
    该接口由领域层定义，但由基础设施层实现。
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化事件总线"""
        if self.initialized:
            return
        
        # 启动订阅者
        await self.subscriber.start()
        self.initialized = True
        logger.info("Event bus initialized")

    @abstractmethod
    async def shutdown(self, timeout: float = 10.0) -> None:
        """关闭事件总线
        
        Args:
            timeout: 等待任务完成的最大时间（秒）
        """
        if not self.initialized:
            return
        
        # 停止订阅者
        await self.subscriber.stop(timeout)
        
        # 停止发布者
        await self.publisher.stop(timeout)
        
        self.initialized = False
        logger.info("Event bus shut down")
    
    @abstractmethod
    def register_event_type(self, event_type: Type[DomainEvent]) -> None:
        """注册事件类型
        
        Args:
            event_type: 领域事件类型
        """
        pass

    @abstractmethod
    def register_event_types(self, event_types: List[Type[DomainEvent]]) -> None:
        """批量注册多个事件类型
        
        Args:
            event_types: 领域事件类型列表
        """
        pass 