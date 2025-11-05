# SQLAlchemy 拦截器系统

SQLAlchemy 拦截器系统是一个用于扩展 SQLAlchemy ORM 功能的框架，它允许在数据库操作的不同阶段插入自定义逻辑，而无需修改核心业务代码。

## 主要特性

- **可扩展的拦截器架构**：基于责任链模式，支持多个拦截器按优先级顺序执行
- **标准拦截器实现**：内置乐观锁、审计日志、软删除等常用功能
- **领域事件支持**：自动发布实体变更事件，支持自定义事件处理
- **聚合边界验证**：确保领域聚合的完整性和一致性
- **元数据驱动**：通过元数据配置实体行为，减少硬编码依赖
- **异步支持**：完全支持 SQLAlchemy 2.0 异步操作
- **批量操作支持**：优化批量实体处理性能
- **高性能缓存**：智能缓存系统，自动管理实体和查询结果缓存

## 架构概览

拦截器系统由以下主要组件组成：

1. **核心类型**：定义基础数据结构和接口
   - `InterceptorContext`：拦截器执行上下文
   - `OperationType`：操作类型枚举（CREATE、READ、UPDATE、DELETE等）
   - `Interceptor`：拦截器基类
   - `InterceptorChain`：拦截器链，协调多个拦截器的执行

2. **元数据管理**：
   - `EntityMetadata`：实体元数据，定义实体特性和行为
   - `EntityMetadataRegistry`：元数据注册表，管理所有实体的元数据
   - `entity_metadata`：装饰器，用于配置实体元数据

3. **标准拦截器**：
   - `OptimisticLockInterceptor`：乐观锁，防止并发更新冲突
   - `AuditInterceptor`：审计日志，记录实体变更历史
   - `SoftDeleteInterceptor`：软删除，逻辑删除而非物理删除
   - `LoggingInterceptor`：日志记录，跟踪数据库操作
   - `TransactionInterceptor`：事务管理，确保操作的原子性
   - `CacheInterceptor`：缓存管理，自动处理实体和查询结果缓存

4. **领域事件**：
   - `DomainEvent`：领域事件基类
   - `EventPublisher`：事件发布接口
   - `DomainEventInterceptor`：自动发布实体变更事件

5. **聚合边界验证**：
   - `AggregateValidator`：聚合验证接口
   - `AggregateRegistry`：聚合注册表
   - `AggregateBoundaryInterceptor`：验证聚合操作的合法性

6. **缓存系统**：
   - `CacheManager`：缓存管理器，提供缓存操作接口
   - `CacheConfig`：缓存配置，定义缓存行为
   - `CacheInterceptor`：缓存拦截器，自动处理实体缓存
   - `CacheBackend`：缓存后端接口，支持多种缓存实现

## 使用示例

### 基本配置

```python
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from idp.infrastructure.persistence.sqlalchemy.interceptor.core.metadata import entity_metadata

Base = declarative_base()

@entity_metadata(
    enable_optimistic_lock=True,
    enable_audit=True,
    enable_soft_delete=True,
    version_field="version"
)
class UserPO(Base):
    """用户持久化对象"""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False)
    
    # 审计字段
    created_at = Column(DateTime, nullable=False)
    created_by = Column(String(50), nullable=False)
    updated_at = Column(DateTime, nullable=False)
    updated_by = Column(String(50), nullable=False)
    
    # 软删除字段
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String(50), nullable=True)
    
    # 乐观锁字段
    version = Column(Integer, default=0, nullable=False)
```

### 创建仓储

```python
from sqlalchemy.ext.asyncio import AsyncSession
from idp.infrastructure.persistence.sqlalchemy.interceptor import InterceptorFactory, OperationType, InterceptorContext

class UserRepository:
    """用户仓储"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.entity_type = UserPO
        
        # 创建拦截器链
        self.interceptor_chain = InterceptorFactory.create_chain(
            entity_type=UserPO,
            actor="system",
            enable_optimistic_lock=True,
            enable_audit=True,
            enable_soft_delete=True,
            enable_logging=True,
            enable_domain_events=True
        )
    
    async def create(self, user: UserPO) -> UserPO:
        """创建用户"""
        context = InterceptorContext(
            session=self.session,
            entity_type=self.entity_type,
            operation=OperationType.CREATE,
            entity=user,
            actor="system"
        )
        
        return await self.interceptor_chain.execute(
            context,
            lambda: self._do_create(user)
        )
    
    async def _do_create(self, user: UserPO) -> UserPO:
        """执行实际的创建操作"""
        self.session.add(user)
        await self.session.flush()
        return user
```

### 缓存拦截器配置

```python
from idp.framework.infrastructure.cache import CacheConfig, CacheManager
from idp.framework.infrastructure.persistence.sqlalchemy.interceptor.impl import CacheInterceptor
from idp.framework.infrastructure.persistence.sqlalchemy.repository import BaseRepository

class UserRepository(BaseRepository[UserPO]):
    """带缓存的用户仓储"""
    
    def __init__(
        self,
        session: AsyncSession,
        actor: str = "system",
        redis_url: str = "redis://localhost:6379/0"
    ):
        # 创建缓存配置
        cache_config = CacheConfig(
            strategy="rw",
            ttl=3600,
            backend="redis",
            redis_url=redis_url,
            enable_stats=True
        )
        
        # 创建缓存管理器
        cache_manager = CacheManager(cache_config)
        
        # 创建自定义缓存拦截器
        cache_interceptor = CacheInterceptor(cache_manager=cache_manager)
        
        # 初始化仓储，使用自定义缓存拦截器
        # 重要：设置use_cache=False避免创建两个缓存拦截器
        super().__init__(
            session=session,
            entity_type=UserPO,
            actor=actor,
            enable_logging=True,
            use_cache=False,
            custom_interceptors=[cache_interceptor]
        )
    
    async def find_by_username(self, username: str) -> Optional[UserPO]:
        """根据用户名查找用户（使用缓存）"""
        # 设置自定义缓存键
        cache_key = f"user:username:{username}"
        self.context_data["cache_key"] = cache_key
        
        return await self.find_one(username=username)
```

### 聚合验证

```python
from idp.infrastructure.persistence.sqlalchemy.interceptor.impl.aggregate_boundary import (
    aggregate_root,
    aggregate_entity,
    AggregateValidator
)

class OrderValidator(AggregateValidator):
    """订单聚合验证器"""
    
    async def validate(self, entity, entity_type, operation, context):
        # 验证订单项数量
        if entity_type.__name__ == "OrderPO":
            if operation in [OperationType.CREATE, OperationType.UPDATE]:
                if not hasattr(entity, "items") or not entity.items:
                    raise AggregateValidationError(
                        "Order must have at least one item",
                        entity_type,
                        getattr(entity, "id", None)
                    )

@aggregate_root(OrderValidator())
class OrderPO(Base):
    # 订单实体定义...
    pass

@aggregate_entity(OrderPO)
class OrderItemPO(Base):
    # 订单项实体定义...
    pass
```

### 自定义拦截器

```python
from idp.infrastructure.persistence.sqlalchemy.interceptor import Interceptor, InterceptorContext, OperationType

class CustomInterceptor(Interceptor):
    """自定义拦截器示例"""
    
    @property
    def priority(self) -> int:
        return 50
    
    async def before_operation(self, context: InterceptorContext) -> None:
        """操作前执行的逻辑"""
        entity = context.entity
        # 自定义前置逻辑...
    
    async def after_operation(self, context: InterceptorContext) -> None:
        """操作后执行的逻辑"""
        result = context.result
        # 自定义后置逻辑...
    
    async def on_error(self, context: InterceptorContext, error: Exception) -> Exception:
        """错误处理逻辑"""
        # 自定义错误处理...
        return error
```

## 完整示例

请参考 `examples.py` 文件，其中包含了完整的使用示例，包括：

- 实体定义与元数据配置
- 聚合根和聚合实体的定义
- 自定义验证器和事件发布器
- 仓储实现
- 完整的操作流程

## 最佳实践

1. **使用元数据装饰器**：通过 `@entity_metadata` 装饰器配置实体行为，避免硬编码
2. **定义清晰的聚合边界**：使用 `@aggregate_root` 和 `@aggregate_entity` 明确聚合关系
3. **实现自定义验证器**：针对特定领域规则实现 `AggregateValidator`
4. **处理领域事件**：实现自定义 `EventPublisher` 处理领域事件
5. **优化批量操作**：对于批量操作，使用 `BatchInterceptorChain` 提高性能
6. **有效利用缓存**：合理配置缓存策略，为关键查询添加自定义cache_key
7. **避免重复拦截器**：使用自定义缓存拦截器时设置use_cache=False避免重复

## 缓存最佳实践

1. **缓存键管理**：
   - 为频繁查询设置自定义缓存键
   - 使用统一的键格式，如`{entity_type}:{operation}:{id}`
   - 谨慎管理缓存前缀，确保前缀一致性

2. **缓存失效策略**：
   - 更新操作后自动清理相关缓存
   - 对于复杂关系，实现自定义缓存清理逻辑
   - 软删除操作特别处理，确保缓存一致性

3. **性能优化**：
   - 避免为同一查询创建多个缓存拦截器
   - 在上下文传递中保持缓存键一致性
   - 使用精确的模式匹配来清理缓存，避免过度清理

## 扩展点

拦截器系统提供了多个扩展点：

1. **自定义拦截器**：继承 `Interceptor` 基类实现自定义拦截器
2. **自定义事件发布器**：实现 `EventPublisher` 接口处理领域事件
3. **自定义聚合验证器**：实现 `AggregateValidator` 接口验证聚合规则
4. **元数据扩展**：扩展 `EntityMetadata` 添加自定义元数据
5. **自定义缓存后端**：实现 `CacheBackend` 接口支持不同缓存存储

## 性能考虑

1. **拦截器优先级**：合理设置拦截器优先级，确保高优先级拦截器先执行
2. **批量操作优化**：对于批量操作，使用批量拦截器链减少开销
3. **缓存利用**：`InterceptorFactory` 内置缓存机制，避免重复创建拦截器链
4. **异步操作**：充分利用异步特性，避免阻塞操作
5. **缓存策略**：根据读写比例选择最佳缓存策略，高读低写场景使用"rw"策略

## 软删除功能设计

软删除使用拦截器模式实现，主要组件：

1. SoftDeleteInterceptor - 拦截DELETE操作，转换为标记删除
2. BaseRepository扩展方法 - 提供soft_delete和hard_delete等便捷方法

使用流程：
1. 创建仓储时启用软删除功能：
   repo = UserRepository(session, enable_soft_delete=True)

2. 执行软删除：
   await repo.soft_delete(entity_id)  # 推荐
   # 或者
   await repo.delete(entity)  # 通用方法

3. 查询时过滤已删除记录：
   user = await repo.get_by_id(id)  # 自动排除已删除记录
   # 或者
   user = await repo.get_by_id(id, include_deleted=True)  # 包含已删除记录 