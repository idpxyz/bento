"""Update category command and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.catalog.domain.category import Category


@dataclass
class UpdateCategoryCommand:
    """Update category command."""

    category_id: str
    name: str | None = None
    description: str | None = None
    parent_id: str | None = None


class UpdateCategoryUseCase(BaseUseCase[UpdateCategoryCommand, Category]):
    """Update category use case."""

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: UpdateCategoryCommand) -> None:
        """Validate command."""
        if not command.category_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "category_id", "reason": "cannot be empty"},
            )

        # At least one field must be provided
        if command.name is None and command.description is None and command.parent_id is None:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"reason": "at least one field must be provided"},
            )

    async def handle(self, command: UpdateCategoryCommand) -> Category:
        """Handle command execution."""
        category_repo = self.uow.repository(Category)

        # Get category
        category = await category_repo.get(command.category_id)  # type: ignore
        if not category:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "category", "id": command.category_id},
            )

        # Update fields
        if command.name:
            category.change_name(command.name)

        if command.description:
            category.description = command.description.strip()

        if command.parent_id is not None:
            category.move_to(command.parent_id)

        # Save changes
        await category_repo.save(category)

        return category
