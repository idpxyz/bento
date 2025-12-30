"""Update category command and use case."""

from dataclasses import dataclass

from bento.application import CommandHandler, command_handler
from bento.application.ports.uow import UnitOfWork

# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException
from bento.core.ids import ID

from contexts.catalog.domain.models.category import Category


@dataclass
class UpdateCategoryCommand:
    """Update category command."""

    category_id: str
    name: str | None = None
    description: str | None = None
    parent_id: str | None = None


@command_handler
class UpdateCategoryHandler(CommandHandler[UpdateCategoryCommand, Category]):
    """Update category use case."""

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: UpdateCategoryCommand) -> None:
        """Validate command."""
        if not command.category_id:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "category_id", "reason": "cannot be empty"},
            )

        # At least one field must be provided
        if command.name is None and command.description is None and command.parent_id is None:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"reason": "at least one field must be provided"},
            )

    async def handle(self, command: UpdateCategoryCommand) -> Category:
        """Handle command execution."""
        category_repo = self.uow.repository(Category)

        # Get category
        category = await category_repo.get(command.category_id)  # type: ignore
        if not category:
            raise ApplicationException(
                reason_code="NOT_FOUND",
                details={"resource": "category", "id": command.category_id},
            )

        # Update fields
        if command.name:
            category.change_name(command.name)

        if command.description:
            category.description = command.description.strip()

        if command.parent_id is not None:
            category.move_to(ID(command.parent_id))

        # Save changes
        await category_repo.save(category)

        return category
