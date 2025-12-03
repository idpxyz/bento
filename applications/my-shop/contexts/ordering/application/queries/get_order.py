"""Get order query and use case."""

from dataclasses import dataclass

from bento.application import QueryHandler, query_handler
from bento.application.ports.uow import UnitOfWork
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.ordering.application.dto import OrderDTO
from contexts.ordering.application.mappers import OrderDTOMapper
from contexts.ordering.domain.models.order import Order


@dataclass
class GetOrderQuery:
    """Get order query."""
    
    order_id: str


@query_handler
class GetOrderHandler(QueryHandler[GetOrderQuery, OrderDTO]):
    """Get order use case.
    
    获取订单详情（包含所有订单项）。
    """
    
    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)
        self.mapper = OrderDTOMapper()
    
    async def validate(self, query: GetOrderQuery) -> None:
        """Validate query."""
        if not query.order_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )
    
    async def handle(self, query: GetOrderQuery) -> OrderDTO:
        """Handle query execution and return DTO."""
        order_repo = self.uow.repository(Order)

        order = await order_repo.get(query.order_id)  # type: ignore[arg-type]
        if not order:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "order", "id": query.order_id},
            )

        # Use mapper for conversion (SOLID compliant)
        return self.mapper.to_dto(order)
