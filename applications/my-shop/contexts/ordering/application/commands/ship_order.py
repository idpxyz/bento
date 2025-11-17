"""Ship order command and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.ordering.domain.order import Order


@dataclass
class ShipOrderCommand:
    """Ship order command."""
    
    order_id: str
    tracking_number: str | None = None


class ShipOrderUseCase(BaseUseCase[ShipOrderCommand, Order]):
    """Ship order use case.
    
    订单发货。
    发布 OrderShipped 事件。
    """
    
    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)
    
    async def validate(self, command: ShipOrderCommand) -> None:
        """Validate command."""
        if not command.order_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )
    
    async def handle(self, command: ShipOrderCommand) -> Order:
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
        
        # 发货（领域方法）
        try:
            order.ship(tracking_number=command.tracking_number)
        except ValueError as e:
            raise ApplicationException(
                error_code=CommonErrors.BUSINESS_ERROR,
                details={"reason": str(e)},
            )
        
        # 保存
        await order_repo.save(order)
        
        return order
