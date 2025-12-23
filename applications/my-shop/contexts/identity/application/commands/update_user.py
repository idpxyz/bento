"""Update user command and use case."""

from dataclasses import dataclass

from bento.application.ports.uow import UnitOfWork
from bento.application.cqrs import CommandHandler
# CommonErrors removed - use DomainException directly
from bento.core.exceptions import ApplicationException

from contexts.identity.domain.models.user import User


@dataclass
class UpdateUserCommand:
    """Update user command.

    Attributes:
        user_id: User identifier
        name: New user name (optional)
        email: New user email (optional)
    """

    user_id: str
    name: str | None = None
    email: str | None = None


class UpdateUserHandler(CommandHandler[UpdateUserCommand, User]):
    """Update user use case.

    Handles user updates with validation.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: UpdateUserCommand) -> None:
        """Validate command."""
        if not command.user_id:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "user_id", "reason": "cannot be empty"},
            )

        # At least one field must be provided
        if not command.name and not command.email:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"reason": "at least one field (name or email) must be provided"},
            )

        # Email format validation
        if command.email and "@" not in command.email:
            raise ApplicationException(
                reason_code="INVALID_PARAMS",
                details={"field": "email", "reason": "invalid email format"},
            )

        # Check if email is already taken by another user
        if command.email:
            user_repo = self.uow.repository(User)
            existing = await user_repo.find_by_email(command.email)
            if existing and existing.id != command.user_id:
                raise ApplicationException(
                    reason_code="ALREADY_EXISTS",
                    details={"field": "email", "reason": f"email '{command.email}' already exists"},
                )

    async def handle(self, command: UpdateUserCommand) -> User:
        """Handle command execution."""
        user_repo = self.uow.repository(User)

        # Get user
        user = await user_repo.get(command.user_id)  # type: ignore[arg-type]
        if not user:
            raise ApplicationException(
                reason_code="NOT_FOUND",
                details={"resource": "user", "id": command.user_id},
            )

        # Update fields using domain methods
        if command.name:
            user.change_name(command.name.strip())

        if command.email:
            user.change_email(command.email.strip().lower())

        # Save changes
        await user_repo.save(user)

        return user
