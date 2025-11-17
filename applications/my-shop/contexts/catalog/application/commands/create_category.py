"""Create category command and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException
from bento.core.ids import ID

from contexts.catalog.domain.category import Category


@dataclass
class CreateCategoryCommand:
    """Create category command."""

    name: str
    description: str
    parent_id: str | None = None


class CreateCategoryUseCase(BaseUseCase[CreateCategoryCommand, Category]):
    """Create category use case."""

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: CreateCategoryCommand) -> None:
        """Validate command."""
        if not command.name or not command.name.strip():
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "name", "reason": "cannot be empty"},
            )

    async def handle(self, command: CreateCategoryCommand) -> Category:
        """Handle command execution."""
        category_id = str(ID.generate())
        category = Category(
            id=category_id,
            name=command.name.strip(),
            description=command.description.strip() if command.description else "",
            parent_id=command.parent_id,
        )

        # Persist via repository
        category_repo = self.uow.repository(Category)
        await category_repo.save(category)

        return category
