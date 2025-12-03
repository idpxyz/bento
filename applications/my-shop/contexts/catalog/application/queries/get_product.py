"""Get product query and use case."""

from dataclasses import dataclass

from bento.application import QueryHandler, query_handler
from bento.application.ports.uow import UnitOfWork
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.catalog.application.dto import ProductDTO
from contexts.catalog.application.mappers import ProductDTOMapper
from contexts.catalog.domain.models.product import Product


@dataclass
class GetProductQuery:
    """Get product query."""

    product_id: str


@query_handler
class GetProductHandler(QueryHandler[GetProductQuery, ProductDTO]):
    """Get product query handler.

    Retrieves a single product by ID and returns as DTO.
    Uses DTOMapper for clean architecture compliance.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)
        self.mapper = ProductDTOMapper()

    async def validate(self, query: GetProductQuery) -> None:
        """Validate query."""
        if not query.product_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "product_id", "reason": "cannot be empty"},
            )

    async def handle(self, query: GetProductQuery) -> ProductDTO:
        """Handle query execution and return DTO."""
        product_repo = self.uow.repository(Product)

        product = await product_repo.get(query.product_id)  # type: ignore[arg-type]
        if not product:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "product", "id": query.product_id},
            )

        # Use mapper for conversion (SOLID compliant)
        return self.mapper.to_dto(product)
