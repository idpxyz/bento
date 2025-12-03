"""Delete category command and use case."""

from dataclasses import dataclass

from bento.application.ports.uow import UnitOfWork
from bento.application.cqrs import CommandHandler
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.catalog.domain.category import Category


@dataclass
class DeleteCategoryCommand:
    """Delete category command."""

    category_id: str


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
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "category_id", "reason": "cannot be empty"},
            )

    async def handle(self, command: DeleteCategoryCommand) -> None:
        """Handle command execution."""
        category_repo = self.uow.repository(Category)

        # Get category
        category = await category_repo.get(command.category_id)  # type: ignore
        if not category:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "category", "id": command.category_id},
            )

        # Delete category (soft delete via framework)
        await category_repo.delete(category)
