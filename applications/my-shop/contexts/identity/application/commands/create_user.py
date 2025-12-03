"""Create user command and use case."""

from dataclasses import dataclass

from bento.application.ports.uow import UnitOfWork
from bento.application.cqrs import CommandHandler
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException
from bento.core.ids import ID

from contexts.identity.domain.models.user import User


@dataclass
class CreateUserCommand:
    """Create user command.

    Attributes:
        name: User name
        email: User email address
    """

    name: str
    email: str


class CreateUserHandler(CommandHandler[CreateUserCommand, User]):
    """Create user use case.

    Handles user creation with validation and persistence.

    Example:
        ```python
        use_case = CreateUserUseCase(uow)

        command = CreateUserCommand(
            name="张三",
            email="zhangsan@example.com"
        )

        user = await use_case.execute(command)
        ```
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, command: CreateUserCommand) -> None:
        """Validate command.

        Args:
            command: Create user command

        Raises:
            ApplicationException: If validation fails
        """
        if not command.name or not command.name.strip():
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "name", "reason": "cannot be empty"},
            )

        if not command.email or not command.email.strip():
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "email", "reason": "cannot be empty"},
            )

        # Email format validation (simple)
        if "@" not in command.email:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "email", "reason": "invalid email format"},
            )

        # Check if email already exists
        user_repo = self.uow.repository(User)
        if await user_repo.email_exists(command.email):
            raise ApplicationException(
                error_code=CommonErrors.ALREADY_EXISTS,
                details={"field": "email", "reason": f"email '{command.email}' already exists"},
            )

    async def handle(self, command: CreateUserCommand) -> User:
        """Handle command execution.

        Args:
            command: Create user command

        Returns:
            Created user aggregate
        """
        # Create user aggregate
        user_id = str(ID.generate())
        user = User(
            id=user_id,
            name=command.name.strip(),
            email=command.email.strip().lower(),
        )

        # Publish UserCreated event
        from contexts.identity.domain.events import UserCreated

        user.add_event(
            UserCreated(
                user_id=user_id,
                name=user.name,
                email=user.email,
            )
        )

        # Persist via repository inside UoW
        user_repo = self.uow.repository(User)
        await user_repo.save(user)

        return user
