是的，在未来的使用中，您只需要使用 `MapperBuilder` 来构建映射器就可以了。这是框架设计的核心意图，通过 `MapperBuilder` 提供了一个简洁、流畅的 API 来配置和创建各种映射器。

## MapperBuilder 使用说明

`MapperBuilder` 是一个便捷的构建器，它隐藏了底层复杂的映射策略和配置细节，让您可以专注于定义映射关系。从代码中可以看到，`MapperBuilderImpl` 类已通过别名 `MapperBuilder` 导出，这样您可以直接使用 `MapperBuilder` 而不是 `MapperBuilderImpl`。

### 基本使用模式

```python
from idp.infrastructure.mapper import MapperBuilder

# 创建映射器
mapper = MapperBuilder.for_types(SourceType, TargetType) \
    .auto_map()  # 自动映射同名属性
    .map("source_field", "target_field")  # 显式映射不同名称的字段
    .map_custom("target_computed_field", lambda source: compute_value(source))  # 自定义映射函数
    .build()  # 构建映射器实例

# 使用映射器
target = mapper.map(source)
```

### 主要功能

通过 `MapperBuilder`，您可以使用以下核心功能：

1. **自动映射**：`.auto_map()` - 自动映射同名属性
2. **显式映射**：`.map(source_path, target_path)` - 明确指定源路径到目标路径的映射
3. **自定义映射**：`.map_custom(target_path, mapping_func)` - 使用自定义函数计算目标值
4. **嵌套对象映射**：`.map_nested(source_path, target_path, mapper)` - 映射嵌套对象
5. **集合映射**：`.map_collection(source_path, target_path, mapper)` - 映射集合属性

### 实际使用示例

#### 基本映射

```python
# 基本映射示例
user_mapper = MapperBuilder.for_types(UserEntity, UserDTO) \
    .auto_map()  # 自动映射同名字段
    .map("is_active", "status")  # 显式映射不同名称的字段
    .map_custom("full_name", lambda user: f"{user.first_name} {user.last_name}")  # 自定义映射
    .build()

user_dto = user_mapper.map(user_entity)
```

#### 嵌套对象映射

```python
# 先创建嵌套对象的映射器
address_mapper = MapperBuilder.for_types(AddressEntity, AddressDTO) \
    .auto_map()
    .build()

# 使用嵌套映射器
customer_mapper = MapperBuilder.for_types(CustomerEntity, CustomerDTO) \
    .auto_map()
    .map_nested("address", "address_info", address_mapper)  # 嵌套对象映射
    .build()

customer_dto = customer_mapper.map(customer_entity)
```

#### 集合映射

```python
# 先创建集合元素的映射器
order_item_mapper = MapperBuilder.for_types(OrderItemEntity, OrderItemDTO) \
    .auto_map()
    .build()

# 使用集合映射
order_mapper = MapperBuilder.for_types(OrderEntity, OrderDTO) \
    .auto_map()
    .map_collection("items", "order_items", order_item_mapper)  # 集合映射
    .build()

order_dto = order_mapper.map(order_entity)
```

### 总结

是的，在大多数情况下，您只需要使用 `MapperBuilder` 来构建和配置映射器，它提供了一个简洁而强大的 API，隐藏了底层的复杂性。这种设计使得代码更加可读、可维护，同时保持了映射配置的灵活性。

如果您有特殊需求，框架也允许您直接使用底层的映射策略或创建自定义映射器，但对于大多数应用场景，`MapperBuilder` 已经足够满足需求。


是的，您理解得完全正确。在实际应用中，您主要只需要使用以下三个核心组件：

## 核心组件使用总结

### 1. MapperBuilder

用于创建和配置映射器的流畅API。

```python
# 使用MapperBuilder创建映射器
mapper = MapperBuilder.for_types(SourceType, TargetType) \
    .auto_map() \
    .map("source_field", "target_field") \
    .map_custom("computed_field", lambda src: compute_value(src)) \
    .build()
```

### 2. Mapper

映射器接口及其实现，用于执行实际的对象映射操作。

```python
# 使用映射器进行对象转换
target_object = mapper.map(source_object)

# 批量映射
target_objects = mapper.map_list(source_objects)
```

### 3. MapperRegistry

管理和获取映射器实例的注册表。

```python
# 从注册表获取映射器
mapper = dto_mapper_registry.get_domain_to_dto(UserEntity, UserDTO)

# 使用获取的映射器
user_dto = mapper.map(user_entity)
```

## 典型使用流程

在实际应用中，典型的使用流程如下：

### 1. 应用启动时配置映射器

通常在应用程序启动时或配置阶段，使用`MapperBuilder`创建并配置所有需要的映射器，然后将它们注册到相应的注册表中：

```python
# 创建并配置用户映射器
user_mapper = MapperBuilder.for_types(UserEntity, UserDTO) \
    .auto_map() \
    .map("is_active", "status") \
    .build()

# 注册到DTO映射器注册表
dto_mapper_registry.register_domain_to_dto(UserEntity, UserDTO, user_mapper)

# 创建并配置订单映射器
order_mapper = MapperBuilder.for_types(OrderEntity, OrderDTO) \
    .auto_map() \
    .build()

# 注册到DTO映射器注册表
dto_mapper_registry.register_domain_to_dto(OrderEntity, OrderDTO, order_mapper)
```

### 2. 在应用程序中使用映射器

在应用程序的服务层、控制器或其他需要进行对象转换的地方，通过注册表获取映射器并使用它：

```python
class UserService:
    def get_user_dto(self, user_id: int) -> UserDTO:
        # 获取用户实体
        user_entity = self.user_repository.get_by_id(user_id)
        
        # 从注册表获取映射器
        mapper = dto_mapper_registry.get_domain_to_dto(UserEntity, UserDTO)
        
        # 使用映射器转换对象
        return mapper.map(user_entity)
    
    def create_user(self, user_dto: UserDTO) -> UserEntity:
        # 从注册表获取映射器
        mapper = dto_mapper_registry.get_dto_to_domain(UserDTO, UserEntity)
        
        # 转换DTO到实体
        user_entity = mapper.map(user_dto)
        
        # 保存实体
        return self.user_repository.save(user_entity)
```

## 简化使用方式

在某些情况下，您可能会发现直接使用专用的映射器类（如`DTOMapper`）更加方便：

```python
# 创建专用的DTO映射器
class UserDTOMapper(DTOMapper[UserEntity, UserDTO]):
    def __init__(self):
        super().__init__(UserEntity, UserDTO, auto_map=True)
        # 自定义映射配置
        self.configure_mapping("is_active", "status")

# 使用专用映射器
user_dto_mapper = UserDTOMapper()
user_dto = user_dto_mapper.to_dto(user_entity)
```

这种方式会自动将映射器注册到相应的注册表中，简化了注册步骤。

## 总结

是的，在实际应用中，您主要只需要关注这三个核心组件：

1. **MapperBuilder** - 用于创建和配置映射器
2. **Mapper** - 用于执行实际的对象映射
3. **MapperRegistry** - 用于管理和获取映射器实例

其他的组件（如映射策略、类型转换器等）都是内部实现细节，通常不需要直接使用。这种设计使得API简洁易用，同时保持了系统的灵活性和可扩展性。

框架的设计目标就是让开发者能够专注于定义映射关系，而不必关心底层的实现细节，这三个核心组件已经足够满足大多数应用场景的需求。
