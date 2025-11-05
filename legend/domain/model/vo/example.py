"""
ValueObject基类使用示例

展示如何使用基于Pydantic v2的ValueObject基类创建值对象。
"""

from typing import Optional

from pydantic import Field, field_validator

from .base import ValueObject


class EmailVO(ValueObject):
    """邮箱值对象示例"""
    address: str = Field(..., description="邮箱地址")
    verified: bool = Field(default=False, description="是否已验证")

    @field_validator('address')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """验证邮箱格式"""
        if '@' not in v:
            raise ValueError("Invalid email format")
        return v.lower().strip()

    def verify(self) -> "EmailVO":
        """创建已验证的邮箱值对象"""
        return self.copy(verified=True)


class MoneyVO(ValueObject):
    """金额值对象示例"""
    amount: float = Field(..., description="金额")
    currency: str = Field(default="CNY", description="货币代码")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        """验证金额"""
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return round(v, 2)

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """验证货币代码"""
        return v.upper()

    def add(self, other: "MoneyVO") -> "MoneyVO":
        """金额相加"""
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return self.copy(amount=self.amount + other.amount)

    def multiply(self, factor: float) -> "MoneyVO":
        """金额乘以系数"""
        return self.copy(amount=self.amount * factor)


class AddressVO(ValueObject):
    """地址值对象示例"""
    street: str = Field(..., description="街道")
    city: str = Field(..., description="城市")
    country: str = Field(..., description="国家")
    postal_code: Optional[str] = Field(None, description="邮政编码")

    @field_validator('street', 'city', 'country')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """验证非空"""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    def with_postal_code(self, postal_code: str) -> "AddressVO":
        """添加邮政编码"""
        return self.copy(postal_code=postal_code)


# 使用示例
def demonstrate_value_objects():
    """演示值对象的使用"""

    # 创建邮箱值对象
    email = EmailVO(address="user@example.com")
    print(f"Email: {email}")
    print(f"Verified: {email.verified}")

    # 创建已验证的邮箱
    verified_email = email.verify()
    print(f"Verified email: {verified_email}")

    # 创建金额值对象
    money1 = MoneyVO(amount=100.50, currency="CNY")
    money2 = MoneyVO(amount=50.25, currency="CNY")

    # 金额相加
    total = money1.add(money2)
    print(f"Total: {total}")

    # 金额乘以系数
    doubled = money1.multiply(2)
    print(f"Doubled: {doubled}")

    # 创建地址值对象
    address = AddressVO(
        street="123 Main St",
        city="Beijing",
        country="China"
    )
    print(f"Address: {address}")

    # 添加邮政编码
    address_with_code = address.with_postal_code("100000")
    print(f"Address with code: {address_with_code}")

    # 序列化
    print(f"Email as dict: {email.to_dict()}")
    print(f"Email as JSON: {email.to_json()}")

    # 从字典创建
    email_from_dict = EmailVO.from_dict({"address": "test@example.com"})
    print(f"Email from dict: {email_from_dict}")

    # 相等性比较
    email1 = EmailVO(address="same@example.com")
    email2 = EmailVO(address="same@example.com")
    print(f"Emails equal: {email1 == email2}")

    # 哈希值
    print(f"Email hash: {hash(email1)}")


if __name__ == "__main__":
    demonstrate_value_objects()
