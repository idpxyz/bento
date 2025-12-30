"""Ship order command and use case."""

from dataclasses import dataclass

from bento.application import ObservableCommandHandler, command_handler
from bento.application.ports.observability import ObservabilityProvider
from bento.application.ports.uow import UnitOfWork

# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException

from contexts.ordering.domain.models.order import Order


@dataclass
class ShipOrderCommand:
    """Ship order command.

    Note: Idempotency is handled by IdempotencyMiddleware at HTTP layer.
    """

    order_id: str
    tracking_number: str | None = None


@command_handler
class ShipOrderHandler(ObservableCommandHandler[ShipOrderCommand, Order]):
    """Ship order use case.

    订单发货。
    发布 OrderShipped 事件。
    """

    def __init__(self, uow: UnitOfWork, observability: ObservabilityProvider) -> None:
        super().__init__(uow, observability, "ordering")

    async def validate(self, command: ShipOrderCommand) -> None:
        """Validate command."""
        if not command.order_id:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "order_id", "reason": "cannot be empty"},
            )

    async def handle(self, command: ShipOrderCommand) -> Order:
        """Handle command execution."""
        async with self.tracer.start_span("ship_order") as span:
            span.set_attribute("order_id", command.order_id)
            if command.tracking_number:
                span.set_attribute("tracking_number", command.tracking_number)

            self.logger.info(
                "Shipping order", order_id=command.order_id, tracking_number=command.tracking_number
            )

            try:
                from contexts.ordering.infrastructure.repositories.order_repository_impl import (
                    OrderRepository,
                )

                order_repo = OrderRepository(self.uow._session)  # type: ignore

                # 获取订单
                order = await order_repo.get(command.order_id)
                if not order:
                    self._record_failure("ship_order", "order_not_found")
                    self.logger.error("Order not found", order_id=command.order_id)
                    raise ApplicationException(
                        reason_code="NOT_FOUND",
                        details={"resource": "order", "id": command.order_id},
                    )

                # 发货（领域方法会自动发布 OrderShippedEvent）
                try:
                    order.ship(tracking_number=command.tracking_number)
                except ValueError as e:
                    self._record_failure("ship_order", "invalid_state", error=str(e))
                    self.logger.error(
                        "Invalid order state for shipping", order_id=command.order_id, error=str(e)
                    )
                    raise ApplicationException(
                        reason_code="INVALID_PARAMS",
                        details={"reason": str(e)},
                    ) from e

                # 保存
                await order_repo.save(order)

                # Record success
                self._record_success(
                    "ship_order",
                    order_id=command.order_id,
                    has_tracking=command.tracking_number is not None,
                )

                span.set_status("ok")
                self.logger.info("Order shipped successfully", order_id=command.order_id)

                return order

            except ApplicationException:
                raise
            except Exception as e:
                span.record_exception(e)
                span.set_status("error", str(e))
                self._record_failure("ship_order", "unexpected_error", error_type=type(e).__name__)
                self.logger.error(
                    "Unexpected error shipping order", order_id=command.order_id, error=str(e)
                )
                raise
