"""List orders query and use case."""

from dataclasses import dataclass

from bento.application.ports.uow import UnitOfWork
from bento.application.cqrs import QueryHandler

from contexts.ordering.domain.order import Order


@dataclass
class ListOrdersResult:
    """List orders result."""
    
    orders: list[Order]
    total: int


@dataclass
class ListOrdersQuery:
    """List orders query."""
    
    customer_id: str | None = None  # 可选：按客户过滤


class ListOrdersHandler(QueryHandler[ListOrdersQuery, ListOrdersResult]):
    """List orders use case."""
    
    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)
    
    async def validate(self, query: ListOrdersQuery) -> None:
        """Validate query."""
        pass
    
    async def handle(self, query: ListOrdersQuery) -> ListOrdersResult:
        """Handle query execution."""
        from contexts.ordering.infrastructure.repositories.order_repository_impl import OrderRepository
        
        order_repo = OrderRepository(self.uow._session)  # type: ignore
        
        if query.customer_id:
            orders = await order_repo.find_by_customer(query.customer_id)
        else:
            orders = await order_repo.list()
        
        return ListOrdersResult(
            orders=orders,
            total=len(orders),
        )
