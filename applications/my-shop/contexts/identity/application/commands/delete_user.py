"""Delete user command and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.identity.domain.models.user import User


@dataclass
class DeleteUserCommand:
    """Delete user command.

    Attributes:
        user_id: User identifier
    """

    user_id: str


class DeleteUserUseCase(BaseUseCase[DeleteUserCommand, None]):
    """Delete user use case.

    Handles user deletion (soft delete).
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: DeleteUserCommand) -> None:
        """Validate command."""
        if not command.user_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "user_id", "reason": "cannot be empty"},
            )

    async def handle(self, command: DeleteUserCommand) -> None:
        """Handle command execution."""
        user_repo = self.uow.repository(User)

        # Get user
        user = await user_repo.get(command.user_id)  # type: ignore[arg-type]
        if not user:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "user", "id": command.user_id},
            )

        # Delete user (soft delete via framework)
        await user_repo.delete(user)
