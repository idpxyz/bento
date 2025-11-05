"""Example: User domain error codes.

This is an EXAMPLE of how to define domain-specific error codes.
In your real project, create this file in your business module:
    modules/user/errors.py

Usage:
    ```python
    from modules.user.errors import UserErrors
    from core.errors import DomainException
    
    raise DomainException(
        error_code=UserErrors.USER_NOT_FOUND,
        details={"user_id": "123"}
    )
    ```
"""

from core.errors import ErrorCode


class UserErrors:
    """User domain error codes.
    
    These errors are specific to the User bounded context.
    """
    
    USER_NOT_FOUND = ErrorCode(
        code="USER_001",
        message="User not found",
        http_status=404,
    )
    """User with given ID doesn't exist"""
    
    USER_ALREADY_EXISTS = ErrorCode(
        code="USER_002",
        message="User already exists",
        http_status=409,
    )
    """User with same email/username already exists"""
    
    INVALID_EMAIL = ErrorCode(
        code="USER_003",
        message="Invalid email format",
        http_status=400,
    )
    """Email format is invalid"""
    
    INVALID_PASSWORD = ErrorCode(
        code="USER_004",
        message="Invalid password",
        http_status=400,
    )
    """Password doesn't meet requirements"""
    
    USER_INACTIVE = ErrorCode(
        code="USER_005",
        message="User account is inactive",
        http_status=403,
    )
    """User account is deactivated"""

