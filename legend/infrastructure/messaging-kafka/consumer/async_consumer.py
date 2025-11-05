import asyncio
import json
import uuid
from typing import Any, Callable, Dict, List, Optional, Set, Union

from confluent_kafka import KafkaException
from confluent_kafka import Message as ConfluentMessage
from confluent_kafka import TopicPartition

from idp.framework.infrastructure.messaging.common.logging import (
    get_logger,
    with_context,
)
from idp.framework.infrastructure.messaging.common.metrics import (
    count_messages,
    processing_time,
    record_error,
    record_message_size,
    track_time,
    update_consumer_lag,
)
from idp.framework.infrastructure.messaging.common.schemas import Message, MessageStatus
from idp.framework.infrastructure.messaging.config.settings import get_settings
from idp.framework.infrastructure.messaging.kafka import AsyncConsumer

# Initialize logger
logger = get_logger(__name__)

# Type for message handler functions
MessageHandlerType = Callable[[ConfluentMessage, Message], Any]


class AsyncMessageConsumer:
    """
    Asynchronous Kafka message consumer.
    """

    def __init__(
        self,
        group_id: str,
        topics: List[str],
        client_id: Optional[str] = None,
        bootstrap_servers: Optional[str] = None,
        auto_commit: Optional[bool] = None,
    ) -> None:
        """
        Initialize the consumer.

        Args:
            group_id (str): Consumer group ID
            topics (List[str]): List of topics to subscribe to
            client_id (Optional[str]): Client ID for the consumer
            bootstrap_servers (Optional[str]): Kafka bootstrap servers
            auto_commit (Optional[bool]): Whether to auto-commit offsets
        """
        self.settings = get_settings()
        self.group_id = f"{self.settings.consumer.group_id_prefix}-{group_id}"
        self.client_id = client_id or f"{self.group_id}-{uuid.uuid4()}"
        self.bootstrap_servers = bootstrap_servers or ",".join(
            self.settings.kafka.bootstrap_servers
        )
        self.topics = topics
        self.auto_commit = (
            auto_commit
            if auto_commit is not None
            else self.settings.consumer.enable_auto_commit
        )
        self.consumer: Optional[AsyncConsumer] = None
        self.is_connected = False
        self.is_running = False
        self.handlers: Dict[str, MessageHandlerType] = {}
        self.default_handler: Optional[MessageHandlerType] = None

    async def connect(self) -> None:
        """
        Connect to Kafka.
        """
        if self.is_connected:
            return

        try:
            # Create the consumer
            self.consumer = AsyncConsumer(
                group_id=self.group_id,
                topics=self.topics,
                client_id=self.client_id,
                bootstrap_servers=self.bootstrap_servers,
                auto_commit=self.auto_commit,
            )
            self.is_connected = True

            logger.info(
                "Connected to Kafka",
                client_id=self.client_id,
                group_id=self.group_id,
                topics=self.topics,
                bootstrap_servers=self.bootstrap_servers,
            )
        except Exception as e:
            logger.error(
                "Failed to connect to Kafka",
                error=str(e),
                client_id=self.client_id,
                group_id=self.group_id,
                topics=self.topics,
                bootstrap_servers=self.bootstrap_servers,
            )
            record_error("", "consumer", "connection_error")
            raise

    async def disconnect(self) -> None:
        """
        Disconnect from Kafka.
        """
        if not self.is_connected or not self.consumer:
            return

        try:
            self.is_running = False
            await self.consumer.close()
            self.is_connected = False
            logger.info(
                "Disconnected from Kafka",
                client_id=self.client_id,
                group_id=self.group_id,
            )
        except Exception as e:
            logger.error(
                "Failed to disconnect from Kafka",
                error=str(e),
                client_id=self.client_id,
                group_id=self.group_id,
            )
            record_error("", "consumer", "disconnection_error")

    def register_handler(self, topic: str, handler: MessageHandlerType) -> None:
        """
        Register a handler for a specific topic.

        Args:
            topic (str): Topic to handle
            handler (MessageHandlerType): Handler function
        """
        self.handlers[topic] = handler
        logger.info(
            "Registered handler for topic",
            topic=topic,
            handler=handler.__name__,
        )

    def register_default_handler(self, handler: MessageHandlerType) -> None:
        """
        Register a default handler for all topics.

        Args:
            handler (MessageHandlerType): Handler function
        """
        self.default_handler = handler
        logger.info(
            "Registered default handler",
            handler=handler.__name__,
        )

    @with_context
    @track_time(processing_time, {"operation": "process_message"})
    async def _process_message(self, record: ConfluentMessage) -> None:
        """
        Process a message from Kafka.

        Args:
            record (ConfluentMessage): Message from Kafka
        """
        topic = record.topic()

        try:
            # Count received message
            count_messages(topic, "consumer", "received")

            # Record message size
            if record.value():
                record_message_size(topic, "consumer", len(record.value()))

            # Extract headers
            headers = {}
            if record.headers():
                for header in record.headers():
                    key, value = header
                    if isinstance(value, bytes):
                        try:
                            value = value.decode("utf-8")
                        except UnicodeDecodeError:
                            pass
                    headers[key] = value

            # Extract message ID
            message_id = headers.get("message_id")

            # Parse message value
            value = record.value()
            if isinstance(value, bytes):
                value = value.decode("utf-8")

            # Try to parse as JSON
            if value.startswith("{") and value.endswith("}"):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    pass

            # Create message object
            message = Message(
                headers={
                    "message_id": message_id,
                    "correlation_id": headers.get("correlation_id"),
                    "timestamp": headers.get("timestamp"),
                    "source": headers.get("source", "unknown"),
                    "destination": headers.get("destination"),
                    "content_type": headers.get("content_type", "application/json"),
                },
                payload=value if isinstance(value, dict) else {"value": value},
            )

            # Find handler for topic
            handler = self.handlers.get(topic) or self.default_handler

            if handler:
                # Process message with handler
                logger.info(
                    "Processing message",
                    topic=topic,
                    partition=record.partition(),
                    offset=record.offset(),
                    message_id=message_id,
                )

                # Call handler
                await handler(record, message)

                # Count processed message
                count_messages(topic, "consumer", "processed")
            else:
                logger.warning(
                    "No handler for message",
                    topic=topic,
                    partition=record.partition(),
                    offset=record.offset(),
                )

            # Commit offset if not auto-committing
            if not self.auto_commit and self.consumer:
                await self.consumer.commit(record)
        except Exception as e:
            # Count failed message
            count_messages(topic, "consumer", "error")
            record_error(topic, "consumer", type(e).__name__)

            logger.error(
                "Failed to process message",
                error=str(e),
                topic=topic,
                partition=record.partition(),
                offset=record.offset(),
            )

    async def start_consuming(self) -> None:
        """
        Start consuming messages from Kafka.
        """
        if not self.is_connected or not self.consumer:
            await self.connect()

        self.is_running = True

        try:
            logger.info(
                "Started consuming messages",
                client_id=self.client_id,
                group_id=self.group_id,
                topics=self.topics,
            )

            # Main consumption loop
            while self.is_running:
                try:
                    # Poll for messages
                    message = await self.consumer.poll(timeout=1.0)

                    if message is None:
                        continue

                    if message.error():
                        logger.error(
                            "Consumer error",
                            error=message.error(),
                            client_id=self.client_id,
                            group_id=self.group_id,
                        )
                        continue

                    # Process the message
                    await self._process_message(message)

                    # Update consumer lag metrics
                    for topic in self.topics:
                        for partition in range(
                            0, 10
                        ):  # Assuming max 10 partitions per topic
                            try:
                                tp = TopicPartition(topic, partition)
                                low, high = await self.consumer.get_watermark_offsets(
                                    tp
                                )
                                # Assuming current position is the last committed offset + 1
                                lag = (
                                    max(0, high - (message.offset() + 1))
                                    if message.topic() == topic
                                    and message.partition() == partition
                                    else high - low
                                )
                                update_consumer_lag(topic, self.group_id, lag)
                            except Exception:
                                # Skip if partition doesn't exist
                                pass
                except asyncio.CancelledError:
                    logger.info(
                        "Consumer task cancelled",
                        client_id=self.client_id,
                        group_id=self.group_id,
                    )
                    break
                except Exception as e:
                    logger.error(
                        "Error in consumer loop",
                        error=str(e),
                        client_id=self.client_id,
                        group_id=self.group_id,
                    )
                    record_error("", "consumer", "consumer_loop_error")
                    # Short sleep to avoid tight loop in case of persistent errors
                    await asyncio.sleep(1)
        finally:
            self.is_running = False

    async def stop_consuming(self) -> None:
        """
        Stop consuming messages from Kafka.
        """
        self.is_running = False
        logger.info(
            "Stopped consuming messages",
            client_id=self.client_id,
            group_id=self.group_id,
        )

    async def __aenter__(self) -> "AsyncMessageConsumer":
        """
        Enter async context manager.
        """
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Exit async context manager.
        """
        await self.stop_consuming()
        await self.disconnect()
