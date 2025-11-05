"""用户ID值对象

定义用户ID值对象，确保ID的一致性和不可变性。
"""

import uuid
from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class UserId:
    """用户ID值对象
    
    不可变的用户标识符，使用UUID实现。
    
    Attributes:
        value: UUID值
    """
    
    value: uuid.UUID
    
    def __init__(self, value: Optional[Union[str, uuid.UUID]] = None):
        """初始化用户ID
        
        Args:
            value: UUID字符串或UUID对象，如果为None则生成新的UUID
        """
        if value is None:
            # 生成新的UUID
            uuid_value = uuid.uuid4()
        elif isinstance(value, str):
            # 从字符串转换为UUID
            try:
                uuid_value = uuid.UUID(value)
            except ValueError:
                raise ValueError(f"Invalid UUID string: {value}")
        elif isinstance(value, uuid.UUID):
            # 直接使用提供的UUID
            uuid_value = value
        else:
            raise TypeError(f"Expected str or UUID, got {type(value).__name__}")
        
        # 由于dataclass是frozen=True，需要使用object.__setattr__设置属性
        object.__setattr__(self, 'value', uuid_value)
    
    def __str__(self) -> str:
        """字符串表示"""
        return str(self.value)
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"UserId({str(self.value)})"
    
    def __eq__(self, other) -> bool:
        """相等比较"""
        if not isinstance(other, UserId):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        """哈希值"""
        return hash(self.value) 