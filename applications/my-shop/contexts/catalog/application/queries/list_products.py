"""List products query and use case."""

from dataclasses import dataclass

from bento.application.ports.uow import UnitOfWork
from bento.application.cqrs import QueryHandler

from contexts.catalog.domain.product import Product


@dataclass
class ListProductsResult:
    """List products result."""

    products: list[Product]
    total: int
    page: int
    page_size: int


@dataclass
class ListProductsQuery:
    """List products query."""

    page: int = 1
    page_size: int = 10
    category_id: str | None = None


class ListProductsHandler(QueryHandler[ListProductsQuery, ListProductsResult]):
    """List products use case."""

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, query: ListProductsQuery) -> None:
        """Validate query."""
        pass

    async def handle(self, query: ListProductsQuery) -> ListProductsResult:
        """Handle query execution."""
        product_repo = self.uow.repository(Product)

        offset = (query.page - 1) * query.page_size

        products = await product_repo.list_products(
            limit=query.page_size,
            offset=offset,
            category_id=query.category_id,
        )

        total = await product_repo.count(category_id=query.category_id)

        return ListProductsResult(
            products=products,
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
