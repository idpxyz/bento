# 字段安全校验功能指南

## 概述

字段安全校验功能为查询构建器提供了强大的字段访问控制能力，确保只有授权的字段和关系可以被访问，防止敏感数据泄露和未授权的查询操作。

## 核心组件

### 1. FieldSecurityConfig

字段安全配置类，定义了字段访问的安全策略：

```python
@dataclass
class FieldSecurityConfig:
    allowed_fields: Optional[Set[str]] = None        # 白名单字段
    forbidden_fields: Optional[Set[str]] = None      # 黑名单字段
    allowed_relations: Optional[Set[str]] = None     # 白名单关系
    forbidden_relations: Optional[Set[str]] = None   # 黑名单关系
    field_permissions: Optional[Dict[str, str]] = None    # 字段权限映射
    relation_permissions: Optional[Dict[str, str]] = None # 关系权限映射
```

### 2. FieldResolver

增强的字段解析器，集成了安全验证功能：

```python
class FieldResolver:
    def __init__(self, entity_type: Type[T], security_config: Optional[FieldSecurityConfig] = None)
    
    def validate_field_access(self, field_path: str, operation: str = "read") -> None
    def validate_fields(self, fields: List[str], operation: str = "read") -> List[str]
    def resolve(self, field_path: str, return_key: bool = False, operation: str = "read") -> Union[str, Any]
```

### 3. FieldSecurityManager

全局安全管理器，用于管理不同场景下的安全配置：

```python
class FieldSecurityManager:
    def register_config(self, name: str, config: FieldSecurityConfig) -> None
    def get_config(self, name: str) -> Optional[FieldSecurityConfig]
    def create_user_config(self, user_permissions: Dict[str, str]) -> FieldSecurityConfig
```

## 权限级别

系统定义了5个权限级别（从低到高）：

1. **read** (1) - 读取权限
2. **filter** (2) - 过滤权限
3. **sort** (3) - 排序权限
4. **write** (4) - 写入权限
5. **admin** (5) - 管理员权限

高级权限自动包含低级权限。

## 使用场景

### 1. 基本白名单/黑名单控制

```python
# 创建安全配置
security_config = FieldSecurityConfig(
    allowed_fields={"id", "username", "email", "department"},
    forbidden_fields={"password_hash", "salary"}
)

# 创建字段解析器
resolver = FieldResolver(UserPO, security_config)

# 验证字段访问
try:
    field = resolver.resolve("username", operation="read")
    print("✓ 允许访问")
except FieldSecurityError as e:
    print(f"✗ 访问被拒绝: {e}")
```

### 2. 基于权限的访问控制

```python
# 创建权限配置
security_config = FieldSecurityConfig(
    field_permissions={
        "id": "read",
        "username": "read",
        "email": "read",
        "phone": "filter",      # 需要 filter 权限才能用于过滤
        "salary": "admin",      # 需要 admin 权限
        "password_hash": "forbidden"
    }
)

resolver = FieldResolver(UserPO, security_config)

# 测试不同操作权限
resolver.validate_field_access("phone", "filter")  # ✓ 通过
resolver.validate_field_access("phone", "read")    # ✗ 拒绝
resolver.validate_field_access("salary", "admin")  # ✓ 通过
resolver.validate_field_access("salary", "read")   # ✗ 拒绝
```

### 3. 用户角色权限管理

```python
# 定义用户权限
user_permissions = {
    "id": "read",
    "username": "read",
    "email": "read",
    "phone": "filter",
    "salary": "forbidden",
    "password_hash": "forbidden"
}

# 创建用户配置
config = field_security_manager.create_user_config(user_permissions)
resolver = FieldResolver(UserPO, config)
```

### 4. 查询构建器集成

```python
# 创建安全配置
security_config = FieldSecurityConfig(
    allowed_fields={"id", "username", "email", "department"},
    forbidden_fields={"password_hash", "salary"}
)

# 创建字段解析器
field_resolver = FieldResolver(UserPO, security_config)

# 创建查询构建器
query_builder = QueryBuilder(UserPO, field_resolver)

# 应用过滤条件（自动进行安全验证）
filters = [
    Filter(field="username", operator=FilterOperator.LIKE, value="john%"),
    Filter(field="email", operator=FilterOperator.EQUALS, value="john@example.com"),
    # 这个会被安全验证拒绝
    Filter(field="password_hash", operator=FilterOperator.EQUALS, value="hash123")
]

query_builder.apply_filters(filters)
```

### 5. 字段列表批量验证

```python
# 验证字段列表
test_fields = ["id", "username", "password_hash", "email", "salary"]

try:
    valid_fields = resolver.validate_fields(test_fields, operation="read")
    print(f"通过验证的字段: {valid_fields}")
except FieldSecurityError as e:
    print(f"字段验证失败: {e}")
```

## 最佳实践

### 1. 配置管理

```python
# 注册预定义配置
public_config = FieldSecurityConfig(
    allowed_fields={"id", "username", "department"},
    forbidden_fields={"password_hash", "salary", "phone", "email"}
)

field_security_manager.register_config("public", public_config)

# 在需要时获取配置
config = field_security_manager.get_config("public")
resolver = FieldResolver(UserPO, config)
```

### 2. 错误处理

```python
try:
    field = resolver.resolve("sensitive_field", operation="read")
except FieldSecurityError as e:
    # 记录安全事件
    logger.warning(f"Field access denied: {e}")
    # 返回默认值或抛出业务异常
    raise BusinessError("Access denied")
```

### 3. 动态权限配置

```python
def create_dynamic_config(user_context: UserContext) -> FieldSecurityConfig:
    """根据用户上下文创建动态安全配置"""
    if user_context.is_admin:
        return FieldSecurityConfig()  # 管理员无限制
    elif user_context.is_manager:
        return FieldSecurityConfig(
            allowed_fields={"id", "username", "email", "department"},
            forbidden_fields={"password_hash", "salary"}
        )
    else:
        return FieldSecurityConfig(
            allowed_fields={"id", "username", "department"},
            forbidden_fields={"password_hash", "salary", "email", "phone"}
        )
```

### 4. 关系字段安全

```python
# 配置关系权限
security_config = FieldSecurityConfig(
    allowed_relations={"manager", "department"},
    forbidden_relations={"secret_data", "audit_logs"},
    relation_permissions={
        "manager": "read",
        "secret_data": "admin"
    }
)

# 验证关系访问
resolver.validate_field_access("manager.name", operation="read")  # ✓ 通过
resolver.validate_field_access("secret_data.content", operation="read")  # ✗ 拒绝
```

## 安全特性

### 1. 自动验证

- 所有字段解析操作都会自动进行安全验证
- 查询构建器在应用过滤、排序、字段选择时自动验证
- 支持批量字段验证

### 2. 权限继承

- 高级权限自动包含低级权限
- 关系权限影响嵌套字段访问
- 配置冲突检测和验证

### 3. 错误处理

- 详细的错误信息
- 优雅的错误处理机制
- 支持日志记录和监控

### 4. 性能优化

- 配置验证在初始化时完成
- 字段验证使用高效的集合操作
- 支持配置缓存和复用

## 集成指南

### 1. 与仓储层集成

```python
class SecureRepository(BaseRepository[UserPO]):
    def __init__(self, session: AsyncSession, user_context: UserContext):
        super().__init__(session)
        
        # 根据用户上下文创建安全配置
        security_config = create_dynamic_config(user_context)
        self.field_resolver = FieldResolver(UserPO, security_config)
        self.query_builder = QueryBuilder(UserPO, self.field_resolver)
    
    async def find_by_spec(self, spec: Specification[UserPO]) -> List[UserPO]:
        # 使用安全的查询构建器
        query = self.query_builder.reset()
        # ... 应用规范
        return await self.session.execute(query.build())
```

### 2. 与API层集成

```python
@router.get("/users")
async def get_users(
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends()
):
    # 创建用户上下文
    user_context = UserContext(
        user_id=current_user.id,
        role=current_user.role,
        permissions=current_user.permissions
    )
    
    # 使用安全的查询服务
    return await user_service.query_with_security(user_context)
```

## 监控和日志

### 1. 安全事件日志

```python
import logging

logger = logging.getLogger("field_security")

try:
    field = resolver.resolve("sensitive_field", operation="read")
except FieldSecurityError as e:
    logger.warning(f"Field access denied: {e}", extra={
        "user_id": user_context.user_id,
        "field": field_path,
        "operation": operation
    })
```

### 2. 性能监控

```python
import time

start_time = time.time()
try:
    field = resolver.resolve(field_path, operation=operation)
    duration = time.time() - start_time
    if duration > 0.1:  # 超过100ms记录慢查询
        logger.warning(f"Slow field resolution: {duration}s")
except FieldSecurityError as e:
    # 记录安全事件
    pass
```

## 总结

字段安全校验功能提供了全面的字段访问控制能力，通过白名单、黑名单、权限级别等多种机制确保数据安全。它与现有的查询构建器无缝集成，支持动态配置和批量验证，是构建安全可靠的数据访问层的重要组件。 