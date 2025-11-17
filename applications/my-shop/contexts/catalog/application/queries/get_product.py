"""Get product query and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.catalog.domain.product import Product


@dataclass
class GetProductQuery:
    """Get product query."""

    product_id: str


class GetProductUseCase(BaseUseCase[GetProductQuery, Product]):
    """Get product use case.

    Retrieves a single product by ID.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, query: GetProductQuery) -> None:
        """Validate query."""
        if not query.product_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "product_id", "reason": "cannot be empty"},
            )

    async def handle(self, query: GetProductQuery) -> Product:
        """Handle query execution."""
        product_repo = self.uow.repository(Product)

        product = await product_repo.get(query.product_id)  # type: ignore[arg-type]
        if not product:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "product", "id": query.product_id},
            )

        return product
