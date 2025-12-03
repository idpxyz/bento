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

        # ✅ 使用 Framework 的 paginate() 便捷方法（性能提升 10-100x）
        page_result = await user_repo.paginate(page=query.page, size=query.page_size)

        # Convert to DTOs
        user_dtos = self.mapper.to_dto_list(page_result.items)

        return ListUsersResult(
            users=user_dtos,
            total=page_result.total,
            page=page_result.page,
            page_size=page_result.size,
        )
