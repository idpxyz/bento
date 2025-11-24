"""Email 值对象 - 不可变且自校验"""

from __future__ import annotations

import re
from dataclasses import dataclass

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


@dataclass(frozen=True)
class Email:
    """Email 值对象.

    值对象特征：
    - 不可变（frozen=True）
    - 自包含验证逻辑
    - 值相等而非引用相等
    - 无标识（ID）

    使用示例：
        ```python
        email = Email("user@example.com")
        print(email.value)  # "user@example.com"
        print(email.domain)  # "example.com"
        print(email.local_part)  # "user"
        ```
    """

    value: str

    def __post_init__(self):
        """验证邮箱格式"""
        if not self.value:
            raise ValueError("Email cannot be empty")

        # 规范化：转小写
        normalized = self.value.lower().strip()
        object.__setattr__(self, "value", normalized)

        # 验证格式
        if not EMAIL_REGEX.match(normalized):
            raise ValueError(f"Invalid email format: {self.value}")

    @property
    def local_part(self) -> str:
        """获取邮箱本地部分（@之前）"""
        return self.value.split("@")[0]

    @property
    def domain(self) -> str:
        """获取邮箱域名部分（@之后）"""
        return self.value.split("@")[1]

    def is_same_domain(self, other: Email) -> bool:
        """检查是否同域名"""
        return self.domain == other.domain

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Email('{self.value}')"
