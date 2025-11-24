"""Identity domain value objects.

值对象（Value Object）是 DDD 的核心概念：
- 不可变（immutable）
- 无标识（no identity）
- 值相等（value equality）
- 自包含验证（self-validating）
"""

from contexts.identity.domain.vo.email import Email
from contexts.identity.domain.vo.user_name import UserName

__all__ = [
    "Email",
    "UserName",
]
