"""Get user query and handler."""

from dataclasses import dataclass

from bento.application import QueryHandler, query_handler
from bento.application.ports.uow import UnitOfWork
from bento.core.error_codes import CommonErrors
from bento.core.errors import ApplicationException

from contexts.identity.application.dto.user_dto import UserDTO
from contexts.identity.application.mappers.user_dto_mapper import UserDTOMapper
from contexts.identity.domain.models.user import User


@dataclass
class GetUserQuery:
    """Get user query.

    Attributes:
        user_id: User identifier
    """

    user_id: str


@query_handler
class GetUserHandler(QueryHandler[GetUserQuery, UserDTO]):
    """Get user handler.

    Retrieves a single user by ID and returns DTO.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)
        self.mapper = UserDTOMapper()

    async def validate(self, query: GetUserQuery) -> None:
        """Validate query."""
        if not query.user_id:
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "user_id", "reason": "cannot be empty"},
            )

    async def handle(self, query: GetUserQuery) -> UserDTO:
        """Handle query execution and return DTO."""
        user_repo = self.uow.repository(User)

        user = await user_repo.get(query.user_id)  # type: ignore[arg-type]
        if not user:
            raise ApplicationException(
                error_code=CommonErrors.NOT_FOUND,
                details={"resource": "user", "id": query.user_id},
            )

        # Use mapper for conversion (SOLID compliant)
        return self.mapper.to_dto(user)
