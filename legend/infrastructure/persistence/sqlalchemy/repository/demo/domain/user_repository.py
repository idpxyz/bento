"""用户仓储接口

定义用户仓储的抽象接口，遵循依赖倒置原则。
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from .user import User
from .user_id import UserId


class UserRepository(ABC):
    """用户仓储接口

    定义用户仓储的操作契约，领域层依赖该抽象接口而非具体实现。
    """

    @abstractmethod
    async def save(self, user: User) -> User:
        """保存用户

        创建或更新用户，根据用户ID是否存在决定是创建还是更新。

        Args:
            user: 用户实体

        Returns:
            保存后的用户实体
        """
        pass

    @abstractmethod
    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """根据ID查找用户

        Args:
            user_id: 用户ID

        Returns:
            用户实体，如果不存在则返回None
        """
        pass

    # @abstractmethod
    # async def find_by_username(self, username: str) -> Optional[User]:
    #     """根据用户名查找用户

    #     Args:
    #         username: 用户名

    #     Returns:
    #         用户实体，如果不存在则返回None
    #     """
    #     pass

    # @abstractmethod
    # async def find_all(self) -> List[User]:
    #     """查找所有用户

    #     Returns:
    #         用户实体列表
    #     """
    #     pass

    @abstractmethod
    async def delete(self, user: User) -> None:
        """删除用户

        Args:
            user: 要删除的用户实体
        """
        pass
