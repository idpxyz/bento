"""Bento Security module.

Provides authentication and authorization utilities.

Note: Multi-tenant support has been moved to `bento.multitenancy` module.

Example:
    ```python
    from bento.security import SecurityContext

    # Get current user
    user = SecurityContext.get_current_user()
    ```
"""

__all__: list[str] = []

