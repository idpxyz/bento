"""领域对象与值对象映射示例。

本示例展示了如何在领域驱动设计(DDD)架构中使用映射器系统，特别是：
1. 领域实体与值对象之间的映射
2. 使用VOMapper进行值对象映射
3. 保护领域边界
4. 处理领域特定的验证和业务规则
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from idp.framework.infrastructure.mapper.core.mapper import MapperBuilder
from idp.framework.infrastructure.mapper.vo import VOMapper



# 值对象定义
@dataclass(frozen=True)
class EmailAddress:
    """电子邮件地址值对象"""
    value: str
    
    def __post_init__(self):
        if not self.value or "@" not in self.value:
            raise ValueError("Invalid email address")
    
    def __str__(self):
        return self.value


@dataclass(frozen=True)
class PhoneNumber:
    """电话号码值对象"""
    country_code: str
    number: str
    
    def __post_init__(self):
        if not self.number:
            raise ValueError("Phone number cannot be empty")
    
    def __str__(self):
        return f"{self.country_code}{self.number}"


@dataclass(frozen=True)
class Address:
    """地址值对象"""
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    
    def __post_init__(self):
        if not self.street or not self.city or not self.country:
            raise ValueError("Street, city and country are required")
    
    def __str__(self):
        return f"{self.street}, {self.city}, {self.state} {self.postal_code}, {self.country}"


class CustomerStatus(Enum):
    """客户状态枚举"""
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


@dataclass(frozen=True)
class Money:
    """金额值对象"""
    amount: float
    currency: str
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter code")
    
    def __str__(self):
        return f"{self.amount:.2f} {self.currency}"


# 领域实体
@dataclass
class Customer:
    """客户领域实体"""
    id: UUID
    email: EmailAddress
    phone: PhoneNumber
    address: Address
    status: CustomerStatus
    credit_limit: Money
    registration_date: datetime
    last_purchase_date: Optional[datetime] = None
    total_purchases: int = 0
    loyalty_points: int = 0
    
    @classmethod
    def create(cls, email: str, phone_dict: Dict[str, str], address_dict: Dict[str, str], 
               credit_limit: float, currency: str = "USD") -> 'Customer':
        """创建新客户的工厂方法"""
        # 创建值对象
        email_vo = EmailAddress(email)
        phone_vo = PhoneNumber(
            country_code=phone_dict.get("country_code", "+1"),
            number=phone_dict.get("number", "")
        )
        address_vo = Address(
            street=address_dict.get("street", ""),
            city=address_dict.get("city", ""),
            state=address_dict.get("state", ""),
            postal_code=address_dict.get("postal_code", ""),
            country=address_dict.get("country", "")
        )
        money_vo = Money(credit_limit, currency)
        
        # 创建客户实体
        return Customer(
            id=uuid4(),
            email=email_vo,
            phone=phone_vo,
            address=address_vo,
            status=CustomerStatus.NEW,
            credit_limit=money_vo,
            registration_date=datetime.now()
        )
    
    def update_status(self, new_status: CustomerStatus) -> None:
        """更新客户状态"""
        # 在实际应用中，这里可能有状态转换的业务规则
        self.status = new_status
    
    def record_purchase(self, amount: float) -> None:
        """记录购买并更新统计信息"""
        self.total_purchases += 1
        self.last_purchase_date = datetime.now()
        self.loyalty_points += int(amount / 10)  # 简单的积分规则：每消费10元获得1积分


# 值对象DTO（用于API或持久化）
@dataclass
class EmailAddressDTO:
    """电子邮件地址DTO"""
    email: str = ""


@dataclass
class PhoneNumberDTO:
    """电话号码DTO"""
    country_code: str = ""
    number: str = ""


@dataclass
class AddressDTO:
    """地址DTO"""
    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""


@dataclass
class MoneyDTO:
    """金额DTO"""
    amount: float = 0.0
    currency: str = "USD"


# 客户DTO（用于API或持久化）
@dataclass
class CustomerDTO:
    """客户DTO"""
    id: str = ""  # UUID作为字符串
    email: str = ""
    phone: PhoneNumberDTO = field(default_factory=PhoneNumberDTO)
    address: AddressDTO = field(default_factory=AddressDTO)
    status: str = ""  # 枚举值作为字符串
    credit_limit: MoneyDTO = field(default_factory=MoneyDTO)
    registration_date: str = ""  # ISO格式的日期字符串
    last_purchase_date: Optional[str] = None  # ISO格式的日期字符串
    total_purchases: int = 0
    loyalty_points: int = 0


def domain_vo_mapping_example():
    """领域对象与值对象映射示例"""
    print("\n=== 领域对象与值对象映射示例 ===")
    
    try:
        # 创建客户领域实体
        customer = Customer.create(
            email="john.doe@example.com",
            phone_dict={"country_code": "+1", "number": "555-123-4567"},
            address_dict={
                "street": "123 Main St",
                "city": "Boston",
                "state": "MA",
                "postal_code": "02108",
                "country": "USA"
            },
            credit_limit=5000.00,
            currency="USD"
        )
        
        # 模拟一些业务操作
        customer.update_status(CustomerStatus.ACTIVE)
        customer.record_purchase(250.00)
        customer.record_purchase(170.00)
        
        # 打印领域实体信息
        print("创建的客户领域实体:")
        print(f"ID: {customer.id}")
        print(f"邮箱: {customer.email}")
        print(f"电话: {customer.phone}")
        print(f"地址: {customer.address}")
        print(f"状态: {customer.status}")
        print(f"信用额度: {customer.credit_limit}")
        print(f"注册日期: {customer.registration_date}")
        print(f"最后购买日期: {customer.last_purchase_date}")
        print(f"总购买次数: {customer.total_purchases}")
        print(f"积分: {customer.loyalty_points}")
        
        # 手动执行映射
        try:
            # 手动创建DTO对象
            customer_dto = CustomerDTO()
            
            # 手动映射简单字段
            customer_dto.id = str(customer.id)
            customer_dto.email = customer.email.value
            customer_dto.status = customer.status.value
            customer_dto.total_purchases = customer.total_purchases
            customer_dto.loyalty_points = customer.loyalty_points
            
            # 手动映射日期字段
            customer_dto.registration_date = customer.registration_date.isoformat() if customer.registration_date else None
            customer_dto.last_purchase_date = customer.last_purchase_date.isoformat() if customer.last_purchase_date else None
            
            # 手动映射嵌套对象 - 电话
            customer_dto.phone.country_code = customer.phone.country_code
            customer_dto.phone.number = customer.phone.number
            
            # 手动映射嵌套对象 - 地址
            customer_dto.address.street = customer.address.street
            customer_dto.address.city = customer.address.city
            customer_dto.address.state = customer.address.state
            customer_dto.address.postal_code = customer.address.postal_code
            customer_dto.address.country = customer.address.country
            
            # 手动映射嵌套对象 - 金额
            customer_dto.credit_limit.amount = customer.credit_limit.amount
            customer_dto.credit_limit.currency = customer.credit_limit.currency
            
            # 打印DTO信息
            print("\n手动映射后的客户DTO:")
            print(f"ID: {customer_dto.id}")
            print(f"邮箱: {customer_dto.email}")
            print(f"电话: {customer_dto.phone.country_code} {customer_dto.phone.number}")
            print(f"地址: {customer_dto.address.street}, {customer_dto.address.city}, {customer_dto.address.state} {customer_dto.address.postal_code}, {customer_dto.address.country}")
            print(f"状态: {customer_dto.status}")
            print(f"信用额度: {customer_dto.credit_limit.amount} {customer_dto.credit_limit.currency}")
            print(f"注册日期: {customer_dto.registration_date}")
            print(f"最后购买日期: {customer_dto.last_purchase_date}")
            print(f"总购买次数: {customer_dto.total_purchases}")
            print(f"积分: {customer_dto.loyalty_points}")
            
            # 显示MapperBuilder配置示例（不执行）
            print("\nMapperBuilder的配置示例（不执行）:")
            print("""
        # 1. 创建电子邮件地址映射器
        email_mapper = MapperBuilderImpl.for_types(EmailAddress, EmailAddressDTO) \\
            .map_custom("email", lambda email_vo: email_vo.value) \\
            .build()
        
        # 2. 创建电话号码映射器
        phone_mapper = MapperBuilderImpl.for_types(PhoneNumber, PhoneNumberDTO) \\
            .auto_map() \\
            .build()
        
        # 3. 创建地址映射器
        address_mapper = MapperBuilderImpl.for_types(Address, AddressDTO) \\
            .auto_map() \\
            .build()
        
        # 4. 创建金额映射器
        money_mapper = MapperBuilderImpl.for_types(Money, MoneyDTO) \\
            .auto_map() \\
            .build()
        
        # 5. 创建客户领域实体映射器
        customer_mapper = MapperBuilderImpl.for_types(Customer, CustomerDTO) \\
            .map_custom("id", lambda c: str(c.id)) \\
            .map_custom("email", lambda c: c.email.value) \\
            .map_nested("phone", "phone", phone_mapper) \\
            .map_nested("address", "address", address_mapper) \\
            .map_custom("status", lambda c: c.status.value) \\
            .map_nested("credit_limit", "credit_limit", money_mapper) \\
            .map_custom("registration_date", lambda c: c.registration_date.isoformat() if c.registration_date else None) \\
            .map_custom("last_purchase_date", lambda c: c.last_purchase_date.isoformat() if c.last_purchase_date else None) \\
            .map("total_purchases", "total_purchases") \\
            .map("loyalty_points", "loyalty_points") \\
            .build()
            """)
            
        except Exception as e:
            print(f"手动映射过程中发生错误: {str(e)}")
        
        # 演示领域对象映射中的异常处理
        print("\n演示领域对象映射中的异常处理:")
        print("在领域驱动设计中，反向映射（DTO到领域实体）通常需要特殊处理:")
        print("""
        # 反向映射通常需要通过工厂方法或领域服务来创建领域实体
        # 简单地使用映射器可能会绕过领域实体的验证和业务规则
        
        # 错误示例 - 尝试直接映射到领域实体
        customer_reverse = customer_mapper.map_to_source(customer_dto)
        
        # 正确示例 - 使用工厂方法创建领域实体
        customer_reverse = Customer.create(
            email=customer_dto.email,
            phone_dict={
                "country_code": customer_dto.phone.country_code,
                "number": customer_dto.phone.number
            },
            address_dict={
                "street": customer_dto.address.street,
                "city": customer_dto.address.city,
                "state": customer_dto.address.state,
                "postal_code": customer_dto.address.postal_code,
                "country": customer_dto.address.country
            },
            credit_limit=customer_dto.credit_limit.amount,
            currency=customer_dto.credit_limit.currency
        )
        
        # 然后手动设置其他属性
        customer_reverse.status = CustomerStatus[customer_dto.status]
        customer_reverse.total_purchases = customer_dto.total_purchases
        customer_reverse.loyalty_points = customer_dto.loyalty_points
        """)
        
    except Exception as e:
        print(f"映射过程中发生错误: {str(e)}")


if __name__ == "__main__":
    domain_vo_mapping_example() 