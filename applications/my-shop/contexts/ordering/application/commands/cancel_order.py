"""Cancel order command and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.ordering.domain.order import Order


@dataclass
class CancelOrderCommand:
    """Cancel order command."""
    
    order_id: str
    reason: str


class CancelOrderUseCase(BaseUseCase[CancelOrderCommand, Order]):
    """Cancel order use case.
    
    取消订单。
    发布 OrderCancelled 事件。
    """
    
    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)
    
    async def validate(self, command: CancelOrderCommand) -> None:
        """Validate command."""
        if not command.order_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )
        if not command.reason:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "reason", "reason": "cannot be empty"},
            )
    
    async def handle(self, command: CancelOrderCommand) -> Order:
        """Handle command execution."""
        from contexts.ordering.infrastructure.repositories.order_repository_impl import OrderRepository
        
        order_repo = OrderRepository(self.uow._session)  # type: ignore
        
        # 获取订单
        order = await order_repo.get(command.order_id)
        if not order:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "order", "id": command.order_id},
            )
        
        # 取消（领域方法）
        try:
            order.cancel(reason=command.reason)
        except ValueError as e:
            raise ApplicationException(
                error_code=CommonErrors.BUSINESS_ERROR,
                details={"reason": str(e)},
            )
        
        # 保存
        await order_repo.save(order)
        
        return order
