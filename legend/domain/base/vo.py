
from typing import Any, Dict, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar('T')


class BaseVO(BaseModel):
    """值对象基类

    基于Pydantic v2的值对象基类，提供：
    - 不可变性
    - 自动验证
    - 序列化支持
    - 类型安全
    """

    model_config = ConfigDict(
        frozen=True,  # 确保不可变性
        validate_assignment=True,  # 赋值时验证
        extra="forbid",  # 禁止额外字段
        str_strip_whitespace=True,  # 自动去除字符串空白
        validate_default=True,  # 验证默认值
    )

    def validate(self) -> None:
        """验证值对象的有效性，子类可重写此方法添加自定义验证"""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """将值对象转换为字典"""
        return self.model_dump()

    def to_json(self) -> str:
        """将值对象转换为JSON字符串"""
        return self.model_dump_json()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseVO":
        """从字典创建值对象"""
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, json_str: str) -> "BaseVO":
        """从JSON字符串创建值对象"""
        return cls.model_validate_json(json_str)

    def copy(self, **changes) -> "BaseVO":
        """创建值对象的副本，支持部分更新"""
        return self.model_copy(update=changes)

    def __eq__(self, other: Any) -> bool:
        """值对象相等性比较"""
        if not isinstance(other, self.__class__):
            return False
        return self.model_dump() == other.model_dump()

    def __hash__(self) -> int:
        """值对象哈希值，基于内容"""
        return hash(tuple(sorted(self.model_dump().items())))

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}({self.model_dump()})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"{self.__class__.__name__}({self.model_dump()})"
