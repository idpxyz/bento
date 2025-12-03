"""List users query and handler."""

from dataclasses import dataclass

from bento.application import QueryHandler, query_handler
from bento.application.ports.uow import UnitOfWork

from contexts.identity.application.dto.user_dto import UserDTO
from contexts.identity.application.mappers.user_dto_mapper import UserDTOMapper
from contexts.identity.domain.models.user import User


@dataclass
class ListUsersResult:
    """List users result.

    Attributes:
        users: List of user DTOs
        total: Total count of users
        page: Current page number
        page_size: Items per page
    """

    users: list[UserDTO]
    total: int
    page: int
    page_size: int


@dataclass
class ListUsersQuery:
    """List users query.

    Attributes:
        page: Page number (1-indexed)
        page_size: Items per page
    """

    page: int = 1
    page_size: int = 10


@query_handler
class ListUsersHandler(QueryHandler[ListUsersQuery, ListUsersResult]):
    """List users handler.

    Retrieves a paginated list of users and returns DTOs.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        super().__init__(uow)
        self.mapper = UserDTOMapper()

    async def validate(self, query: ListUsersQuery) -> None:
        """Validate query."""
        # Page and page_size validation
        pass  # Validation can be added if needed

    async def handle(self, query: ListUsersQuery) -> ListUsersResult:
        """Handle query execution and return DTOs."""
        user_repo = self.uow.repository(User)

        # Get all users (simplified for now - could add pagination later)
        users = await user_repo.find_all()

        # Convert to DTOs
        user_dtos = self.mapper.to_dto_list(users)

        # Simple pagination (in-memory for demo)
        start_idx = (query.page - 1) * query.page_size
        end_idx = start_idx + query.page_size
        paginated_dtos = user_dtos[start_idx:end_idx]

        return ListUsersResult(
            users=paginated_dtos,
            total=len(user_dtos),
            page=query.page,
            page_size=query.page_size,
        )
