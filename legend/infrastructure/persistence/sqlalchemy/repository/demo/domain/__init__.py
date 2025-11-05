"""领域模型
   
用户领域的实体、值对象和仓储接口。
"""

from .user import User
from .user_id import UserId
from .user_repository import UserRepository

__all__ = [
    "User",
    "UserId",
    "UserRepository"
] 