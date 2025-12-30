"""List categories query and use case."""

from dataclasses import dataclass

from bento.application import QueryHandler, query_handler
from bento.application.ports.uow import UnitOfWork

from contexts.catalog.application.dto import CategoryDTO
from contexts.catalog.application.mappers import CategoryDTOMapper
from contexts.catalog.domain.models.category import Category


@dataclass
class ListCategoriesResult:
    """List categories result with DTOs."""

    categories: list[CategoryDTO]
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
    """Get category tree result with DTOs."""

    categories: list[CategoryDTO]


@query_handler
class ListCategoriesHandler(QueryHandler[ListCategoriesQuery, ListCategoriesResult]):
    """List categories use case."""

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)
        self.mapper = CategoryDTOMapper()

    async def validate(self, query: ListCategoriesQuery) -> None:
        """Validate query."""
        pass

    async def handle(self, query: ListCategoriesQuery) -> ListCategoriesResult:
        """Handle query execution and return DTOs."""
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

        # Convert to DTOs using mapper (SOLID compliant)
        category_dtos = self.mapper.to_dto_list(categories)

        return ListCategoriesResult(
            categories=category_dtos,
            total=len(category_dtos),
        )


class GetCategoryTreeHandler(QueryHandler[CategoryTreeQuery, CategoryTreeResult]):
    """Get category tree query."""

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)
        self.mapper = CategoryDTOMapper()

    async def validate(self, query: CategoryTreeQuery) -> None:
        """Validate query."""
        pass

    async def handle(self, query: CategoryTreeQuery) -> CategoryTreeResult:
        """Handle query execution and return DTOs."""
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

        # Convert to DTOs using mapper (SOLID compliant)
        category_dtos = self.mapper.to_dto_list(categories)

        return CategoryTreeResult(
            categories=category_dtos,
        )
