from datetime import datetime
from typing import List, Optional

from .entity import Message
from .event import DomainEvent
from .exception import InvalidMessageStateException
from .vo import MessageId, TopicName


class MessageAggregate:
    """消息聚合根"""
    def __init__(self, id: MessageId):
        self.id = id
        self._messages: List[Message] = []
        self._events: List[DomainEvent] = []
    
    @property
    def events(self) -> List[DomainEvent]:
        return self._events.copy()
    
    def clear_events(self) -> None:
        self._events.clear()
    
    def publish(self, topic: TopicName, payload: dict) -> DomainEvent:
        """发布新消息"""
        message = Message(
            id=MessageId(),
            topic=topic,
            payload=payload,
            created_at=datetime.utcnow()
        )
        self._messages.append(message)
        
        event = DomainEvent(
            event_type="message.published",
            payload={"message_id": message.id.value},
            occurred_at=datetime.utcnow(),
            source="message_aggregate",
            correlation_id=str(self.id.value)
        )
        self._events.append(event)
        return event
    
    def process_message(self, message_id: MessageId) -> None:
        """处理消息"""
        message = self._find_message(message_id)
        if message is None:
            raise InvalidMessageStateException(f"Message {message_id.value} not found")
        
        if message.is_processed:
            raise InvalidMessageStateException(f"Message {message_id.value} already processed")
        
        message.mark_as_processed()
        
        event = DomainEvent(
            event_type="message.processed",
            payload={"message_id": message_id.value},
            occurred_at=datetime.utcnow(),
            source="message_aggregate",
            correlation_id=str(self.id.value)
        )
        self._events.append(event)
    
    def retry_message(self, message_id: MessageId) -> None:
        """重试消息"""
        message = self._find_message(message_id)
        if message is None:
            raise InvalidMessageStateException(f"Message {message_id.value} not found")
        
        if not message.can_retry:
            raise InvalidMessageStateException(f"Message {message_id.value} exceeded retry limit")
        
        message.increment_retry_count()
        
        event = DomainEvent(
            event_type="message.retried",
            payload={
                "message_id": message_id.value,
                "retry_count": message.retry_count
            },
            occurred_at=datetime.utcnow(),
            source="message_aggregate",
            correlation_id=str(self.id.value)
        )
        self._events.append(event)
    
    def _find_message(self, message_id: MessageId) -> Optional[Message]:
        """查找消息"""
        return next(
            (msg for msg in self._messages if msg.id == message_id),
            None
        )