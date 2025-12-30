"""Get category tree query and handler."""

from dataclasses import dataclass

from bento.application import QueryHandler, query_handler
from bento.application.ports.uow import UnitOfWork
# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException
from pydantic import BaseModel, Field

from contexts.catalog.domain.models.category import Category


class CategoryTreeNodeDTO(BaseModel):
    """Category tree node DTO."""

    id: str = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    description: str = Field(..., description="Category description")
    is_root: bool = Field(..., description="Is root category")
    children: list["CategoryTreeNodeDTO"] = Field(
        default_factory=list, description="Child categories"
    )


# Update forward reference
CategoryTreeNodeDTO.model_rebuild()


@dataclass
class GetCategoryTreeQuery:
    """Get category tree query."""

    root_id: str | None = None  # If None, return all root categories


@query_handler
class GetCategoryTreeHandler(QueryHandler[GetCategoryTreeQuery, list[CategoryTreeNodeDTO]]):
    """Get category tree query handler.

    Returns categories in tree structure.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, query: GetCategoryTreeQuery) -> None:
        """Validate query."""
        # If root_id is provided, check if it exists
        if query.root_id:
            category_repo = self.uow.repository(Category)
            category = await category_repo.get(query.root_id)  # type: ignore
            if not category:
                raise ApplicationException(
                    reason_code="NOT_FOUND",
                    details={"resource": "category", "id": query.root_id},
                )

    async def handle(self, query: GetCategoryTreeQuery) -> list[CategoryTreeNodeDTO]:
        """Handle query execution and return tree structure."""
        category_repo = self.uow.repository(Category)

        # Get all categories
        all_categories = await category_repo.find_all()

        # Build a map for quick lookup
        categories_by_id = {str(c.id): c for c in all_categories}

        # Build tree structure
        def build_tree_node(category: Category) -> CategoryTreeNodeDTO:
            """Build a tree node for a category and its children."""
            # Find children
            children = [
                c for c in all_categories if c.parent_id and str(c.parent_id) == str(category.id)
            ]

            # Recursively build children nodes
            children_nodes = [
                build_tree_node(child) for child in sorted(children, key=lambda c: c.name)
            ]

            return CategoryTreeNodeDTO(
                id=str(category.id),
                name=category.name,
                description=category.description,
                is_root=category.is_root(),
                children=children_nodes,
            )

        # If root_id is provided, return tree from that root
        if query.root_id:
            root_category = categories_by_id.get(query.root_id)
            if root_category:
                return [build_tree_node(root_category)]
            return []

        # Otherwise, return all root categories with their trees
        root_categories = [c for c in all_categories if c.is_root()]
        root_categories.sort(key=lambda c: c.name)

        return [build_tree_node(root) for root in root_categories]
