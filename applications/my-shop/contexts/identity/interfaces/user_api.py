"""User API routes (FastAPI) - Thin Interface Layer.

This layer only handles HTTP concerns:
1. Request/Response models (Pydantic)
2. Dependency injection
3. Request → Command/Query conversion
4. Domain → Response conversion

All business logic is in the Application layer (Handlers)."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

from contexts.identity.application.commands import (
    CreateUserCommand,
    CreateUserHandler,
    DeleteUserCommand,
    DeleteUserHandler,
    UpdateUserCommand,
    UpdateUserHandler,
)
from contexts.identity.application.queries import (
    GetUserHandler,
    GetUserQuery,
    ListUsersHandler,
    ListUsersQuery,
)
from contexts.identity.interfaces.presenters import user_to_dict
from shared.infrastructure.dependencies import handler_dependency

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
#
# Note: All Handlers use handler_dependency() for clean OpenAPI schemas.
# No need for individual DI functions - universal factory pattern!


# ==================== API Routes ====================


@router.post(
    "/",
    response_model=UserResponse,
    status_code=201,
    summary="Create a new user",
)
async def create_user(
    request: CreateUserRequest,
    handler: CreateUserHandler = handler_dependency(CreateUserHandler),
) -> UserResponse:
    """Create a new user."""
    # 1. Convert Request → Command
    command = CreateUserCommand(
        name=request.name,
        email=request.email,
    )

    # 2. Execute Handler
    user = await handler.execute(command)

    # 3. Convert Domain → Response
    return UserResponse(**user_to_dict(user))


@router.get(
    "/",
    response_model=ListUsersResponse,
    summary="List users",
    description="List users with pagination",
)
async def list_users(
    handler: ListUsersHandler = handler_dependency(ListUsersHandler),
    page: int = 1,
    page_size: int = 10,
) -> ListUsersResponse:
    """List users with pagination."""
    # 1. Convert Request → Query
    query = ListUsersQuery(
        page=page,
        page_size=page_size,
    )

    # 2. Execute Handler
    result = await handler.execute(query)

    # 3. Convert DTO → Response (使用 model_dump)
    return ListUsersResponse(
        items=[UserResponse(**user.model_dump()) for user in result.users],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a user",
    description="Retrieve a user by ID",
)
async def get_user(
    user_id: str,
    handler: GetUserHandler = handler_dependency(GetUserHandler),
) -> UserResponse:
    """Get a user by ID."""
    # 1. Convert Request → Query
    query = GetUserQuery(user_id=user_id)

    # 2. Execute Handler
    user = await handler.execute(query)

    # 3. Convert DTO → Response (使用 model_dump)
    return UserResponse(**user.model_dump())


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
    description="Update user information",
)
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    handler: UpdateUserHandler = handler_dependency(UpdateUserHandler),
) -> UserResponse:
    """Update a user."""
    # 1. Convert Request → Command
    command = UpdateUserCommand(
        user_id=user_id,
        name=request.name,
        email=request.email,
    )

    # 2. Execute Handler
    user = await handler.execute(command)

    # 3. Convert Domain → Response
    return UserResponse(**user_to_dict(user))


@router.delete(
    "/{user_id}",
    status_code=204,
    summary="Delete a user",
    description="Soft delete a user",
)
async def delete_user(
    user_id: str,
    handler: DeleteUserHandler = handler_dependency(DeleteUserHandler),
) -> None:
    """Delete a user (soft delete)."""
    # 1. Convert Request → Command
    command = DeleteUserCommand(user_id=user_id)

    # 2. Execute Handler
    await handler.execute(command)

    # 3. No response for 204
