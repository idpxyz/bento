"""List categories query and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase

from contexts.catalog.domain.category import Category


@dataclass
class ListCategoriesResult:
    """List categories result."""

    categories: list[Category]
    total: int


@dataclass
class ListCategoriesQuery:
    """List categories query."""

    parent_id: str | None = None  # Filter by parent_id (None = root categories)


class ListCategoriesUseCase(BaseUseCase[ListCategoriesQuery, ListCategoriesResult]):
    """List categories use case."""

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, query: ListCategoriesQuery) -> None:
        """Validate query."""
        pass

    async def handle(self, query: ListCategoriesQuery) -> ListCategoriesResult:
        """Handle query execution."""
        category_repo = self.uow.repository(Category)

        # Get all categories (can add filtering later)
        categories = await category_repo.list()

        # Filter by parent_id if specified
        if query.parent_id is not None:
            categories = [c for c in categories if c.parent_id == query.parent_id]

        return ListCategoriesResult(
            categories=categories,
            total=len(categories),
        )
