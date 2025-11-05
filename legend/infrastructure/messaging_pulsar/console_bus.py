# infra/messaging/console_bus.py
import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from idp.framework.domain.event import DomainEvent
from idp.framework.infrastructure.messaging.core.base_message import MessageEnvelope
from idp.framework.infrastructure.messaging.core.event_bus import AbstractEventBus

logger = logging.getLogger(__name__)


class ConsoleBus(AbstractEventBus):
    """Simple console-based event bus implementation for testing/debugging."""

    def __init__(self, engine: AsyncEngine = None):
        self._handlers: Dict[str, Callable[[
            MessageEnvelope], Awaitable[None]]] = {}
        self._active = False
        self._engine = engine

    async def publish(self, events: List[DomainEvent]) -> None:
        """Publish a list of domain events."""
        for event in events:
            try:
                event_type = event.event_type
                logger.info(f"[BUS] Publishing event: {event_type}")

                # Get event data including payload
                event_data = {
                    "id": event.event_id,
                    "type": event_type,
                    "aggregate_id": event.aggregate_id,
                    "timestamp": event.timestamp.isoformat(),
                    "version": event.version,
                    "metadata": event.metadata,
                    "payload": event.get_payload()
                }

                # Publish event
                await self.publish_event(
                    event_type=event_type,
                    payload=event_data,
                    source="console_bus",
                    correlation_id=str(event.event_id)
                )
            except Exception as e:
                logger.error(
                    f"Failed to publish event {event_type}: {e}", exc_info=True)
                raise

    async def publish_event(self, event_type: str, payload: dict, source: str, correlation_id: str) -> None:
        """Publish a single event."""
        try:
            logger.info(f"[EVENT] Publishing {event_type}")
            logger.debug(f"[EVENT] Payload: {payload}")
            logger.debug(f"[EVENT] Source: {source}")
            logger.debug(f"[EVENT] Correlation ID: {correlation_id}")

            # Create envelope
            envelope = MessageEnvelope(
                event_type=event_type,
                payload=payload,
                source=source,
                correlation_id=correlation_id
            )

            # Route to handler if registered
            if event_type in self._handlers:
                try:
                    handler = self._handlers[event_type]
                    await handler(envelope)
                    logger.info(f"[EVENT] Successfully handled {event_type}")
                except Exception as e:
                    logger.error(
                        f"Handler failed for {event_type}: {e}", exc_info=True)
                    raise
            else:
                logger.warning(
                    f"[EVENT] No handler registered for {event_type}")

        except Exception as e:
            logger.error(
                f"Failed to publish event {event_type}: {e}", exc_info=True)
            raise

    def register_handler(self, event_type: str, handler: Callable[[MessageEnvelope], Awaitable[None]]) -> None:
        """Register an event handler for a specific event type.

        Args:
            event_type: Type of event to handle
            handler: Async function that takes a MessageEnvelope and returns an Awaitable[None]
        """
        if not callable(handler):
            raise ValueError("Handler must be callable")

        self._handlers[event_type] = handler
        logger.info(f"[BUS] Registered handler for: {event_type}")

    async def run_subscription(self, topic: str) -> None:
        """Start the event bus subscription and process events from the outbox table."""
        if not self._engine:
            raise ValueError("Database engine not configured for event bus")

        if self._active:
            logger.warning("[BUS] Subscription already running")
            return

        self._active = True
        logger.info(f"[BUS] Started subscription on topic: {topic}")

        try:
            while self._active:
                async with self._engine.connect() as conn:
                    # Begin transaction
                    async with conn.begin():
                        # Get unprocessed events
                        result = await conn.execute(
                            text("""
                                SELECT id, aggregate_id, type, payload, tenant_id
                                FROM outbox 
                                WHERE status = 'NEW'
                                ORDER BY created_at ASC
                                LIMIT 10
                                FOR UPDATE SKIP LOCKED
                            """)
                        )
                        events = result.fetchall()

                        if not events:
                            await asyncio.sleep(1)  # Wait before next poll
                            continue

                        for event in events:
                            try:
                                # Create envelope
                                envelope = MessageEnvelope(
                                    event_type=event.type,
                                    payload=event.payload,
                                    source="outbox",
                                    correlation_id=str(event.id)
                                )

                                # Process event
                                if event.type in self._handlers:
                                    handler = self._handlers[event.type]
                                    await handler(envelope)
                                    logger.info(
                                        f"[EVENT] Successfully processed {event.type}")

                                    # Mark as processed
                                    await conn.execute(
                                        text("""
                                            UPDATE outbox 
                                            SET status = 'PROCESSED', 
                                                processed_at = :processed_at 
                                            WHERE id = :id
                                        """),
                                        {
                                            "id": event.id,
                                            "processed_at": datetime.now(timezone.utc)
                                        }
                                    )
                                else:
                                    logger.warning(
                                        f"[EVENT] No handler for {event.type}")
                                    # Mark as failed
                                    await conn.execute(
                                        text("""
                                            UPDATE outbox 
                                            SET status = 'FAILED',
                                                error = 'No handler registered'
                                            WHERE id = :id
                                        """),
                                        {"id": event.id}
                                    )

                            except Exception as e:
                                logger.error(
                                    f"Failed to process event {event.id}: {e}", exc_info=True)
                                # Mark as failed
                                await conn.execute(
                                    text("""
                                        UPDATE outbox 
                                        SET status = 'FAILED',
                                            error = :error
                                        WHERE id = :id
                                    """),
                                    {
                                        "id": event.id,
                                        "error": str(e)
                                    }
                                )

                await asyncio.sleep(0.1)  # Small delay between iterations

        except asyncio.CancelledError:
            logger.info("[BUS] Subscription cancelled")
            self._active = False
        except Exception as e:
            logger.error(f"[BUS] Subscription failed: {e}", exc_info=True)
            self._active = False
            raise
