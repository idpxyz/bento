# 映射器系统 (Mapper System)

映射器系统提供了一种灵活、类型安全的方式来处理领域对象与各种数据对象（持久化对象、数据传输对象、值对象）之间的转换。本文档介绍了系统的设计原则、核心功能、使用方法和最佳实践。

> **重要提示**: 为了简化使用，`MapperBuilderImpl` 类已通过别名 `MapperBuilder` 导出。在代码中，您可以直接使用 `MapperBuilder` 而不是 `MapperBuilderImpl`。这样可以使代码更加简洁和直观。

> **示例代码**: 查看 `example/basic_mapping.py` 文件获取完整的基本映射示例，包括手动映射和使用 `MapperBuilder` 的自动映射。

## 设计原则

1. **清晰的职责分离**：每个映射器负责特定类型之间的转换，遵循单一职责原则。
2. **组合优于继承**：使用组合模式构建映射策略，而不是复杂的继承层次。
3. **接口与实现分离**：通过接口定义映射器的行为，实现与接口分离。
4. **保护领域边界**：映射器作为防腐层，保护领域模型不受外部数据结构的影响。
5. **可测试性**：映射器设计便于单元测试，支持模拟和替换。
6. **类型安全**：使用泛型类型参数确保类型安全。
7. **灵活性**：支持多种映射策略，可以根据需要选择合适的策略。

## 核心功能

1. **自动映射**：基于属性名称自动映射同名属性
2. **显式映射**：明确指定源对象属性和目标对象属性之间的映射关系
3. **自定义映射**：使用自定义函数计算目标对象的属性值
4. **嵌套对象映射**：支持映射嵌套在源对象和目标对象中的复杂对象
5. **集合映射**：支持映射源对象和目标对象中的集合属性（列表、集合、字典）
6. **双向映射**：支持源对象和目标对象之间的双向转换
7. **类型转换**：支持不同类型之间的自动转换
8. **循环引用处理**：处理对象图中的循环引用
9. **批量映射**：支持高效的批量对象映射
10. **异常处理**：提供清晰的错误信息和异常处理机制

## 系统架构

映射器系统采用了模块化的架构设计，主要包括以下组件：

1. **核心接口层**：
   - 定义了清晰的接口层次结构，包括基础映射器接口、双向映射器接口、可配置映射器接口等
   - 使用泛型类型参数确保类型安全
   - 接口设计遵循单一职责原则

2. **映射策略层**：
   - 实现了多种映射策略，包括自动映射、显式映射、自定义映射等
   - 使用组合模式组合不同的映射策略
   - 策略实现支持嵌套对象和集合映射

3. **映射器实现层**：
   - 实现了通用映射器，支持双向映射、可配置映射和嵌套映射
   - 提供了映射器构建器，支持链式调用配置映射器
   - 实现了特定类型的映射器，包括PO映射器、DTO映射器和VO映射器

4. **注册表层**：
   - 实现了映射器注册表，用于管理和获取映射器实例
   - 提供了特定类型的注册表，包括PO注册表、DTO注册表和VO注册表
   - 注册表实现支持类型安全的映射器查找

## 使用指南

### 基本映射

基本映射是最简单的映射方式，适用于源对象和目标对象具有相似结构的情况。

```python
from idp.infrastructure.mapper import MapperBuilder

# 创建映射器
mapper = MapperBuilder.for_types(UserEntity, UserDTO) \
    .map("id", "id") \
    .map("username", "username") \
    .map("email", "email") \
    .map_custom("full_name", lambda user: f"{user.first_name} {user.last_name}") \
    .map("is_active", "active") \
    .map("age", "age") \
    .build()

# 执行映射
user_dto = mapper.map(user_entity)
```

### 嵌套对象映射

嵌套对象映射允许您映射嵌套在源对象和目标对象中的复杂对象。

```python
# 1. 首先创建最深层嵌套对象的映射器（地址映射器）
address_mapper = MapperBuilder.for_types(AddressEntity, AddressDTO) \
    .map("street", "street_line") \
    .map("postal_code", "zip_code") \
    .auto_map() \
    .build()

# 2. 创建中间层嵌套对象的映射器（联系信息映射器）
contact_info_mapper = MapperBuilder.for_types(ContactInfoEntity, ContactInfoDTO) \
    .map("email", "email_address") \
    .map("phone", "phone_number") \
    .map_nested("address", "address", address_mapper) \
    .build()

# 3. 创建主对象的映射器（客户映射器）
customer_mapper = MapperBuilder.for_types(CustomerEntity, CustomerDTO) \
    .map("id", "customer_id") \
    .map_custom("full_name", lambda src: f"{src.first_name} {src.last_name}") \
    .map_nested("contact_info", "contact_details", contact_info_mapper) \
    .map("is_active", "status") \
    .build()

# 执行映射
customer_dto = customer_mapper.map(customer_entity)
```

### 集合映射

集合映射允许您映射源对象和目标对象中的集合属性（列表、集合、字典）。

```python
# 创建产品映射器
product_mapper = MapperBuilder.for_types(ProductEntity, ProductDTO) \
    .map("id", "product_id") \
    .map("name", "product_name") \
    .map("price", "price") \
    .build()

# 创建订单映射器，使用产品映射器处理集合元素
order_mapper = MapperBuilder.for_types(OrderEntity, OrderDTO) \
    .map("id", "order_id") \
    .map_collection("items", "products", product_mapper) \
    .build()

# 执行映射
order_dto = order_mapper.map(order_entity)
```

### 自定义映射

自定义映射允许您使用自定义函数来计算目标对象的属性值。这适用于需要复杂转换逻辑的情况。

```python
# 自定义映射函数
def format_amount(payment: PaymentEntity) -> str:
    return f"${payment.amount:.2f} {payment.currency}"

def map_status_code(payment: PaymentEntity) -> int:
    status_codes = {
        PaymentStatus.PENDING: 100,
        PaymentStatus.PROCESSING: 200,
        PaymentStatus.COMPLETED: 300,
        PaymentStatus.FAILED: 400,
        PaymentStatus.REFUNDED: 500
    }
    return status_codes.get(payment.status, 0)

# 创建映射器
payment_mapper = MapperBuilder.for_types(PaymentEntity, PaymentDTO) \
    .map("id", "payment_id") \
    .map_custom("amount_formatted", format_amount) \
    .map_custom("status_code", map_status_code) \
    .build()

# 执行映射
payment_dto = payment_mapper.map(payment_entity)
```

### 双向映射

双向映射允许您在源对象和目标对象之间进行双向转换。

```python
# 自定义映射函数 - 正向映射
def get_full_name(person: PersonEntity) -> str:
    return f"{person.first_name} {person.last_name}"

# 自定义映射函数 - 反向映射
def extract_first_name(dto: PersonDTO) -> str:
    parts = dto.full_name.split()
    return parts[0] if parts else ""

def extract_last_name(dto: PersonDTO) -> str:
    parts = dto.full_name.split()
    return " ".join(parts[1:]) if len(parts) > 1 else ""

# 创建正向映射器
forward_mapper = MapperBuilder.for_types(PersonEntity, PersonDTO) \
    .map("id", "person_id") \
    .map_custom("full_name", get_full_name) \
    .map("email", "email") \
    .build()

# 创建反向映射器
reverse_mapper = MapperBuilder.for_types(PersonDTO, PersonEntity) \
    .map("person_id", "id") \
    .map_custom("first_name", extract_first_name) \
    .map_custom("last_name", extract_last_name) \
    .map("email", "email") \
    .build()

# 执行正向映射
person_dto = forward_mapper.map(person_entity)

# 执行反向映射
person_entity = reverse_mapper.map(person_dto)
```

### 领域对象与值对象映射

领域对象与值对象映射是一种特殊的映射场景，需要特别注意值对象的不可变性和领域规则。

```python
# 创建值对象映射器
email_mapper = MapperBuilder.for_types(EmailAddress, EmailAddressDTO) \
    .map_custom("email", lambda email_vo: email_vo.value) \
    .build()

# 创建客户领域实体映射器
customer_mapper = MapperBuilder.for_types(Customer, CustomerDTO) \
    .map_custom("id", lambda c: str(c.id)) \
    .map_custom("email", lambda c: c.email.value) \
    .map_nested("phone", "phone", phone_mapper) \
    .map_nested("address", "address", address_mapper) \
    .build()

# 执行映射
customer_dto = customer_mapper.map(customer)

# 注意：在领域驱动设计中，反向映射（DTO到领域实体）通常需要特殊处理
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
    }
)
```

## 最佳实践

### 1. 使用默认值避免类型转换错误

为了避免类型转换错误，确保目标类中的所有字段都有适当的默认值。这对于可选字段和集合字段尤为重要。

```python
@dataclass
class UserDTO:
    id: str = ""                  # 使用空字符串作为默认值
    username: str = ""            # 使用空字符串作为默认值
    email: str = ""               # 使用空字符串作为默认值
    full_name: str = ""           # 使用空字符串作为默认值
    active: bool = False          # 使用布尔值作为默认值
    age: Optional[int] = None     # 使用None作为默认值
    tags: List[str] = None        # 集合字段需要在__post_init__中初始化
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []        # 初始化集合字段
```

### 2. 处理嵌套对象

对于嵌套对象，确保目标对象中的嵌套对象已经初始化，或者在映射前手动初始化它们。

```python
# 确保嵌套对象已初始化
target = CustomerDTO(
    customer_id="",
    name="",
    address=AddressDTO(street="", city="", postal_code="")
)

# 执行映射
customer_mapper.map_to_target(source, target)
```

### 3. 手动处理集合映射

对于集合映射，有时候手动处理集合元素的映射可能更可靠。

```python
# 手动处理集合映射
target = OrderDTO(order_id="", items=[])
order_mapper.map_to_target(source, target)

# 手动映射集合元素
for product in source.products:
    product_dto = ProductDTO()
    product_mapper.map_to_target(product, product_dto)
    target.items.append(product_dto)
```

### 4. 使用映射上下文处理循环引用

对于包含循环引用的对象图，使用映射上下文来避免无限递归。

```python
# 创建映射上下文
context = MappingContext()

# 使用上下文执行映射
target = mapper.map_with_context(source, context)
```

### 5. 使用自定义映射函数处理类型转换

对于需要特殊类型转换的字段，使用自定义映射函数。

```python
# 日期转换
mapper = MapperBuilder.for_types(UserEntity, UserDTO) \
    .map_custom("created_date", lambda user: user.created_at.isoformat() if user.created_at else "") \
    .build()
```

### 6. 处理可能为空的值

确保自定义映射函数能够处理空值。

```python
def format_date(dt: Optional[datetime]) -> str:
    return dt.isoformat() if dt else ""
```

### 7. 使用map_to_target而不是map

在某些情况下，使用`map_to_target`方法将源对象映射到已存在的目标对象可能比使用`map`方法创建新的目标对象更可靠，特别是当目标对象有复杂的初始化逻辑时。

```python
# 创建目标对象
target = UserDTO()

# 执行映射
mapper.map_to_target(source, target)

# 验证映射结果时，确保使用正确的变量名
assert target.id == source.id  # 使用target变量名，而不是其他名称
```

使用`map_to_target`的主要优势：
- 可以预先初始化目标对象的所有必要字段
- 避免类型转换错误，因为字段已经有了正确的类型和默认值
- 对于嵌套对象和集合，可以确保它们已经被正确初始化
- 提供更好的类型安全性，因为目标对象的类型是明确的

### 8. 分离映射逻辑

将复杂的映射逻辑封装在单独的函数中，而不是直接在lambda表达式中实现。

```python
# 不推荐
mapper.map_custom("full_name", lambda user: f"{user.first_name} {user.last_name}")

# 推荐
def get_full_name(user: UserEntity) -> str:
    return f"{user.first_name} {user.last_name}"

mapper.map_custom("full_name", get_full_name)
```

### 9. 使用工厂方法创建领域实体

在领域驱动设计中，使用工厂方法创建领域实体，而不是直接映射。

```python
# 不推荐
customer = customer_mapper.map_to_source(customer_dto)

# 推荐
customer = Customer.create(
    email=customer_dto.email,
    phone=customer_dto.phone,
    address=customer_dto.address
)
```

### 10. 测试映射器

为映射器编写单元测试，确保映射逻辑正确。

```python
def test_user_mapper():
    # 创建源对象
    user_entity = UserEntity(
        id="123",
        username="johndoe",
        email="john.doe@example.com",
        first_name="John",
        last_name="Doe",
        is_active=True,
        age=30
    )
    
    # 创建映射器
    mapper = MapperBuilder.for_types(UserEntity, UserDTO) \
        .map("id", "id") \
        .map("username", "username") \
        .map("email", "email") \
        .map_custom("full_name", lambda user: f"{user.first_name} {user.last_name}") \
        .map("is_active", "active") \
        .map("age", "age") \
        .build()
    
    # 执行映射
    user_dto = mapper.map(user_entity)
    
    # 验证映射结果
    assert user_dto.id == user_entity.id
    assert user_dto.username == user_entity.username
    assert user_dto.email == user_entity.email
    assert user_dto.full_name == f"{user_entity.first_name} {user_entity.last_name}"
    assert user_dto.active == user_entity.is_active
    assert user_dto.age == user_entity.age
```

## 常见问题与解决方案

### 类型转换错误

如果在映射过程中遇到类型转换错误，可能是因为源对象和目标对象的属性类型不兼容。确保源对象和目标对象的属性类型兼容，或者使用自定义映射函数进行类型转换。

```python
# 使用自定义映射函数进行类型转换
mapper = MapperBuilder.for_types(SourceType, TargetType) \
    .map_custom("target_field", lambda source: str(source.source_field)) \
    .build()
```

### 循环引用

如果在映射过程中遇到循环引用，可能是因为对象图中存在循环引用。使用映射上下文处理循环引用。

```python
# 使用映射上下文处理循环引用
context = MappingContext()
target = mapper.map_with_context(source, context)
```

### 缺少必需字段

如果在映射过程中遇到缺少必需字段的错误，可能是因为目标对象的必需字段没有被映射。确保所有必需字段都被映射。

```python
# 确保所有必需字段都被映射
mapper = MapperBuilder.for_types(SourceType, TargetType) \
    .map("source_field1", "target_field1") \
    .map("source_field2", "target_field2") \
    .map_custom("target_field3", lambda source: default_value) \
    .build()
```

### 集合映射失败

如果集合映射失败，可能是因为目标对象的集合字段没有被初始化。确保目标对象的集合字段已经初始化，或者在映射前手动初始化它们。

```python
# 确保集合字段已初始化
@dataclass
class OrderDTO:
    order_id: str = ""
    items: List[ProductDTO] = None
    
    def __post_init__(self):
        if self.items is None:
            self.items = []
```

### 嵌套对象映射失败

如果嵌套对象映射失败，可能是因为目标对象的嵌套对象字段没有被初始化。确保目标对象的嵌套对象字段已经初始化，或者在映射前手动初始化它们。

```python
# 确保嵌套对象字段已初始化
@dataclass
class CustomerDTO:
    customer_id: str = ""
    name: str = ""
    address: Optional[AddressDTO] = None
    
    def __post_init__(self):
        if self.address is None:
            self.address = AddressDTO()
```

### 变量命名一致性

在映射过程中，保持变量命名的一致性非常重要，特别是在验证映射结果时。确保在断言或其他验证逻辑中使用正确的变量名。

```python
# 创建目标对象
target_dto = UserDTO()

# 执行映射
mapper.map_to_target(source, target_dto)

# 验证映射结果 - 使用正确的变量名
assert target_dto.id == source.id  # 正确
assert mapped_dto.id == source.id  # 错误：使用了未定义的变量名
```

## 总结

映射器系统提供了一种灵活、类型安全的方式来处理领域对象与各种数据对象之间的转换。通过使用适当的映射策略和遵循最佳实践，可以简化数据转换逻辑，提高代码质量和可维护性。

系统支持多种映射场景，包括基本映射、嵌套对象映射、集合映射、自定义映射、双向映射和领域对象与值对象映射。同时，系统提供了清晰的错误信息和异常处理机制，帮助开发人员快速定位和解决问题。

在领域驱动设计中，映射器作为防腐层，保护领域模型不受外部数据结构的影响，是实现清晰架构的重要组件。