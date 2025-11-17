"""Get order query and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.ordering.domain.order import Order


@dataclass
class GetOrderQuery:
    """Get order query."""
    
    order_id: str


class GetOrderUseCase(BaseUseCase[GetOrderQuery, Order]):
    """Get order use case.
    
    获取订单详情（包含所有订单项）。
    """
    
    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)
    
    async def validate(self, query: GetOrderQuery) -> None:
        """Validate query."""
        if not query.order_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )
    
    async def handle(self, query: GetOrderQuery) -> Order:
        """Handle query execution."""
        from contexts.ordering.infrastructure.repositories.order_repository_impl import OrderRepository
        
        order_repo = OrderRepository(self.uow._session)  # type: ignore
        
        order = await order_repo.get(query.order_id)
        if not order:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "order", "id": query.order_id},
            )
        
        return order
