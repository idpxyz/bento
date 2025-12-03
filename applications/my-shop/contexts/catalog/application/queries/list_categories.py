"""List categories query and use case."""

from dataclasses import dataclass

from bento.application.ports.uow import UnitOfWork
from bento.application.cqrs import QueryHandler

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


@dataclass
class CategoryTreeQuery:
    """Get category tree query."""

    parent_id: str | None = None  # Filter by parent_id (None = root categories)


@dataclass
class CategoryTreeResult:
    """Get category tree result."""

    categories: list[Category]


class ListCategoriesHandler(QueryHandler[ListCategoriesQuery, ListCategoriesResult]):
    """List categories use case."""

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, query: ListCategoriesQuery) -> None:
        """Validate query."""
        pass

    async def handle(self, query: ListCategoriesQuery) -> ListCategoriesResult:
        """Handle query execution."""
        from bento.persistence.specification import EntitySpecificationBuilder

        category_repo = self.uow.repository(Category)

        # Query with specification (database-level filtering)
        if query.parent_id is not None:
            # Use fluent builder for clean, readable specification
            spec = EntitySpecificationBuilder().where("parent_id", query.parent_id).build()
            categories = await category_repo.find_all(spec)
        else:
            # Get all categories
            categories = await category_repo.find_all()

        return ListCategoriesResult(
            categories=categories,
            total=len(categories),
        )


class GetCategoryTreeHandler(QueryHandler[CategoryTreeQuery, CategoryTreeResult]):
    """Get category tree query."""

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, query: CategoryTreeQuery) -> None:
        """Validate query."""
        pass

    async def handle(self, query: CategoryTreeQuery) -> CategoryTreeResult:
        """Handle query execution."""
        from bento.persistence.specification import EntitySpecificationBuilder

        category_repo = self.uow.repository(Category)

        # Query with specification (database-level filtering)
        if query.parent_id is not None:
            # Use fluent builder for clean, readable specification
            spec = EntitySpecificationBuilder().where("parent_id", query.parent_id).build()
            categories = await category_repo.find_all(spec)
        else:
            # Get all categories
            categories = await category_repo.find_all()

        return CategoryTreeResult(
            categories=categories,
        )
