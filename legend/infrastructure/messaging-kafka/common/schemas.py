from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class MessageStatus(str, Enum):
    """
    Status of a message.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class MessageDeliveryStatus(str, Enum):
    """
    Status of a message delivery.
    """
    DELIVERED = "delivered"
    FAILED = "failed"
    PENDING = "pending"


class MessagePriority(str, Enum):
    """
    Priority of a message.
    """
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class MessageHeaders(BaseModel):
    """
    Headers for a message.
    """
    message_id: UUID = Field(default_factory=uuid4)
    correlation_id: Optional[UUID] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str
    destination: Optional[str] = None
    priority: MessagePriority = MessagePriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    content_type: str = "application/json"
    schema_version: str = "1.0.0"
    custom_headers: Dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """
    Base message model.
    """
    headers: MessageHeaders
    payload: Dict[str, Any]
    
    @field_validator("payload")
    def validate_payload(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate payload format. Empty payloads are now allowed.
        """
        return v


class MessageDeliveryResult(BaseModel):
    """
    Result of a message delivery.
    """
    status: MessageDeliveryStatus
    topic: str
    timestamp: str
    error: Optional[str] = None
    partition: Optional[int] = None
    offset: Optional[int] = None
    message_id: Optional[UUID] = None


class TopicConfig(BaseModel):
    """
    Configuration for a Kafka topic.
    """
    name: str
    partitions: int = 3
    replication_factor: int = 3
    configs: Dict[str, str] = Field(default_factory=dict)
    
    @field_validator("name")
    def validate_topic_name(cls, v: str) -> str:
        """
        Validate that the topic name is valid.
        """
        if not v:
            raise ValueError("Topic name cannot be empty")
        if len(v) > 249:
            raise ValueError("Topic name cannot be longer than 249 characters")
        if not all(c.isalnum() or c in ['.', '_', '-'] for c in v):
            raise ValueError("Topic name can only contain alphanumeric characters, dots, underscores, and hyphens")
        return v


class ConsumerGroupInfo(BaseModel):
    """
    Information about a consumer group.
    """
    group_id: str
    topics: List[str]
    members: int
    lag: Dict[str, int] = Field(default_factory=dict)
    status: str


class SchemaInfo(BaseModel):
    """
    Information about a schema.
    """
    subject: str
    version: int
    id: int
    schema: str
    compatibility: str 