"""嵌套对象映射示例。

本示例展示了如何使用映射器系统处理嵌套对象结构，包括：
1. 创建包含嵌套对象的源对象和目标对象类
2. 配置嵌套对象的映射器
3. 执行嵌套对象映射
4. 处理嵌套映射中的异常
"""

from dataclasses import dataclass
from typing import Optional

from idp.framework.infrastructure.mapper.core.mapper import MapperBuilder


# 嵌套对象类 - 源
@dataclass
class AddressEntity:
    """地址实体类（嵌套源对象）"""
    street: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = ""


@dataclass
class ContactInfoEntity:
    """联系信息实体类（嵌套源对象）"""
    email: str = ""
    phone: str = ""
    address: AddressEntity = None

    def __post_init__(self):
        if self.address is None:
            self.address = AddressEntity()


# 主源对象类
@dataclass
class CustomerEntity:
    """客户实体类（主源对象）"""
    id: int = 0
    first_name: str = ""
    last_name: str = ""
    contact_info: ContactInfoEntity = None
    is_active: bool = True

    def __post_init__(self):
        if self.contact_info is None:
            self.contact_info = ContactInfoEntity()


# 嵌套对象类 - 目标
@dataclass
class AddressDTO:
    """地址DTO类（嵌套目标对象）"""
    street_line: str = ""  # 注意字段名与源对象不同
    city: str = ""
    state: str = ""
    zip_code: str = ""  # 注意字段名与源对象不同
    country: str = ""


@dataclass
class ContactInfoDTO:
    """联系信息DTO类（嵌套目标对象）"""
    email_address: str = ""  # 注意字段名与源对象不同
    phone_number: str = ""  # 注意字段名与源对象不同
    address: AddressDTO = None

    def __post_init__(self):
        if self.address is None:
            self.address = AddressDTO()


# 主目标对象类
@dataclass
class CustomerDTO:
    """客户DTO类（主目标对象）"""
    customer_id: int = 0  # 注意字段名与源对象不同
    full_name: str = ""  # 注意这是一个合并字段
    contact_details: ContactInfoDTO = None  # 注意字段名与源对象不同
    status: bool = True  # 注意字段名与源对象不同

    def __post_init__(self):
        if self.contact_details is None:
            self.contact_details = ContactInfoDTO()


def nested_mapping_example():
    """嵌套对象映射示例"""
    print("\n=== 嵌套对象映射示例 ===")

    try:
        # 创建源对象（包含嵌套对象）
        customer_entity = CustomerEntity(
            id=1001,
            first_name="Jane",
            last_name="Smith",
            contact_info=ContactInfoEntity(
                email="jane.smith@example.com",
                phone="555-123-4567",
                address=AddressEntity(
                    street="123 Main St",
                    city="Boston",
                    state="MA",
                    postal_code="02108",
                    country="USA"
                )
            ),
            is_active=True
        )

        print(f"源对象: {customer_entity}")

        # 手动创建映射
        address_dto = AddressDTO(
            street_line=customer_entity.contact_info.address.street,
            city=customer_entity.contact_info.address.city,
            state=customer_entity.contact_info.address.state,
            zip_code=customer_entity.contact_info.address.postal_code,
            country=customer_entity.contact_info.address.country
        )

        contact_info_dto = ContactInfoDTO(
            email_address=customer_entity.contact_info.email,
            phone_number=customer_entity.contact_info.phone,
            address=address_dto
        )

        customer_dto = CustomerDTO(
            customer_id=customer_entity.id,
            full_name=f"{customer_entity.first_name} {customer_entity.last_name}",
            contact_details=contact_info_dto,
            status=customer_entity.is_active
        )

        # 打印结果
        print("\n映射结果:")
        print(f"客户ID: {customer_dto.customer_id}")
        print(f"全名: {customer_dto.full_name}")
        print(f"状态: {customer_dto.status}")
        print("联系详情:")
        print(f"  邮箱: {customer_dto.contact_details.email_address}")
        print(f"  电话: {customer_dto.contact_details.phone_number}")
        print("地址:")
        print(f"  街道: {customer_dto.contact_details.address.street_line}")
        print(f"  城市: {customer_dto.contact_details.address.city}")
        print(f"  州/省: {customer_dto.contact_details.address.state}")
        print(f"  邮编: {customer_dto.contact_details.address.zip_code}")
        print(f"  国家: {customer_dto.contact_details.address.country}")

        # 演示MapperBuilder的配置（仅作为示例，不执行）
        print("\nMapperBuilder的配置示例（不执行）:")
        print("""
        # 1. 首先创建最深层嵌套对象的映射器（地址映射器）
        address_mapper = MapperBuilder.for_types(AddressEntity, AddressDTO) \\
            .map("street", "street_line") \\
            .map("postal_code", "zip_code") \\
            .auto_map()  \\
            .build()
        
        # 2. 创建中间层嵌套对象的映射器（联系信息映射器）
        contact_info_mapper = MapperBuilder.for_types(ContactInfoEntity, ContactInfoDTO) \\
            .map("email", "email_address") \\
            .map("phone", "phone_number") \\
            .map_nested("address", "address", address_mapper)  \\
            .build()
        
        # 3. 创建主对象的映射器（客户映射器）
        customer_mapper = MapperBuilder.for_types(CustomerEntity, CustomerDTO) \\
            .map("id", "customer_id") \\
            .map_custom("full_name", lambda src: f"{src.first_name} {src.last_name}") \\
            .map_nested("contact_info", "contact_details", contact_info_mapper)  \\
            .map("is_active", "status") \\
            .build()
        """)

        # 演示嵌套映射中的异常处理
        print("\n嵌套映射中的异常处理示例:")
        print("如果传入无效的嵌套映射器，将导致异常: 'Source path, target path and mapper cannot be empty'")

    except Exception as e:
        print(f"映射过程中发生错误: {str(e)}")


if __name__ == "__main__":
    nested_mapping_example()
