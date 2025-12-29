# Multi-Tenancy 集成分析

## 问题
Bento Framework 提供了完整的 multi-tenancy 支持，是否需要集成到 my-shop 应用中？

## Bento Framework Multi-Tenancy 功能

### 核心组件

1. **TenantContext** - 租户上下文管理
   ```python
   from bento.multitenancy import TenantContext

   # 获取当前租户
   tenant_id = TenantContext.get()
   tenant_id = TenantContext.require()  # 必须存在，否则抛异常
   ```

2. **TenantResolver** - 租户识别策略
   - `HeaderTenantResolver` - 从 HTTP header 提取
   - `TokenTenantResolver` - 从 JWT token 提取
   - `SubdomainTenantResolver` - 从子域名提取
   - `CompositeTenantResolver` - 组合多种策略

3. **Tenant Middleware** - 自动租户识别
   ```python
   from bento.multitenancy import add_tenant_middleware, HeaderTenantResolver

   add_tenant_middleware(
       app,
       resolver=HeaderTenantResolver(),
       require_tenant=True,
       exclude_paths=["/health", "/docs"],
   )
   ```

4. **Repository 自动过滤** - 数据隔离
   - 自动在查询中添加 `tenant_id` 过滤
   - 防止跨租户数据泄露

### 已有的租户支持

框架中已经有租户支持的组件：
- ✅ `IdempotencyRecord` - 包含 `tenant_id` 字段
- ✅ `OutboxRecord` - 包含 `tenant_id` 字段
- ✅ `InboxRecord` - 包含 `tenant_id` 字段
- ✅ Repository mixins - 自动租户过滤

## my-shop 当前状态

### 当前租户使用情况

1. **IdempotencyMiddleware**
   ```python
   app.add_middleware(
       IdempotencyMiddleware,
       tenant_id="default",  # 硬编码为 "default"
   )
   ```

2. **数据模型**
   - 当前没有 `tenant_id` 字段
   - 所有数据共享，无租户隔离

3. **业务场景**
   - 单一商店应用
   - 没有多租户需求

## 是否需要集成 Multi-Tenancy？

### ❌ 当前阶段：**不需要**

**理由**:

1. **业务需求不明确**
   - my-shop 是单一商店应用
   - 没有 SaaS 化需求
   - 没有多租户业务场景

2. **增加复杂度**
   - 需要在所有表添加 `tenant_id` 字段
   - 需要修改所有查询逻辑
   - 增加开发和维护成本

3. **性能开销**
   - 每个查询都需要添加租户过滤
   - 索引需要包含 `tenant_id`
   - 数据库查询更复杂

4. **YAGNI 原则**
   - You Aren't Gonna Need It
   - 不要为未来可能的需求过度设计

### ✅ 未来可能需要的场景

如果 my-shop 需要支持以下场景，则应该集成 multi-tenancy：

1. **SaaS 化**
   - 多个商家共享同一个系统
   - 每个商家有独立的数据
   - 例如：Shopify、有赞模式

2. **白标方案**
   - 为不同客户提供定制化商店
   - 数据完全隔离

3. **企业级部署**
   - 同一个公司的多个部门/品牌
   - 需要数据隔离但共享基础设施

## 推荐方案

### Phase 1: 当前阶段（保持简单）

**不集成 multi-tenancy**，保持当前架构：

```python
# 继续使用默认租户
app.add_middleware(
    IdempotencyMiddleware,
    tenant_id="default",
)
```

**优势**:
- ✅ 简单直接
- ✅ 开发效率高
- ✅ 性能更好
- ✅ 易于理解和维护

### Phase 2: 未来需要时（渐进式迁移）

如果未来确实需要 multi-tenancy，可以渐进式迁移：

#### Step 1: 添加租户识别

```python
from bento.multitenancy import add_tenant_middleware, HeaderTenantResolver

# 添加租户 middleware
add_tenant_middleware(
    app,
    resolver=HeaderTenantResolver(header_name="X-Tenant-ID"),
    require_tenant=False,  # 开始时不强制
    exclude_paths=["/health", "/ping", "/docs"],
)
```

#### Step 2: 数据库迁移

```python
# 为所有表添加 tenant_id 字段
# Alembic migration
def upgrade():
    op.add_column('orders', sa.Column('tenant_id', sa.String(64), nullable=True))
    op.add_column('products', sa.Column('tenant_id', sa.String(64), nullable=True))
    # ... 其他表

    # 为现有数据设置默认租户
    op.execute("UPDATE orders SET tenant_id = 'default'")
    op.execute("UPDATE products SET tenant_id = 'default'")

    # 设置为 NOT NULL
    op.alter_column('orders', 'tenant_id', nullable=False)
    op.alter_column('products', 'tenant_id', nullable=False)

    # 添加索引
    op.create_index('ix_orders_tenant', 'orders', ['tenant_id'])
```

#### Step 3: 更新 Repository

```python
from bento.infrastructure.repository.mixins import TenantFilterMixin

class OrderRepository(TenantFilterMixin, SqlAlchemyRepository[Order]):
    """Order repository with automatic tenant filtering."""
    pass
```

#### Step 4: 更新业务逻辑

```python
from bento.multitenancy import TenantContext

async def create_order(command: CreateOrderCommand) -> Order:
    # 自动使用当前租户
    tenant_id = TenantContext.require()

    order = Order(
        id=ID.generate(),
        tenant_id=tenant_id,  # 添加租户
        customer_id=command.customer_id,
        items=command.items,
    )

    await order_repo.save(order)
    return order
```

## 当前建议的配置

### 保持简单，使用默认租户

```python
# runtime/bootstrap_v2.py

# Idempotency 使用默认租户
app.add_middleware(
    IdempotencyMiddleware,
    header_name="x-idempotency-key",
    ttl_seconds=86400,
    tenant_id="default",  # 保持默认
)

# 不添加 TenantMiddleware
# 不修改数据模型
# 不添加租户过滤逻辑
```

### 为未来预留扩展点

如果想为未来预留扩展点，可以：

1. **在配置中添加租户选项**（但不启用）
   ```python
   # config/settings.py
   class Settings(BaseSettings):
       # Multi-tenancy (future use)
       enable_multitenancy: bool = False
       tenant_header_name: str = "X-Tenant-ID"
       default_tenant_id: str = "default"
   ```

2. **在文档中说明迁移路径**
   - 保留此文档作为未来参考
   - 记录迁移步骤

3. **不修改代码**
   - 保持当前简单架构
   - 等待真实需求出现

## 决策矩阵

| 场景 | 是否需要 Multi-Tenancy | 优先级 |
|------|----------------------|--------|
| 单一商店应用 | ❌ 不需要 | - |
| 多商家 SaaS 平台 | ✅ 需要 | 高 |
| 白标解决方案 | ✅ 需要 | 高 |
| 企业多部门 | ✅ 需要 | 中 |
| 开发/测试环境隔离 | ⚠️ 可选 | 低 |

## 结论

### 当前阶段：**不集成 Multi-Tenancy**

**原因**:
1. ✅ my-shop 是单一商店应用，无多租户需求
2. ✅ 保持架构简单，降低复杂度
3. ✅ 遵循 YAGNI 原则
4. ✅ 提高开发效率和性能

### 未来考虑

当出现以下情况时，再考虑集成：
- 📋 需要支持多个商家
- 📋 需要 SaaS 化部署
- 📋 需要数据隔离
- 📋 有明确的多租户业务需求

### 迁移路径

如果未来需要，可以参考本文档的 Phase 2 渐进式迁移方案。

## 参考

- [Bento Multi-Tenancy 文档](../../../src/bento/multitenancy/)
- [Multi-Tenancy 最佳实践](https://docs.microsoft.com/en-us/azure/architecture/guide/multitenant/overview)
- [SaaS 架构模式](https://martinfowler.com/articles/multi-tenant.html)
