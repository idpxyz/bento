"""Entity base module."""

from abc import ABC
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, Union
from uuid import UUID

T = TypeVar('T')


@dataclass
class Identifier(Generic[T]):
    """标识符值对象基类"""
    value: T

    def __eq__(self, other: object) -> bool:
        """比较两个标识符是否相等"""
        if not isinstance(other, Identifier):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """获取标识符的哈希值"""
        return hash(self.value)

    def __str__(self) -> str:
        """获取标识符的字符串表示"""
        return str(self.value)


class Entity(ABC):
    """
    实体基类

    所有实体都应继承此类，提供唯一标识和版本控制
    """

    def __init__(self, id: Union[UUID, str, None] = None):
        """初始化实体

        Args:
            id: 实体ID，可以是UUID、字符串或None
        """
        if isinstance(id, str):
            self._id = UUID(id)
        elif isinstance(id, UUID):
            self._id = id
        elif id is None:
            self._id = None
        else:
            raise ValueError(f"Invalid id type: {type(id)}")

    @property
    def id(self) -> UUID:
        """获取实体ID"""
        if self._id is None:
            raise ValueError("Entity ID is not set")
        return self._id

    @id.setter
    def id(self, value: Union[UUID, str]) -> None:
        """设置实体ID

        Args:
            value: 新的实体ID，可以是UUID或字符串

        Raises:
            ValueError: 如果ID类型无效
        """
        if isinstance(value, str):
            self._id = UUID(value)
        elif isinstance(value, UUID):
            self._id = value
        else:
            raise ValueError(f"Invalid id type: {type(value)}")

    def __eq__(self, other: Any) -> bool:
        """比较两个实体是否相等"""
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """获取实体的哈希值"""
        return hash(self.id)
