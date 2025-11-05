from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from .vo import MessageId, TopicName


@dataclass
class Message:
    """消息实体"""
    id: MessageId
    topic: TopicName
    payload: Dict[str, Any]
    created_at: datetime
    processed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    
    @property
    def is_processed(self) -> bool:
        return self.processed_at is not None
    
    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries
    
    def mark_as_processed(self) -> None:
        self.processed_at = datetime.utcnow()
    
    def increment_retry_count(self) -> None:
        self.retry_count += 1 