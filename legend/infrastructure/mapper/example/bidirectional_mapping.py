"""双向映射示例。

本示例展示了如何使用映射器系统的双向映射功能，包括：
1. 配置双向映射器
2. 执行正向映射（源对象到目标对象）
3. 执行反向映射（目标对象到源对象）
4. 处理双向映射中的异常
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List

# 源对象类
@dataclass
class PersonEntity:
    """人员实体类（源对象）"""
    id: int = 0
    first_name: str = ""
    last_name: str = ""
    birth_date: date = field(default_factory=lambda: date.today())
    email: str = ""
    phone_number: str = ""
    address: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now())
    updated_at: Optional[datetime] = None
    is_active: bool = True
    tags: List[str] = field(default_factory=list)


# 目标对象类
@dataclass
class PersonDTO:
    """人员DTO类（目标对象）"""
    person_id: int = 0
    full_name: str = ""  # 合并字段
    age: int = 0  # 计算字段
    contact_email: str = ""
    contact_phone: str = ""
    location: str = ""
    registration_date: str = ""  # 格式化日期
    last_modified: Optional[str] = None  # 格式化日期
    active: bool = True
    labels: List[str] = field(default_factory=list)


def bidirectional_mapping_example():
    """双向映射示例"""
    print("\n=== 双向映射示例 ===")
    
    try:
        # 创建源对象
        today = date.today()
        birth_date = date(1990, 5, 15)
        
        person_entity = PersonEntity(
            id=1001,
            first_name="Alice",
            last_name="Johnson",
            birth_date=birth_date,
            email="alice.johnson@example.com",
            phone_number="555-987-6543",
            address="456 Park Avenue, New York, NY 10022",
            created_at=datetime(2022, 3, 10, 9, 30, 0),
            updated_at=datetime(2023, 1, 15, 14, 45, 0),
            is_active=True,
            tags=["customer", "premium", "verified"]
        )
        
        print(f"源对象: {person_entity}")
        
        # 自定义映射函数 - 正向映射
        
        # 1. 计算全名
        def get_full_name(person: PersonEntity) -> str:
            return f"{person.first_name} {person.last_name}"
        
        # 2. 计算年龄
        def calculate_age(person: PersonEntity) -> int:
            today = date.today()
            age = today.year - person.birth_date.year
            if (today.month, today.day) < (person.birth_date.month, person.birth_date.day):
                age -= 1
            return age
        
        # 3. 格式化日期
        def format_date(dt: Optional[datetime]) -> str:
            return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""
        
        # 自定义映射函数 - 反向映射
        
        # 1. 从全名提取姓和名
        def extract_first_name(dto: PersonDTO) -> str:
            parts = dto.full_name.split()
            return parts[0] if parts else ""
        
        def extract_last_name(dto: PersonDTO) -> str:
            parts = dto.full_name.split()
            return " ".join(parts[1:]) if len(parts) > 1 else ""
        
        # 2. 从年龄和当前日期估算出生日期
        def estimate_birth_date(dto: PersonDTO) -> date:
            today = date.today()
            estimated_year = today.year - dto.age
            # 假设生日是当年的1月1日（这是一个简化的估算）
            return date(estimated_year, 1, 1)
        
        # 3. 解析日期字符串
        def parse_date(date_str: Optional[str]) -> Optional[datetime]:
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None
        
        # 手动执行正向映射（源对象 -> 目标对象）
        try:
            # 创建目标对象
            person_dto = PersonDTO()
            
            # 手动应用映射函数
            person_dto.person_id = person_entity.id
            person_dto.full_name = get_full_name(person_entity)
            person_dto.age = calculate_age(person_entity)
            person_dto.contact_email = person_entity.email
            person_dto.contact_phone = person_entity.phone_number
            person_dto.location = person_entity.address
            person_dto.registration_date = format_date(person_entity.created_at)
            person_dto.last_modified = format_date(person_entity.updated_at)
            person_dto.active = person_entity.is_active
            person_dto.labels = person_entity.tags.copy()
            
            # 打印正向映射结果
            print("\n正向映射结果 (PersonEntity -> PersonDTO):")
            print(f"人员ID: {person_dto.person_id}")
            print(f"全名: {person_dto.full_name}")
            print(f"年龄: {person_dto.age}")
            print(f"联系邮箱: {person_dto.contact_email}")
            print(f"联系电话: {person_dto.contact_phone}")
            print(f"位置: {person_dto.location}")
            print(f"注册日期: {person_dto.registration_date}")
            print(f"最后修改: {person_dto.last_modified}")
            print(f"活跃状态: {person_dto.active}")
            print(f"标签: {person_dto.labels}")
            
            # 手动执行反向映射（目标对象 -> 源对象）
            reverse_person_entity = PersonEntity()
            
            # 手动应用反向映射函数
            reverse_person_entity.id = person_dto.person_id
            reverse_person_entity.first_name = extract_first_name(person_dto)
            reverse_person_entity.last_name = extract_last_name(person_dto)
            reverse_person_entity.birth_date = estimate_birth_date(person_dto)
            reverse_person_entity.email = person_dto.contact_email
            reverse_person_entity.phone_number = person_dto.contact_phone
            reverse_person_entity.address = person_dto.location
            reverse_person_entity.created_at = parse_date(person_dto.registration_date)
            reverse_person_entity.updated_at = parse_date(person_dto.last_modified)
            reverse_person_entity.is_active = person_dto.active
            reverse_person_entity.tags = person_dto.labels.copy()
            
            # 打印反向映射结果
            print("\n反向映射结果 (PersonDTO -> PersonEntity):")
            print(f"ID: {reverse_person_entity.id}")
            print(f"名: {reverse_person_entity.first_name}")
            print(f"姓: {reverse_person_entity.last_name}")
            print(f"出生日期: {reverse_person_entity.birth_date}")
            print(f"邮箱: {reverse_person_entity.email}")
            print(f"电话: {reverse_person_entity.phone_number}")
            print(f"地址: {reverse_person_entity.address}")
            print(f"创建时间: {reverse_person_entity.created_at}")
            print(f"更新时间: {reverse_person_entity.updated_at}")
            print(f"活跃状态: {reverse_person_entity.is_active}")
            print(f"标签: {reverse_person_entity.tags}")
            
            # 比较原始源对象和反向映射后的源对象
            print("\n原始源对象与反向映射后的源对象比较:")
            print(f"ID 匹配: {person_entity.id == reverse_person_entity.id}")
            print(f"名 匹配: {person_entity.first_name == reverse_person_entity.first_name}")
            print(f"姓 匹配: {person_entity.last_name == reverse_person_entity.last_name}")
            print(f"出生日期 匹配: {person_entity.birth_date == reverse_person_entity.birth_date}")
            print(f"邮箱 匹配: {person_entity.email == reverse_person_entity.email}")
            print(f"电话 匹配: {person_entity.phone_number == reverse_person_entity.phone_number}")
            print(f"地址 匹配: {person_entity.address == reverse_person_entity.address}")
            print(f"活跃状态 匹配: {person_entity.is_active == reverse_person_entity.is_active}")
            print(f"标签 匹配: {person_entity.tags == reverse_person_entity.tags}")
            
            # 注意：某些字段（如出生日期）在反向映射中是估算的，因此可能与原始值不匹配
            print("注意：出生日期在反向映射中是根据年龄估算的，因此与原始值不匹配")
            
            # 显示MapperBuilder配置示例（不执行）
            print("\nMapperBuilder的配置示例（不执行）:")
            print("""
        # 正向映射器（源对象 -> 目标对象）
        forward_mapper = MapperBuilder.for_types(PersonEntity, PersonDTO) \\
            .map("id", "person_id") \\
            .map_custom("full_name", get_full_name) \\
            .map_custom("age", calculate_age) \\
            .map("email", "contact_email") \\
            .map("phone_number", "contact_phone") \\
            .map("address", "location") \\
            .map_custom("registration_date", lambda p: format_date(p.created_at)) \\
            .map_custom("last_modified", lambda p: format_date(p.updated_at)) \\
            .map("is_active", "active") \\
            .map("tags", "labels") \\
            .build()
        
        # 反向映射器（目标对象 -> 源对象）
        reverse_mapper = MapperBuilder.for_types(PersonDTO, PersonEntity) \\
            .map("person_id", "id") \\
            .map_custom("first_name", extract_first_name) \\
            .map_custom("last_name", extract_last_name) \\
            .map_custom("birth_date", estimate_birth_date) \\
            .map("contact_email", "email") \\
            .map("contact_phone", "phone_number") \\
            .map("location", "address") \\
            .map_custom("created_at", lambda dto: parse_date(dto.registration_date)) \\
            .map_custom("updated_at", lambda dto: parse_date(dto.last_modified)) \\
            .map("active", "is_active") \\
            .map("labels", "tags") \\
            .build()
            """)
            
        except Exception as e:
            print(f"手动映射过程中发生错误: {str(e)}")
        
        # 演示双向映射中的异常处理
        print("\n演示双向映射中的异常处理:")
        print("如果缺少必要的映射函数，将导致异常:")
        print("""
        # 故意创建错误的反向映射配置
        invalid_mapper = (MapperBuilder()
            .for_types(PersonDTO, PersonEntity)
            .map("person_id", "id")
            # 没有为first_name和last_name配置映射
            .map_custom("birth_date", estimate_birth_date)
            .map("contact_email", "email")
            .map("contact_phone", "phone_number")
            .map("location", "address")
            .map_custom("created_at", lambda dto: parse_date(dto.registration_date))
            .map_custom("updated_at", lambda dto: parse_date(dto.last_modified))
            .map("active", "is_active")
            .map("labels", "tags")
            .build()
        )
        """)
            
    except Exception as e:
        print(f"映射过程中发生错误: {str(e)}")


if __name__ == "__main__":
    bidirectional_mapping_example() 