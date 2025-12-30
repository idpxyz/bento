"""Delete category command and use case."""

from dataclasses import dataclass

from bento.application import CommandHandler, command_handler
from bento.application.ports.uow import UnitOfWork

# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException

from contexts.catalog.domain.models.category import Category


@dataclass
class DeleteCategoryCommand:
    """Delete category command."""

    category_id: str


@command_handler
class DeleteCategoryHandler(CommandHandler[DeleteCategoryCommand, None]):
    """Delete category use case.

    Handles category deletion (soft delete).
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: DeleteCategoryCommand) -> None:
        """Validate command."""
        if not command.category_id:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "category_id", "reason": "cannot be empty"},
            )

        # Check if category exists
        category_repo = self.uow.repository(Category)
        category = await category_repo.get(command.category_id)  # type: ignore
        if not category:
            raise ApplicationException(
                reason_code="NOT_FOUND",
                details={"resource": "category", "id": command.category_id},
            )

        # Check if category has children
        all_categories = await category_repo.find_all()
        children = [
            c for c in all_categories if c.parent_id and str(c.parent_id) == command.category_id
        ]
        if children:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={
                    "reason": "Cannot delete category with children",
                    "category_id": command.category_id,
                    "children_count": len(children),
                },
            )

    async def handle(self, command: DeleteCategoryCommand) -> None:
        """Handle command execution."""
        category_repo = self.uow.repository(Category)

        # Get category
        category = await category_repo.get(command.category_id)  # type: ignore
        if not category:
            raise ApplicationException(
                reason_code="NOT_FOUND",
                details={"resource": "category", "id": command.category_id},
            )

        # Mark category as deleted (triggers event)
        category.mark_deleted()

        # Delete category (soft delete via framework)
        await category_repo.delete(category)
