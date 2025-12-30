"""Pay order command and use case."""

from dataclasses import dataclass

from bento.application import ObservableCommandHandler, command_handler
from bento.application.ports.observability import ObservabilityProvider
from bento.application.ports.uow import UnitOfWork
# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException

from contexts.ordering.domain.models.order import Order


@dataclass
class PayOrderCommand:
    """Pay order command.

    Note: Idempotency is handled by IdempotencyMiddleware at HTTP layer.
    """

    order_id: str


@command_handler
class PayOrderHandler(ObservableCommandHandler):
    """Pay order use case.

    确认订单支付。
    发布 OrderPaid 事件。
    """

    def __init__(self, uow: UnitOfWork, observability: ObservabilityProvider) -> None:
        super().__init__(uow, observability, "ordering")

    async def validate(self, command: PayOrderCommand) -> None:
        """Validate command."""
        if not command.order_id:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "order_id", "reason": "cannot be empty"},
            )

    async def handle(self, command: PayOrderCommand) -> Order:
        """Handle command execution."""
        async with self.tracer.start_span("pay_order") as span:
            span.set_attribute("order_id", command.order_id)

            self.logger.info("Processing payment", order_id=command.order_id)

            try:
                from contexts.ordering.infrastructure.repositories.order_repository_impl import (
                    OrderRepository,
                )

                order_repo = OrderRepository(self.uow._session)  # type: ignore

                # 获取订单
                order = await order_repo.get(command.order_id)
                if not order:
                    self._record_failure("pay_order", "order_not_found")
                    self.logger.error("Order not found", order_id=command.order_id)
                    raise ApplicationException(
                        reason_code="NOT_FOUND",
                        details={"resource": "order", "id": command.order_id},
                    )

                # 确认支付（领域方法会自动发布 OrderPaidEvent）
                try:
                    order.confirm_payment()
                except ValueError as e:
                    self._record_failure("pay_order", "invalid_state", reason=str(e))
                    self.logger.error("Invalid order state for payment", order_id=command.order_id, reason=str(e))
                    raise ApplicationException(
                        reason_code="INVALID_PARAMS",
                        details={"reason": str(e)},
                    ) from e

                # 保存
                await order_repo.save(order)

                # Record success
                self._record_success(
                    "pay_order",
                    order_id=command.order_id,
                    total=float(order.total),
                )

                span.set_attribute("order_total", float(order.total))
                span.set_status("ok")

                self.logger.info(
                    "Payment processed successfully",
                    order_id=command.order_id,
                    total=float(order.total),
                )

                return order

            except ApplicationException:
                raise
            except Exception as e:
                span.record_exception(e)
                span.set_status("error", str(e))
                self._record_failure("pay_order", "unexpected_error", error_type=type(e).__name__)
                self.logger.error("Unexpected error processing payment", order_id=command.order_id, error=str(e))
                raise
