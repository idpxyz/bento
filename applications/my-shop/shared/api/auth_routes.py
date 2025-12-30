"""Authentication API routes.

Provides endpoints for authentication-related operations.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from bento.security import SecurityContext, CurrentUser, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class CurrentUserResponse(BaseModel):
    """Response model for current user with tenant context."""

    id: str
    permissions: list[str]
    roles: list[str]
    tenant_id: str | None = None
    metadata: dict | None = None

    class Config:
        from_attributes = True


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_endpoint(
    current_user: CurrentUser | None = Depends(get_current_user),
) -> CurrentUserResponse:
    """Get current authenticated user with tenant context.

    Returns:
        Current user information including ID, permissions, roles, tenant, and metadata.

    Example:
        ```bash
        # Without tenant
        curl http://localhost:8000/api/v1/auth/me

        # With tenant
        curl -H "X-Tenant-ID: tenant-a" http://localhost:8000/api/v1/auth/me
        ```

        Response:
        ```json
        {
            "id": "demo-user",
            "permissions": ["*"],
            "roles": ["admin"],
            "tenant_id": "tenant-a",
            "metadata": {
                "stub": true,
                "environment": "development",
                "username": "demo"
            }
        }
        ```
    """
    from bento.security import SecurityContext

    tenant_id = SecurityContext.get_tenant()

    if current_user is None:
        # This shouldn't happen if require_auth=True, but handle it gracefully
        return CurrentUserResponse(
            id="anonymous",
            permissions=[],
            roles=[],
            tenant_id=tenant_id,
            metadata={"authenticated": False},
        )

    return CurrentUserResponse(
        id=current_user.id,
        permissions=list(current_user.permissions) if current_user.permissions else [],
        roles=list(current_user.roles) if current_user.roles else [],
        tenant_id=tenant_id,
        metadata=current_user.metadata,
    )


@router.get("/me/context")
async def get_security_context():
    """Get current security context (for debugging).

    This endpoint shows the raw security context information,
    useful for debugging authentication and tenant issues.

    Returns:
        Raw security context data including user and tenant information.

    Example:
        ```bash
        # Without tenant
        curl http://localhost:8000/api/v1/auth/me/context

        # With tenant
        curl -H "X-Tenant-ID: tenant-a" http://localhost:8000/api/v1/auth/me/context
        ```
    """
    user = SecurityContext.get_user()
    tenant_id = SecurityContext.get_tenant()

    if user is None:
        return {
            "authenticated": False,
            "user": None,
            "tenant_id": tenant_id,
            "message": "No user in security context",
        }

    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "permissions": user.permissions,
            "roles": user.roles,
            "metadata": user.metadata,
        },
        "tenant_id": tenant_id,
        "has_permission_check": {
            "admin": user.has_permission("admin"),
            "user": user.has_permission("user"),
        },
    }
