"""Observable Command Handler - CQRS with built-in observability support.

Provides CommandHandler base class with integrated tracing, metrics, and logging.
Use this for critical business commands that need detailed observability.

Example:
    ```python
    from bento.application.cqrs import ObservableCommandHandler
    from bento.application.ports.observability import ObservabilityProvider

    class CreateOrderHandler(ObservableCommandHandler[CreateOrderCommand, Order]):
        def __init__(self, uow: UnitOfWork, observability: ObservabilityProvider):
            super().__init__(uow, observability, "ordering")

        async def handle(self, command: CreateOrderCommand) -> Order:
            async with self.tracer.start_span("create_order") as span:
                try:
                    # ... business logic ...
                    self._record_success("create_order", customer_id=command.customer_id)
                    return order
                except Exception as e:
                    self._record_failure("create_order", "error", error=str(e))
                    raise
    ```
"""

from __future__ import annotations

from typing import Any, TypeVar

from bento.application.cqrs.command_handler import CommandHandler
from bento.application.ports.observability import ObservabilityProvider
from bento.application.ports.uow import UnitOfWork

__all__ = ["ObservableCommandHandler"]

TCommand = TypeVar("TCommand")
TResult = TypeVar("TResult")


class ObservableCommandHandler[TCommand, TResult](CommandHandler[TCommand, TResult]):
    """CommandHandler with built-in observability support.

    Provides:
    - self.tracer: For distributed tracing
    - self.meter: For metrics collection
    - self.logger: For structured logging
    - Helper methods: _record_success(), _record_failure(), _record_duration()

    Use this base class for critical business commands that need detailed observability.
    For simple CRUD operations, use regular CommandHandler.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        observability: ObservabilityProvider,
        context_name: str,
    ) -> None:
        """Initialize observable command handler.

        Args:
            uow: Unit of work for transaction management
            observability: Observability provider for tracing/metrics/logging
            context_name: Context name for tracer/meter/logger (e.g., "ordering", "catalog")
        """
        super().__init__(uow)
        self.tracer = observability.get_tracer(context_name)
        self.meter = observability.get_meter(context_name)
        self.logger = observability.get_logger(context_name)
        self._context_name = context_name

    def _record_success(self, operation: str, **attributes: Any) -> None:
        """Record success metrics for an operation.

        Args:
            operation: Operation name (e.g., "create_order", "update_product")
            **attributes: Additional attributes to attach to the metric

        Example:
            ```python
            self._record_success("create_order", customer_id="123", total=99.99)
            ```
        """
        counter = self.meter.create_counter(f"{operation}_success")
        counter.add(1, attributes)

    def _record_failure(self, operation: str, reason: str, **attributes: Any) -> None:
        """Record failure metrics for an operation.

        Args:
            operation: Operation name (e.g., "create_order", "update_product")
            reason: Failure reason (e.g., "validation_error", "not_found", "timeout")
            **attributes: Additional attributes to attach to the metric

        Example:
            ```python
            self._record_failure("create_order", "validation_error", field="customer_id")
            ```
        """
        counter = self.meter.create_counter(f"{operation}_failed")
        counter.add(1, {"reason": reason, **attributes})

    def _record_duration(self, operation: str, duration_ms: float, **attributes: Any) -> None:
        """Record operation duration.

        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            **attributes: Additional attributes

        Example:
            ```python
            import time
            start = time.time()
            # ... operation ...
            duration_ms = (time.time() - start) * 1000
            self._record_duration("create_order", duration_ms)
            ```
        """
        histogram = self.meter.create_histogram(f"{operation}_duration_ms")
        histogram.record(duration_ms, attributes)
