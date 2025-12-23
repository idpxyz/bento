"""Bento Security module.

Provides security context for request-scoped data.

Note: Multi-tenant support is in `bento.multitenancy` module.

Example:
    ```python
    from bento.security import RequestContext

    ctx = RequestContext(
        user_id="user-123",
        scopes=["read", "write"],
    )
    ```
"""

from bento.security.context import RequestContext

__all__ = [
    "RequestContext",
]

