"""联系人值对象"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Contact:
    """联系人值对象

    表示一个联系人信息，包含姓名、电话和邮箱。
    值对象是不可变的，一旦创建就不能修改。
    """
    name: Optional[str]
    phone: Optional[str]
    email: Optional[str]

    def __post_init__(self):
        """初始化后验证数据"""
        if self.phone and not self._is_valid_phone(self.phone):
            raise ValueError("Invalid phone number")
        if self.email and not self._is_valid_email(self.email):
            raise ValueError("Invalid email address")

    @staticmethod
    def _is_valid_phone(phone: str) -> bool:
        """验证电话号码格式

        Args:
            phone: 电话号码

        Returns:
            bool: 是否有效
        """
        # 简单的电话号码验证，可以根据实际需求修改
        return bool(phone and len(phone) >= 8)

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """验证邮箱格式

        Args:
            email: 邮箱地址

        Returns:
            bool: 是否有效
        """
        # 简单的邮箱验证，可以根据实际需求修改
        return bool(email and '@' in email and '.' in email)

    @classmethod
    def from_dict(cls, data: dict) -> Optional['Contact']:
        """从字典创建联系人值对象

        Args:
            data: 包含 name、phone 和 email 的字典

        Returns:
            Optional[Contact]: 联系人值对象，如果数据无效则返回 None
        """
        try:
            return cls(
                name=data.get('contact_name'),
                phone=data.get('contact_phone'),
                email=data.get('contact_email')
            )
        except ValueError:
            return None

    def to_dict(self) -> dict:
        """转换为字典

        Returns:
            dict: 包含 name、phone 和 email 的字典
        """
        return {
            'contact_name': self.name,
            'contact_phone': self.phone,
            'contact_email': self.email
        }
