"""Get category query and handler."""

from dataclasses import dataclass

from bento.application import QueryHandler, query_handler
from bento.application.ports.uow import UnitOfWork
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.catalog.application.dto import CategoryDTO
from contexts.catalog.application.mappers import CategoryDTOMapper
from contexts.catalog.domain.models.category import Category


@dataclass
class GetCategoryQuery:
    """Get category query."""

    category_id: str


@query_handler
class GetCategoryHandler(QueryHandler[GetCategoryQuery, CategoryDTO]):
    """Get category query handler.

    Retrieves a single category by ID and returns as DTO.
    使用 @query_handler 装饰器自动注册到全局 Handler 注册表。
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)
        self.mapper = CategoryDTOMapper()

    async def validate(self, query: GetCategoryQuery) -> None:
        """Validate query."""
        if not query.category_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "category_id", "reason": "cannot be empty"},
            )

    async def handle(self, query: GetCategoryQuery) -> CategoryDTO:
        """Handle query execution and return DTO."""
        category_repo = self.uow.repository(Category)

        category = await category_repo.get(query.category_id)  # type: ignore[arg-type]
        if not category:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "category", "id": query.category_id},
            )

        # Use mapper for conversion (SOLID compliant)
        return self.mapper.to_dto(category)
