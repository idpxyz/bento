"""Cancel order command and use case."""

from dataclasses import dataclass

from bento.application import ObservableCommandHandler, command_handler
from bento.application.ports.observability import ObservabilityProvider
from bento.application.ports.uow import UnitOfWork

# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException

from contexts.ordering.domain.models.order import Order


@dataclass
class CancelOrderCommand:
    """Cancel order command."""

    order_id: str
    reason: str


@command_handler
class CancelOrderHandler(ObservableCommandHandler[CancelOrderCommand, Order]):
    """Cancel order use case.

    取消订单。
    发布 OrderCancelled 事件。
    """

    def __init__(self, uow: UnitOfWork, observability: ObservabilityProvider) -> None:
        super().__init__(uow, observability, "ordering")

    async def validate(self, command: CancelOrderCommand) -> None:
        """Validate command."""
        if not command.order_id:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "order_id", "reason": "cannot be empty"},
            )
        if not command.reason:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "reason", "reason": "cannot be empty"},
            )

    async def handle(self, command: CancelOrderCommand) -> Order:
        """Handle command execution."""
        async with self.tracer.start_span("cancel_order") as span:
            span.set_attribute("order_id", command.order_id)
            span.set_attribute("reason", command.reason)

            self.logger.info("Cancelling order", order_id=command.order_id, reason=command.reason)

            try:
                from contexts.ordering.infrastructure.repositories.order_repository_impl import (
                    OrderRepository,
                )

                order_repo = OrderRepository(self.uow._session)  # type: ignore

                # 获取订单
                order = await order_repo.get(command.order_id)
                if not order:
                    self._record_failure("cancel_order", "order_not_found")
                    self.logger.error("Order not found", order_id=command.order_id)
                    raise ApplicationException(
                        reason_code="NOT_FOUND",
                        details={"resource": "order", "id": command.order_id},
                    )

                # 取消订单（领域方法会自动发布 OrderCancelledEvent）
                try:
                    order.cancel(reason=command.reason)
                except ValueError as e:
                    self._record_failure("cancel_order", "invalid_state", error=str(e))
                    self.logger.error("Invalid order state for cancellation", order_id=command.order_id, error=str(e))
                    raise ApplicationException(
                        reason_code="INVALID_PARAMS",
                        details={"reason": str(e)},
                    ) from e

                # 保存
                await order_repo.save(order)

                # Record success
                self._record_success(
                    "cancel_order",
                    order_id=command.order_id,
                    reason=command.reason,
                )

                span.set_status("ok")
                self.logger.info("Order cancelled successfully", order_id=command.order_id)

                return order

            except ApplicationException:
                raise
            except Exception as e:
                span.record_exception(e)
                span.set_status("error", str(e))
                self._record_failure("cancel_order", "unexpected_error", error_type=type(e).__name__)
                self.logger.error("Unexpected error cancelling order", order_id=command.order_id, error=str(e))
                raise
