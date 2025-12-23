"""Create category command and handler."""

from dataclasses import dataclass

from bento.application import CommandHandler, command_handler
from bento.application.ports.uow import UnitOfWork
# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException
from bento.core.ids import ID

from contexts.catalog.domain.models.category import Category


@dataclass
class CreateCategoryCommand:
    """Create category command."""

    name: str
    description: str
    parent_id: str | None = None


@command_handler
class CreateCategoryHandler(CommandHandler[CreateCategoryCommand, Category]):
    """Create category command handler.

    使用 @command_handler 装饰器自动注册到全局 Handler 注册表。
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: CreateCategoryCommand) -> None:
        """Validate command."""
        if not command.name or not command.name.strip():
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "name", "reason": "cannot be empty"},
            )

        # Validate parent category exists if parent_id is provided
        if command.parent_id:
            category_repo = self.uow.repository(Category)
            parent = await category_repo.get(ID(command.parent_id))
            if not parent:
                raise ApplicationException(
                    reason_code="NOT_FOUND",
                    details={"resource": "parent category", "id": command.parent_id},
                )

    async def handle(self, command: CreateCategoryCommand) -> Category:
        """Handle command execution."""
        category_id = ID.generate()
        category = Category(
            id=category_id,
            name=command.name.strip(),
            description=command.description.strip() if command.description else "",
            parent_id=ID(command.parent_id) if command.parent_id else None,
        )

        # Persist via repository
        category_repo = self.uow.repository(Category)
        await category_repo.save(category)

        return category
