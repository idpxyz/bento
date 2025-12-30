"""Delete user command and use case."""

from dataclasses import dataclass

from bento.application.cqrs import CommandHandler
from bento.application.ports.uow import UnitOfWork

# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException

from contexts.identity.domain.models.user import User


@dataclass
class DeleteUserCommand:
    """Delete user command.

    Attributes:
        user_id: User identifier
    """

    user_id: str


class DeleteUserHandler(CommandHandler[DeleteUserCommand, None]):
    """Delete user use case.

    Handles user deletion (soft delete).
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: DeleteUserCommand) -> None:
        """Validate command."""
        if not command.user_id:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "user_id", "reason": "cannot be empty"},
            )

    async def handle(self, command: DeleteUserCommand) -> None:
        """Handle command execution."""
        user_repo = self.uow.repository(User)

        # Get user
        user = await user_repo.get(command.user_id)  # type: ignore[arg-type]
        if not user:
            raise ApplicationException(
                reason_code="NOT_FOUND",
                details={"resource": "user", "id": command.user_id},
            )

        # Publish UserDeleted event before deletion
        from contexts.identity.domain.events import UserDeleted

        user.add_event(
            UserDeleted(
                user_id=user.id,
                email=user.email,
            )
        )

        # Delete user (soft delete via framework)
        await user_repo.delete(user)
