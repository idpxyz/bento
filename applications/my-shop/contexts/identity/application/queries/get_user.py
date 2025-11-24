"""Get user query and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.identity.domain.models.user import User


@dataclass
class GetUserQuery:
    """Get user query.

    Attributes:
        user_id: User identifier
    """

    user_id: str


class GetUserUseCase(BaseUseCase[GetUserQuery, User]):
    """Get user use case.

    Retrieves a single user by ID.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, query: GetUserQuery) -> None:
        """Validate query."""
        if not query.user_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "user_id", "reason": "cannot be empty"},
            )

    async def handle(self, query: GetUserQuery) -> User:
        """Handle query execution."""
        user_repo = self.uow.repository(User)

        user = await user_repo.get(query.user_id)  # type: ignore[arg-type]
        if not user:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "user", "id": query.user_id},
            )

        return user
