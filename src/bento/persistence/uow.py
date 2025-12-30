"""Unit of Work implementation for SQLAlchemy.

This module provides UnitOfWork pattern implementation that manages
transactions and coordinates repositories.

Implements Legend's Outbox pattern with:
- ContextVar for automatic event registration from Aggregates
- Dual publishing strategy (immediate + fallback to Outbox)
- SQLAlchemy Event Listener for automatic Outbox persistence
"""

import contextvars
import logging
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential

from bento.application.ports.message_bus import MessageBus
from bento.application.ports.uow import UnitOfWork as IUnitOfWork
from bento.domain.domain_event import DomainEvent
from bento.messaging.idempotency import IdempotencyStore
from bento.messaging.inbox import Inbox
from bento.messaging.outbox import Outbox
from bento.persistence.config import is_outbox_listener_enabled

T = TypeVar("T")

logger = logging.getLogger(__name__)

# ------- ContextVar so Aggregates can push events without DI hell ---------
_current_uow: contextvars.ContextVar["SQLAlchemyUnitOfWork | None"] = contextvars.ContextVar(
    "current_uow", default=None
)


class SQLAlchemyUnitOfWork(IUnitOfWork):
    """SQLAlchemy Unit of Work with Transactional Outbox pattern.

    Manages database transactions and coordinates event publishing using
    the Outbox pattern for guaranteed event delivery.

    Architecture:
        1. Application executes business logic within UoW transaction
        2. Domain events are collected from aggregates
        3. On commit: Both aggregate changes AND events are saved atomically
        4. Separate Outbox Publisher pulls and publishes events asynchronously

    This ensures:
        - Exactly-once event delivery
        - Transactional consistency between data and events
        - Resilience to message broker failures

    Example:
        ```python
        from bento.persistence.outbox.record import SqlAlchemyOutbox

        # Setup (in composition root)
        outbox = SqlAlchemyOutbox(session)
        uow = SQLAlchemyUnitOfWork(session, outbox)
        uow.register_repository(Order, lambda s: OrderRepository(s))

        # Usage (in use case)
        async with uow:
            order = Order.create(...)  # Produces OrderCreated event
            order_repo = uow.repository(Order)
            await order_repo.save(order)
            uow.track(order)  # Track for event collection
            await uow.commit()  # Saves order + event to outbox atomically

        # Separate process: Outbox Publisher
        # Pulls events from outbox table and publishes to event bus
        ```
    """

    def __init__(
        self,
        session: AsyncSession,
        outbox: Outbox,
        repository_factories: dict[type, Callable[[AsyncSession], Any]] | None = None,
        event_bus: MessageBus | None = None,  # Optional: for dual publishing strategy
        inbox: Inbox | None = None,  # Optional: for message deduplication
        idempotency: IdempotencyStore | None = None,  # Optional: for command idempotency
        tenant_id: str = "default",
    ) -> None:
        """Initialize unit of work with Outbox pattern support.

        Args:
            session: SQLAlchemy async session
            outbox: Outbox for transactional event publishing
            repository_factories: Dictionary mapping aggregate types to repository factory functions
            event_bus: Optional event bus for immediate publishing (dual publishing strategy)
            inbox: Optional Inbox for message deduplication
            idempotency: Optional IdempotencyStore for command idempotency
            tenant_id: Tenant identifier for multi-tenant operations
        """
        self._session = session
        self._outbox = outbox
        self._event_bus = event_bus
        self._committed = False
        self._repository_factories: dict[type, Callable[[AsyncSession], Any]] = (
            repository_factories or {}
        )
        self._repositories: dict[type, Any] = {}
        # Port container: manages outbound port implementations (adapters)
        self._port_factories: dict[type, Callable[[AsyncSession], Any]] = {}
        self._ports: dict[type, Any] = {}
        self.pending_events: list[DomainEvent] = []
        self._tracked_aggregates: list[Any] = []  # Track aggregates for event collection
        self._ctx_token: contextvars.Token | None = None
        # Inbox and Idempotency (injected or lazy-loaded)
        self._inbox: Inbox | None = inbox
        self._idempotency: IdempotencyStore | None = idempotency
        self._tenant_id: str = tenant_id
        logger.debug(
            "UoW initialized with outbox: %s, event_bus: %s",
            outbox.__class__.__name__ if outbox else "None",
            event_bus.__class__.__name__ if event_bus else "None",
        )

    def register_repository(
        self, aggregate_type: type, factory: Callable[[AsyncSession], Any]
    ) -> None:
        """Register a repository factory for an aggregate type.

        Args:
            aggregate_type: The aggregate root class
            factory: Function that creates repository instance from session

        Example:
            ```python
            uow.register_repository(Order, lambda s: OrderRepository(s))
            ```
        """
        self._repository_factories[aggregate_type] = factory

    def repository(self, aggregate_type: type[T]) -> T:
        """Get repository for an aggregate type.

        Args:
            aggregate_type: The aggregate root class

        Returns:
            Repository instance for the aggregate type

        Raises:
            ValueError: If repository not registered for the aggregate type

        Example:
            ```python
            order_repo = uow.repository(Order)
            order = await order_repo.find_by_id(order_id)
            ```
        """
        if aggregate_type not in self._repositories:
            if aggregate_type not in self._repository_factories:
                raise ValueError(f"No repository registered for {aggregate_type.__name__}")
            self._repositories[aggregate_type] = self._repository_factories[aggregate_type](
                self._session
            )
        return self._repositories[aggregate_type]

    def register_port(self, port_type: type, factory: Callable[[AsyncSession], Any]) -> None:
        """Register an outbound port implementation (adapter) factory.

        Ports are interfaces defined in the domain layer that the application layer
        depends on. This method registers the infrastructure implementation (adapter)
        that will be provided when the application requests the port.

        This follows the Hexagonal Architecture pattern:
        - Port: Interface defined by the domain/application (what we need)
        - Adapter: Infrastructure implementation (how we implement it)

        Args:
            port_type: The port interface type (e.g., IProductCatalogService)
            factory: Function that creates the adapter instance from session

        Example:
            ```python
            # Register adapter for cross-BC service
            uow.register_port(
                IProductCatalogService,
                lambda s: ProductCatalogAdapter(s)
            )
            ```

        Note:
            - Only register ports that are relevant to the current BC's transaction context
            - Don't use this for global infrastructure services (logging, caching, etc.)
            - The port interface should be defined in the domain/application layer
        """
        self._port_factories[port_type] = factory

    def port(self, port_type: type[T]) -> T:
        """Get the implementation (adapter) for an outbound port.

        This method provides lazy-loaded adapter instances for ports defined by
        the application layer. The adapter is created only on first access and
        then cached for the lifetime of the UoW.

        Args:
            port_type: The port interface type

        Returns:
            Adapter instance implementing the port interface

        Raises:
            ValueError: If no adapter registered for the port type

        Example:
            ```python
            # In application handler
            product_catalog = self.uow.port(IProductCatalogService)
            available, unavailable = await product_catalog.check_products_available([...])
            ```

        Architecture:
            Application Layer → depends on → Port Interface (IProductCatalogService)
                                                ↑
            Infrastructure Layer → implements → Adapter (ProductCatalogAdapter)
        """
        if port_type not in self._ports:
            if port_type not in self._port_factories:
                raise ValueError(
                    f"No adapter registered for port {port_type.__name__}. "
                    f"Register it using uow.register_port({port_type.__name__}, factory)"
                )
            self._ports[port_type] = self._port_factories[port_type](self._session)
        return self._ports[port_type]

    @property
    def session(self) -> AsyncSession:
        """Get underlying session."""
        return self._session

    @property
    def inbox(self) -> Inbox:
        """Get the Inbox for message deduplication.

        Lazily creates SqlAlchemyInbox on first access.

        Returns:
            Inbox instance for the current transaction
        """
        if self._inbox is None:
            from bento.persistence.inbox import SqlAlchemyInbox

            self._inbox = SqlAlchemyInbox(self._session, self._tenant_id)  # type: ignore[assignment]
        return self._inbox  # type: ignore[return-value]

    @property
    def idempotency(self) -> IdempotencyStore:
        """Get the IdempotencyStore for command deduplication.

        Lazily creates SqlAlchemyIdempotency on first access.

        Returns:
            IdempotencyStore instance for the current transaction
        """
        if self._idempotency is None:
            from bento.persistence.idempotency import SqlAlchemyIdempotency

            self._idempotency = SqlAlchemyIdempotency(self._session, self._tenant_id)  # type: ignore[assignment]
        return self._idempotency  # type: ignore[return-value]

    def set_tenant_id(self, tenant_id: str) -> None:
        """Set the tenant ID for multi-tenant operations.

        Args:
            tenant_id: The tenant identifier
        """
        self._tenant_id = tenant_id
        # Reset lazy-loaded instances to use new tenant_id
        self._inbox = None
        self._idempotency = None

    def track(self, aggregate: Any) -> None:
        """Track an aggregate for event collection.

        Repositories should call this when saving aggregates.

        Args:
            aggregate: Aggregate root to track
        """
        if aggregate not in self._tracked_aggregates:
            self._tracked_aggregates.append(aggregate)

    async def begin(self) -> None:
        """Begin a new transaction and register self in ContextVar."""
        # SQLAlchemy sessions don't need explicit begin for async
        # Transaction starts automatically on first operation
        self.pending_events.clear()
        self._tracked_aggregates.clear()
        # Reset lazy-loaded instances for new transaction (if not injected)
        # This ensures each transaction gets fresh instances
        self._inbox = None
        self._idempotency = None

        # Register UoW in session.info for Event Listener access
        # For AsyncSession, we need to set it on the sync_session
        if hasattr(self._session, "sync_session"):
            # AsyncSession - set on sync_session for event listener
            self._session.sync_session.info["uow"] = self
        else:
            # Regular Session
            self._session.info["uow"] = self

        # Register in ContextVar for Aggregate access
        self._ctx_token = _current_uow.set(self)
        logger.debug("UoW session started")

    async def collect_events(self) -> list[DomainEvent]:
        """Collect domain events from tracked aggregates.

        This method:
        1. Iterates through all tracked aggregates
        2. Collects their domain events via the `events` property
        3. Clears events from aggregates (prevent duplicate publishing)
        4. Adds events to pending_events

        Convention:
            Aggregates MUST provide an `events` property that returns
            a list of DomainEvent instances.

        Returns:
            List of collected domain events
        """
        for aggregate in self._tracked_aggregates:
            # Convention: aggregates must have 'events' property
            if hasattr(aggregate, "events"):
                events = getattr(aggregate, "events", [])

                if events:
                    self.pending_events.extend(events)
                    logger.debug(
                        f"Collected {len(events)} events from {aggregate.__class__.__name__}"
                    )

                    # Clear events from aggregate after collecting
                    if hasattr(aggregate, "clear_events"):
                        aggregate.clear_events()
                    elif isinstance(events, list):
                        events.clear()
            else:
                logger.warning(
                    f"{aggregate.__class__.__name__} does not have 'events' property. "
                    f"Aggregates must inherit from AggregateRoot or provide an 'events' property."
                )

        return self.pending_events.copy()

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        """Enter async context."""
        await self.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        """Exit async context, rolling back if not committed."""
        try:
            if exc_type:
                await self.rollback()
            elif not self._committed:
                await self.rollback()
        finally:
            await self._cleanup()

    async def _cleanup(self) -> None:
        """Cleanup resources and reset ContextVar."""
        # Note: Session should be managed by the caller (session factory context)
        # We only reset the ContextVar here
        if self._ctx_token is not None:
            _current_uow.reset(self._ctx_token)
        if hasattr(self._session, "sync_session"):
            self._session.sync_session.info.pop("uow", None)
        else:
            self._session.info.pop("uow", None)
        logger.debug("UoW cleanup completed")

    async def commit(self) -> None:
        """Commit the transaction using dual publishing strategy.

        This method implements Legend's dual publishing pattern:
        1. Collects events from all tracked aggregates
        2. Commits the database transaction (SQLAlchemy Event Listener will
           automatically write events to Outbox table in same transaction)
        3. Attempts immediate publishing with retry (if event_bus is configured)
        4. Falls back to Outbox Projector for guaranteed delivery

        This ensures:
        - Exactly-once delivery via Outbox pattern
        - Low latency for successful immediate publishes
        - Guaranteed delivery via Projector fallback
        """
        # 1. Collect events from aggregates
        await self.collect_events()

        listener_enabled = is_outbox_listener_enabled()

        if self.pending_events and listener_enabled:
            import importlib

            importlib.import_module("bento.persistence.outbox.listener")

        # 2. Persist events to Outbox (if we have an outbox and events)
        # We do this manually because after_flush listeners don't reliably trigger with AsyncSession
        # when there are no entity changes
        if self.pending_events and self._outbox and not listener_enabled:
            from sqlalchemy import select

            from bento.persistence.outbox.record import OutboxRecord

            logger.debug("Persisting %d events to Outbox", len(self.pending_events))

            # Check for existing event IDs to maintain idempotency
            event_ids = [
                getattr(evt, "event_id", None)
                for evt in self.pending_events
                if hasattr(evt, "event_id")
            ]
            existing_ids: set[str] = set()

            if event_ids:
                # Convert UUIDs to strings for SQLite compatibility
                event_id_strs = [str(eid) for eid in event_ids]
                stmt = select(OutboxRecord.id).where(OutboxRecord.id.in_(event_id_strs))
                result = await self._session.execute(stmt)
                existing_ids = {row[0] for row in result}

            # Add events to outbox
            for evt in self.pending_events:
                event_id = getattr(evt, "event_id", None)
                event_id_str = str(event_id) if event_id else None

                # Skip if already exists (idempotency)
                if event_id_str and event_id_str in existing_ids:
                    logger.warning("Event %s already exists in outbox, skipping", event_id_str)
                    continue

                try:
                    record = OutboxRecord.from_domain_event(evt)
                    self._session.add(record)
                    logger.debug("Added event %s to outbox", event_id_str or "N/A")
                except Exception as e:
                    logger.error("Failed to add event to outbox: %s", str(e), exc_info=True)
                    raise

        # 3. Commit transaction
        await self._session.commit()
        self._committed = True
        logger.debug("Database transaction committed")

        # 4. Optional: Attempt immediate publishing (dual publishing strategy)
        if self._event_bus and self.pending_events:
            logger.info("Attempting immediate publishing of %d events", len(self.pending_events))
            try:
                await self._publish_with_retry(self.pending_events)
                logger.info("Events published immediately, success!")  # Keep INFO for success
            except RetryError as retry_error:
                # Retry exhausted - events are already in Outbox, Projector will handle
                logger.warning(
                    "Immediate publishing failed after retries: %s. "
                    "Events are in Outbox, Projector will publish them.",
                    str(retry_error),
                )
            finally:
                # Always clear after commit (whether immediate publish succeeded or not)
                self.pending_events.clear()
        else:
            logger.debug("No event bus configured or no events, relying on Projector")
            self.pending_events.clear()

        # Events in Outbox will be published by Projector

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5))
    async def _publish_with_retry(self, events: Sequence[DomainEvent]) -> None:
        """Publish events with retry (at-least-once semantics).

        Args:
            events: Domain events to publish

        Raises:
            RetryError: If all retry attempts are exhausted
        """
        if self._event_bus is None:
            raise RuntimeError("Event bus not configured")

        logger.debug("Publishing %d events (attempt)", len(events))
        try:
            await self._event_bus.publish(list(events))
            logger.debug("Events published successfully")
        except Exception as e:
            logger.error("Failed to publish events: %s", str(e), exc_info=True)
            raise

    def _register_event(self, evt: DomainEvent) -> None:
        """Register event from Aggregate (called via ContextVar helper).

        Args:
            evt: Domain event to register
        """
        logger.debug(
            "Registering event: %s (id=%s)", evt.__class__.__name__, getattr(evt, "event_id", "N/A")
        )
        self.pending_events.append(evt)

    def _serialize_event(self, event: DomainEvent) -> dict:
        """Serialize domain event to dict for Outbox storage.

        Args:
            event: Domain event to serialize

        Returns:
            Serializable dictionary representation
        """
        from dataclasses import asdict, is_dataclass

        # For dataclasses, use asdict()
        if is_dataclass(event):
            return asdict(event)
        # Fallback to __dict__
        elif hasattr(event, "__dict__"):
            return {k: v for k, v in event.__dict__.items() if not k.startswith("_")}
        else:
            return {"event_type": event.__class__.__name__}

    async def rollback(self) -> None:
        """Rollback the transaction and discard collected events."""
        logger.info("Rolling back transaction")
        await self._session.rollback()
        self.pending_events.clear()
        self._tracked_aggregates.clear()


# -------------------- helper for AggregateRoot ---------------------------


def register_event_from_aggregate(evt: DomainEvent) -> None:
    """Called inside AggregateRoot.raise_event() to push into current UoW.

    This helper function allows Aggregates to register events without
    depending on the UoW directly, using ContextVar for decoupling.

    Args:
        evt: Domain event to register

    Example:
        ```python
        # Inside AggregateRoot
        def raise_event(self, event: DomainEvent):
            from bento.persistence.uow import register_event_from_aggregate
            register_event_from_aggregate(event)
        ```
    """
    uow = _current_uow.get(None)
    if uow:
        logger.debug("Registering event from aggregate: %s", evt.__class__.__name__)
        uow._register_event(evt)
    else:
        logger.warning(
            "No active UoW found when registering event from aggregate. "
            "Event will not be published: %s",
            evt.__class__.__name__,
        )


class UnitOfWorkFactory:
    """Factory for creating UnitOfWork instances with Outbox support.

    Example:
        ```python
        from bento.persistence.outbox.record import SqlAlchemyOutbox

        factory = UnitOfWorkFactory(session_factory)
        uow = await factory.create()
        ```
    """

    def __init__(self, session_factory: Any) -> None:
        """Initialize factory.

        Args:
            session_factory: Callable that creates async sessions
        """
        self._session_factory = session_factory

    async def create(self) -> SQLAlchemyUnitOfWork:
        """Create a new UnitOfWork instance with Outbox.

        Returns:
            New UnitOfWork instance configured with Outbox pattern
        """
        from bento.persistence.outbox.record import SqlAlchemyOutbox

        session = self._session_factory()
        outbox = SqlAlchemyOutbox(session)
        return SQLAlchemyUnitOfWork(session, outbox)


# Convenience alias
UnitOfWork = SQLAlchemyUnitOfWork
