"""Get category query and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.catalog.domain.category import Category


@dataclass
class GetCategoryQuery:
    """Get category query."""

    category_id: str


class GetCategoryUseCase(BaseUseCase[GetCategoryQuery, Category]):
    """Get category use case.

    Retrieves a single category by ID.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, query: GetCategoryQuery) -> None:
        """Validate query."""
        if not query.category_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "category_id", "reason": "cannot be empty"},
            )

    async def handle(self, query: GetCategoryQuery) -> Category:
        """Handle query execution."""
        category_repo = self.uow.repository(Category)

        category = await category_repo.get(query.category_id)  # type: ignore
        if not category:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "category", "id": query.category_id},
            )

        return category


s
