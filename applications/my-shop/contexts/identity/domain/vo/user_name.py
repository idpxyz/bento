"""UserName 值对象 - 用户名称的业务规则封装"""

from __future__ import annotations

from dataclasses import dataclass

from bento.domain import ValueObject


@dataclass(frozen=True)
class UserName(ValueObject[str]):
    """UserName 值对象.

    封装用户名称的业务规则：
    - 不能为空
    - 长度限制 (2-50)
    - 自动去除首尾空格
    - 不允许特殊字符（可选）

    使用示例：
        ```python
        name = UserName.create("张三")
        print(name.value)  # "张三"
        print(len(name))   # 2
        ```
    """

    value: str

    # 业务规则常量
    MIN_LENGTH = 2
    MAX_LENGTH = 50

    def validate(self) -> None:
        """验证用户名"""
        if not self.value:
            raise ValueError("User name cannot be empty")

        # 规范化：去除首尾空格
        normalized = self.value.strip()
        object.__setattr__(self, "value", normalized)

        # 长度验证
        if len(normalized) < self.MIN_LENGTH:
            raise ValueError(
                f"User name must be at least {self.MIN_LENGTH} characters, got {len(normalized)}"
            )

        if len(normalized) > self.MAX_LENGTH:
            raise ValueError(
                f"User name must be at most {self.MAX_LENGTH} characters, got {len(normalized)}"
            )

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"UserName('{self.value}')"

    def __len__(self) -> int:
        return len(self.value)

    def starts_with(self, prefix: str) -> bool:
        """检查是否以指定前缀开头"""
        return self.value.startswith(prefix)

    def contains(self, substring: str) -> bool:
        """检查是否包含指定子串"""
        return substring in self.value
