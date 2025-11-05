from typing import Any, Dict, Optional


class KafkaError(Exception):
    """
    Base class for Kafka-related exceptions.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class KafkaConnectionError(KafkaError):
    """
    Exception raised when there is an error connecting to Kafka.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(f"Failed to connect to Kafka: {message}", details)


class KafkaProducerError(KafkaError):
    """
    Exception raised when there is an error producing messages to Kafka.
    """
    
    def __init__(
        self,
        message: str,
        topic: Optional[str] = None,
        message_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if topic:
            error_details["topic"] = topic
        if message_id:
            error_details["message_id"] = message_id
        
        super().__init__(f"Failed to produce message to Kafka: {message}", error_details)


class KafkaConsumerError(KafkaError):
    """
    Exception raised when there is an error consuming messages from Kafka.
    """
    
    def __init__(
        self,
        message: str,
        topic: Optional[str] = None,
        group_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if topic:
            error_details["topic"] = topic
        if group_id:
            error_details["group_id"] = group_id
        
        super().__init__(f"Failed to consume message from Kafka: {message}", error_details)


class MessageProcessingError(KafkaError):
    """
    Exception raised when there is an error processing a message.
    """
    
    def __init__(
        self,
        message: str,
        topic: Optional[str] = None,
        message_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if topic:
            error_details["topic"] = topic
        if message_id:
            error_details["message_id"] = message_id
        
        super().__init__(f"Failed to process message: {message}", error_details)


class SchemaRegistryError(KafkaError):
    """
    Exception raised when there is an error with the Schema Registry.
    """
    
    def __init__(
        self,
        message: str,
        subject: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        if subject:
            error_details["subject"] = subject
        
        super().__init__(f"Schema Registry error: {message}", error_details)


class TopicCreationError(KafkaError):
    """
    Exception raised when there is an error creating a topic.
    """
    
    def __init__(
        self,
        message: str,
        topic: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        error_details["topic"] = topic
        
        super().__init__(f"Failed to create topic: {message}", error_details)


class DeadLetterQueueError(KafkaError):
    """
    Exception raised when there is an error with the dead letter queue.
    """
    
    def __init__(
        self,
        message: str,
        original_topic: str,
        dlq_topic: str,
        message_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        error_details = details or {}
        error_details["original_topic"] = original_topic
        error_details["dlq_topic"] = dlq_topic
        if message_id:
            error_details["message_id"] = message_id
        
        super().__init__(f"Dead letter queue error: {message}", error_details) 