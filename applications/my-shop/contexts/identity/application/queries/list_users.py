"""List users query and use case."""

from dataclasses import dataclass

from bento.application.ports import IUnitOfWork
from bento.application.usecase import BaseUseCase

from contexts.identity.domain.models.user import User


@dataclass
class ListUsersResult:
    """List users result.

    Attributes:
        users: List of users
        total: Total count of users
        page: Current page number
        page_size: Items per page
    """

    users: list[User]
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


class ListUsersUseCase(BaseUseCase[ListUsersQuery, ListUsersResult]):
    """List users use case.

    Retrieves a paginated list of users.
    """

    def __init__(self, uow: IUnitOfWork) -> None:
        super().__init__(uow)

    async def validate(self, query: ListUsersQuery) -> None:
        """Validate query."""
        # Page and page_size validation
        pass  # Validation can be added if needed

    async def handle(self, query: ListUsersQuery) -> ListUsersResult:
        """Handle query execution."""
        user_repo = self.uow.repository(User)

        # Calculate offset
        offset = (query.page - 1) * query.page_size

        # Get users with pagination
        users = await user_repo.list_paginated(
            limit=query.page_size,
            offset=offset,
        )

        # Get total count
        total = await user_repo.total_count()

        return ListUsersResult(
            users=users,
            total=total,
            page=query.page,
            page_size=query.page_size,
        )
