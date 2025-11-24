"""User API routes (FastAPI) - Thin Interface Layer.

This layer only handles HTTP concerns:
1. Request/Response models (Pydantic)
2. Dependency injection
3. Request → Command/Query conversion
4. Domain → Response conversion

All business logic is in the Application layer (Use Cases).
"""

from typing import Annotated, Any

from bento.persistence.uow import SQLAlchemyUnitOfWork
from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr

from contexts.identity.application.commands import (
    CreateUserCommand,
    CreateUserUseCase,
    DeleteUserCommand,
    DeleteUserUseCase,
    UpdateUserCommand,
    UpdateUserUseCase,
)
from contexts.identity.application.queries import (
    GetUserQuery,
    GetUserUseCase,
    ListUsersQuery,
    ListUsersUseCase,
)
from contexts.identity.interfaces.presenters import user_to_dict
from shared.infrastructure.dependencies import get_uow

# Create router
router = APIRouter()


# ==================== Request/Response Models ====================


class CreateUserRequest(BaseModel):
    """Create user request model."""

    name: str
    email: EmailStr


class UpdateUserRequest(BaseModel):
    """Update user request model."""

    name: str | None = None
    email: EmailStr | None = None


class UserResponse(BaseModel):
    """User response model."""

    id: str
    name: str
    email: str


class ListUsersResponse(BaseModel):
    """List users response model."""

    items: list[UserResponse]
    total: int
    page: int
    page_size: int


# ==================== Dependency Injection ====================


async def get_create_user_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> CreateUserUseCase:
    """Get create user use case (dependency)."""
    return CreateUserUseCase(uow)


async def get_update_user_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> UpdateUserUseCase:
    """get_update_user_use_case (dependency)."""
    return UpdateUserUseCase(uow)


async def get_delete_user_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> DeleteUserUseCase:
    """get_delete_user_use_case (dependency)."""
    return DeleteUserUseCase(uow)


async def get_get_user_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> GetUserUseCase:
    """get_get_user_use_case (dependency)."""
    return GetUserUseCase(uow)


async def get_list_users_use_case(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> ListUsersUseCase:
    """get_list_users_use_case (dependency)."""
    return ListUsersUseCase(uow)


# ==================== API Routes ====================


@router.post(
    "/",
    response_model=UserResponse,
    status_code=201,
    summary="Create a new user",
    description="Create a new user with name and email",
)
async def create_user(
    request: CreateUserRequest,
    use_case: Annotated[CreateUserUseCase, Depends(get_create_user_use_case)],
) -> dict[str, Any]:
    """Create a new user.

    Args:
        request: Create user request
        use_case: Create user use case (injected)

    Returns:
        Created user data
    """
    # 1. Convert Request → Command
    command = CreateUserCommand(
        name=request.name,
        email=request.email,
    )

    # 2. Execute Use Case
    user = await use_case.execute(command)

    # 3. Convert Domain → Response
    return user_to_dict(user)


@router.get(
    "/",
    response_model=ListUsersResponse,
    summary="List users",
    description="List users with pagination",
)
async def list_users(
    use_case: Annotated[ListUsersUseCase, Depends(get_list_users_use_case)],
    page: int = 1,
    page_size: int = 10,
) -> dict[str, Any]:
    """List users with pagination.

    Args:
        use_case: List users use case (injected)
        page: Page number (1-indexed)
        page_size: Items per page

    Returns:
        Paginated user list
    """
    # 1. Convert Request → Query
    query = ListUsersQuery(
        page=page,
        page_size=page_size,
    )

    # 2. Execute Use Case
    result = await use_case.execute(query)

    # 3. Convert Domain → Response
    return {
        "items": [user_to_dict(user) for user in result.users],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a user",
    description="Retrieve a user by ID",
)
async def get_user(
    user_id: str,
    use_case: Annotated[GetUserUseCase, Depends(get_get_user_use_case)],
) -> dict[str, Any]:
    """Get a user by ID.

    Args:
        user_id: User identifier
        use_case: Get user use case (injected)

    Returns:
        User data
    """
    # 1. Convert Request → Query
    query = GetUserQuery(user_id=user_id)

    # 2. Execute Use Case
    user = await use_case.execute(query)

    # 3. Convert Domain → Response
    return user_to_dict(user)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
    description="Update user information",
)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    use_case: Annotated[UpdateUserUseCase, Depends(get_update_user_use_case)],
) -> dict[str, Any]:
    """Update a user.

    Args:
        user_id: User identifier
        request: Update user request
        use_case: Update user use case (injected)

    Returns:
        Updated user data
    """
    # 1. Convert Request → Command
    command = UpdateUserCommand(
        user_id=user_id,
        name=request.name,
        email=request.email,
    )

    # 2. Execute Use Case
    user = await use_case.execute(command)

    # 3. Convert Domain → Response
    return user_to_dict(user)


@router.delete(
    "/{user_id}",
    status_code=204,
    summary="Delete a user",
    description="Soft delete a user",
)
async def delete_user(
    user_id: str,
    use_case: Annotated[DeleteUserUseCase, Depends(get_delete_user_use_case)],
) -> None:
    """Delete a user (soft delete).

    Args:
        user_id: User identifier
        use_case: Delete user use case (injected)
    """
    # 1. Convert Request → Command
    command = DeleteUserCommand(user_id=user_id)

    # 2. Execute Use Case
    await use_case.execute(command)

    # 3. No response for 204
