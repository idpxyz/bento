# MapperRegistry 的作用与用途

`MapperRegistry` 是映射器系统中的一个重要组件，它主要负责管理和获取映射器实例。下面详细解释它的作用和使用场景：

## 主要功能

1. **集中管理映射器实例**：
   - 提供一个中央存储库，存储和管理所有已创建的映射器实例
   - 避免重复创建相同类型之间的映射器，节省内存和初始化时间

2. **类型安全的映射器查找**：
   - 根据源类型和目标类型查找对应的映射器
   - 确保类型安全，避免运行时类型错误

3. **支持依赖注入**：
   - 在应用程序中作为一个全局服务，可以被注入到需要使用映射器的组件中
   - 降低组件之间的耦合度

4. **简化映射器的使用**：
   - 使用者不需要关心映射器的创建和配置细节
   - 只需要通过注册表获取已配置好的映射器实例

## 专用注册表

框架提供了几种专用的注册表，针对不同类型的映射场景：

1. **DTOMapperRegistry**：
   - 管理领域对象与DTO之间的映射器
   - 支持领域对象到DTO和DTO到领域对象的双向映射

2. **POMapperRegistry**：
   - 管理领域对象与持久化对象之间的映射器
   - 支持领域对象到PO和PO到领域对象的双向映射

3. **VOMapperRegistry**：
   - 管理领域对象与值对象之间的映射器
   - 支持领域对象到VO和VO到领域对象的双向映射

## 使用场景

### 1. 应用启动时注册映射器

在应用程序启动时，您可以配置和注册所有需要的映射器：

```python
# 创建映射器
user_mapper = MapperBuilder.for_types(UserEntity, UserDTO) \
    .auto_map() \
    .build()

# 注册到DTO映射器注册表
dto_mapper_registry.register_domain_to_dto(UserEntity, UserDTO, user_mapper)
```

### 2. 在服务或仓储中使用注册表获取映射器

在服务或仓储实现中，您可以通过注册表获取映射器：

```python
class UserService:
    def __init__(self, user_repository):
        self.user_repository = user_repository
        
    def get_user_dto(self, user_id: int) -> UserDTO:
        # 获取领域对象
        user = self.user_repository.get_by_id(user_id)
        
        # 从注册表获取映射器
        mapper = dto_mapper_registry.get_domain_to_dto(UserEntity, UserDTO)
        
        # 使用映射器转换对象
        return mapper.map(user)
```

### 3. 自动注册映射器

在某些实现中，映射器会在创建时自动注册到对应的注册表：

```python
# DTOMapper的初始化方法中会自动注册
class UserDTOMapper(DTOMapper[UserEntity, UserDTO]):
    def __init__(self):
        super().__init__(UserEntity, UserDTO, auto_map=True)
        
        # 自定义映射配置
        self.configure_custom_mapping("full_name", lambda user: f"{user.first_name} {user.last_name}")
```

### 4. 在依赖注入容器中注册

在使用依赖注入框架的应用中，可以将注册表作为单例服务注册：

```python
# 使用某个DI容器的示例代码
container.register_singleton(DTOMapperRegistry, dto_mapper_registry)
container.register_singleton(POMapperRegistry, po_mapper_registry)
container.register_singleton(VOMapperRegistry, vo_mapper_registry)
```

## 与MapperBuilder的关系

`MapperBuilder` 和 `MapperRegistry` 是相互补充的组件：

- **MapperBuilder**：负责创建和配置映射器，提供流畅的API来定义映射规则
- **MapperRegistry**：负责存储和管理已创建的映射器，提供类型安全的查找机制

在典型的使用流程中：
1. 使用 `MapperBuilder` 创建和配置映射器
2. 将创建好的映射器注册到 `MapperRegistry`
3. 在应用程序的其他部分，通过 `MapperRegistry` 获取映射器

## 总结

`MapperRegistry` 是映射器系统中的一个重要组件，它提供了集中管理和获取映射器实例的机制。通过使用注册表，您可以避免重复创建映射器，简化映射器的使用，并支持依赖注入模式。

在实际应用中，您通常会同时使用 `MapperBuilder` 和 `MapperRegistry`：使用 `MapperBuilder` 创建映射器，然后将其注册到 `MapperRegistry`，最后在需要使用映射器的地方通过 `MapperRegistry` 获取映射器实例。
