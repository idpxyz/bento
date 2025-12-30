"""List orders query and use case."""

from dataclasses import dataclass

from bento.application import QueryHandler, query_handler
from bento.application.ports.uow import UnitOfWork

from contexts.ordering.application.dto import OrderDTO
from contexts.ordering.application.mappers import OrderDTOMapper


@dataclass
class ListOrdersResult:
    """List orders result with DTOs."""

    orders: list[OrderDTO]
    total: int


@dataclass
class ListOrdersQuery:
    """List orders query."""

    customer_id: str | None = None  # 可选：按客户过滤


@query_handler
class ListOrdersHandler(QueryHandler[ListOrdersQuery, ListOrdersResult]):
    """List orders use case."""

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)
        self.mapper = OrderDTOMapper()

    async def validate(self, query: ListOrdersQuery) -> None:
        """Validate query."""
        pass

    async def handle(self, query: ListOrdersQuery) -> ListOrdersResult:
        """Handle query execution and return DTOs."""
        from contexts.ordering.domain.models.order import Order

        # ✅ 使用正确的 UoW Repository 访问方式
        order_repo = self.uow.repository(Order)

        if query.customer_id:
            # TODO: 实现 find_by_customer 方法或使用 Specification
            orders = await order_repo.find_all()
            # 简单过滤（生产中应该使用 Specification）
            orders = [o for o in orders if str(o.customer_id) == query.customer_id]
        else:
            orders = await order_repo.find_all()

        # Convert to DTOs using mapper (SOLID compliant)
        order_dtos = self.mapper.to_dto_list(orders)

        return ListOrdersResult(
            orders=order_dtos,
            total=len(order_dtos),
        )
