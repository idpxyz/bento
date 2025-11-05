"""Pulsar Message Bus - Apache Pulsar implementation of MessageBus protocol.

This module provides the Pulsar adapter for the MessageBus port, enabling
asynchronous event-driven communication using Apache Pulsar.

Features:
- Publish domain events to Pulsar topics
- Subscribe to events with handlers
- Automatic topic management
- Message serialization using codecs
- Graceful startup/shutdown
"""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, cast

import pulsar
from pulsar import ConsumerType

from bento.domain.domain_event import DomainEvent
from bento.messaging.codec import JsonCodec, MessageCodec
from bento.messaging.envelope import MessageEnvelope

from .config import PulsarConfig


class PulsarMessageBus:
    """Apache Pulsar implementation of MessageBus protocol.

    Provides asynchronous message publishing and subscription using Apache Pulsar.

    Features:
    - Event publishing to Pulsar topics
    - Event subscription with handlers
    - Automatic topic derivation from event types
    - JSON serialization (extensible to other codecs)
    - Producer connection pooling
    - Consumer lifecycle management

    Example:
        ```python
        from bento.adapters.messaging.pulsar import PulsarMessageBus, PulsarConfig
        from bento.domain.events import OrderCreatedEvent

        # Initialize
        config = PulsarConfig.from_env()
        bus = PulsarMessageBus(config)

        # Start the bus
        await bus.start()

        # Publish event
        event = OrderCreatedEvent(order_id="123", total=99.99)
        await bus.publish(event)

        # Subscribe to events
        async def handle_order_created(event: OrderCreatedEvent):
            print(f"Order created: {event.order_id}")

        await bus.subscribe(OrderCreatedEvent, handle_order_created)

        # Shutdown
        await bus.stop()
        ```
    """

    def __init__(
        self,
        config: PulsarConfig | None = None,
        codec: MessageCodec | None = None,
        source: str = "bento-service",
    ) -> None:
        """Initialize Pulsar message bus.

        Args:
            config: Pulsar configuration (uses environment config if None)
            codec: Message codec for serialization (uses JSON if None)
            source: Service name for event source tracking
        """
        self.config = config or PulsarConfig.from_env()
        self.codec = codec or JsonCodec()
        self.source = source

        # Pulsar client (lazy-initialized)
        self._client: pulsar.Client | None = None

        # Producer pool (topic -> producer)
        self._producers: dict[str, pulsar.Producer] = {}

        # Consumer pool (topic -> consumer)
        self._consumers: dict[str, pulsar.Consumer] = {}

        # Event handlers (event_type -> list of handlers)
        self._handlers: dict[str, list[Callable[[DomainEvent], Awaitable[None]]]] = {}

        # Consumer tasks (topic -> asyncio.Task)
        self._consumer_tasks: dict[str, asyncio.Task[None]] = {}

        # Lifecycle state
        self._running = False

    # ==================== Lifecycle Management ====================

    async def start(self) -> None:
        """Start the message bus.

        Establishes connection to Pulsar broker and starts event consumers.
        Should be called during application startup.

        Example:
            ```python
            bus = PulsarMessageBus()
            await bus.start()
            ```
        """
        if self._running:
            return

        # Create Pulsar client
        self._client = self._create_client()
        self._running = True

    async def stop(self) -> None:
        """Stop the message bus.

        Gracefully shuts down all consumers and producers, closes connection.
        Should be called during application shutdown.

        Example:
            ```python
            await bus.stop()
            ```
        """
        if not self._running:
            return

        self._running = False

        # Stop all consumer tasks
        for task in self._consumer_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        if self._consumer_tasks:
            await asyncio.gather(*self._consumer_tasks.values(), return_exceptions=True)

        # Close consumers
        for consumer in self._consumers.values():
            consumer.close()

        # Close producers
        for producer in self._producers.values():
            producer.close()

        # Close client
        if self._client:
            self._client.close()

        # Clear state
        self._producers.clear()
        self._consumers.clear()
        self._consumer_tasks.clear()

    # ==================== MessageBus Protocol Implementation ====================

    async def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to Pulsar.

        Args:
            event: Domain event to publish

        Raises:
            RuntimeError: If bus is not started

        Example:
            ```python
            event = OrderCreatedEvent(order_id="123")
            await bus.publish(event)
            ```
        """
        if not self._running:
            raise RuntimeError("MessageBus is not started. Call start() first.")

        # Get event type name
        event_type = self._get_event_type(event)

        # Get topic
        topic = self.config.get_topic_fqn(event_type)

        # Get or create producer
        producer = self._get_or_create_producer(topic)

        # Create envelope
        envelope = MessageEnvelope(
            event_type=event_type,
            payload=self._event_to_dict(event),
            source=self.source,
        )

        # Serialize
        data = self.codec.encode(envelope)

        # Send to Pulsar (sync send for reliability)
        producer.send(data)

    async def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], Awaitable[None]],
    ) -> None:
        """Subscribe to a specific event type.

        Args:
            event_type: Event class to subscribe to
            handler: Async function to handle events

        Example:
            ```python
            async def handle_order(event: OrderCreatedEvent):
                print(f"Order: {event.order_id}")

            await bus.subscribe(OrderCreatedEvent, handle_order)
            ```
        """
        # Get event type name
        event_type_name = self._get_event_type_name(event_type)

        # Register handler
        if event_type_name not in self._handlers:
            self._handlers[event_type_name] = []
        self._handlers[event_type_name].append(handler)

        # Get topic
        topic = self.config.get_topic_fqn(event_type_name)

        # Create consumer if not exists
        if topic not in self._consumers:
            self._create_consumer(topic, event_type_name)

    async def unsubscribe(
        self,
        event_type: type[DomainEvent],
        handler: Callable[[DomainEvent], Awaitable[None]],
    ) -> None:
        """Unsubscribe a handler from an event type.

        Args:
            event_type: Event class to unsubscribe from
            handler: Handler function to remove

        Example:
            ```python
            await bus.unsubscribe(OrderCreatedEvent, handle_order)
            ```
        """
        event_type_name = self._get_event_type_name(event_type)

        if event_type_name in self._handlers:
            try:
                self._handlers[event_type_name].remove(handler)
            except ValueError:
                pass  # Handler not found

    # ==================== Internal Methods ====================

    def _create_client(self) -> pulsar.Client:
        """Create Pulsar client with configuration.

        Returns:
            Pulsar client instance
        """
        kwargs: dict[str, Any] = {
            "service_url": self.config.service_url,
        }

        # TLS configuration
        if self.config.tls_enabled:
            kwargs["tls_trust_certs_file_path"] = self.config.tls_trust_cert_path
            kwargs["tls_validate_hostname"] = self.config.tls_validate_hostname
            kwargs["use_tls"] = True

        # Authentication
        if self.config.auth_token:
            kwargs["authentication"] = pulsar.AuthenticationToken(self.config.auth_token)

        return pulsar.Client(**kwargs)

    def _get_or_create_producer(self, topic: str) -> pulsar.Producer:
        """Get or create producer for topic.

        Args:
            topic: Fully qualified topic name

        Returns:
            Pulsar producer instance
        """
        if topic not in self._producers:
            if self._client is None:
                raise RuntimeError("Pulsar client not initialized")

            self._producers[topic] = self._client.create_producer(topic)

        return self._producers[topic]

    def _create_consumer(self, topic: str, event_type_name: str) -> None:
        """Create consumer for topic and start consumption task.

        Args:
            topic: Fully qualified topic name
            event_type_name: Event type for routing
        """
        if self._client is None:
            raise RuntimeError("Pulsar client not initialized")

        # Create consumer
        consumer = self._client.subscribe(
            topic,
            subscription_name=f"{self.source}-{event_type_name}",
            consumer_type=ConsumerType.Shared,
        )

        self._consumers[topic] = consumer

        # Start consumption task
        task = asyncio.create_task(self._consume_messages(consumer, event_type_name))
        self._consumer_tasks[topic] = task

    async def _consume_messages(self, consumer: pulsar.Consumer, event_type_name: str) -> None:
        """Consume messages from Pulsar and dispatch to handlers.

        Args:
            consumer: Pulsar consumer
            event_type_name: Event type for handler routing
        """
        while self._running:
            try:
                # Receive message (blocking with timeout)
                msg = consumer.receive(timeout_millis=1000)

                # Decode envelope
                envelope = self.codec.decode(msg.data())

                # Get handlers
                handlers = self._handlers.get(event_type_name, [])

                if not handlers:
                    # No handlers registered
                    consumer.acknowledge(msg)
                    continue

                # Dispatch to all handlers
                for handler in handlers:
                    try:
                        # Convert payload to event object
                        event = self._dict_to_event(envelope.payload, event_type_name)
                        await handler(event)
                    except Exception as e:
                        # Log error but continue processing
                        print(f"Error in handler for {event_type_name}: {e}")

                # Acknowledge message
                consumer.acknowledge(msg)

            except Exception as e:
                # Timeout or other errors (ignore timeout)
                if "Pulsar error: TimeOut" not in str(e):
                    print(f"Error consuming message: {e}")
                await asyncio.sleep(0.1)

    @staticmethod
    def _get_event_type(event: DomainEvent) -> str:
        """Get event type name from event instance.

        Args:
            event: Domain event instance

        Returns:
            Event type name (e.g., "order.OrderCreated")
        """
        return f"{event.__class__.__module__}.{event.__class__.__name__}"

    @staticmethod
    def _get_event_type_name(event_type: type[DomainEvent]) -> str:
        """Get event type name from event class.

        Args:
            event_type: Domain event class

        Returns:
            Event type name
        """
        return f"{event_type.__module__}.{event_type.__name__}"

    @staticmethod
    def _event_to_dict(event: DomainEvent) -> dict[str, Any]:
        """Convert domain event to dictionary.

        Args:
            event: Domain event instance

        Returns:
            Dictionary representation
        """
        # Assume event has __dict__ or similar
        to_dict_method = getattr(event, "to_dict", None)
        if callable(to_dict_method):
            return cast(dict[str, Any], to_dict_method())
        elif hasattr(event, "__dict__"):
            return {k: v for k, v in event.__dict__.items() if not k.startswith("_")}
        else:
            return {}

    @staticmethod
    def _dict_to_event(payload: dict[str, Any], event_type_name: str) -> DomainEvent:
        """Convert dictionary to domain event.

        Args:
            payload: Event payload
            event_type_name: Event type name

        Returns:
            Domain event instance (currently returns dict, TODO: proper reconstruction)
        """
        # TODO: Implement proper event reconstruction from registry
        # For now, return the payload as-is (handlers will need to handle dict)
        return payload  # type: ignore
