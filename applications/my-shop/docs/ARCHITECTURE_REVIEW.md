# 架构审查：目录结构与命名规范

## 📊 当前问题分析

### 问题 1: Port 位置不一致 ❌

**Ordering BC（新重构）:**
```
contexts/ordering/
├── application/
│   └── ports/  ❌ 错误：Port 不应该在 application 层
│       └── product_catalog_service.py
```

**Identity BC（原有）:**
```
contexts/identity/
├── domain/
│   └── ports/  ✅ 正确：Port 应该在 domain 层
│       └── user_repository.py
```

**不一致！** Ordering BC 和 Identity BC 的目录结构不统一。

---

### 问题 2: 没有明确使用 "adapter" 术语 ⚠️

**当前命名：**
```
contexts/ordering/
└── infrastructure/
    └── services/  ⚠️ 名称不够明确
        └── product_catalog_service.py
```

**更好的命名（六边形架构标准）：**
```
contexts/ordering/
└── infrastructure/
    └── adapters/  ✅ 明确表示这是适配器
        └── product_catalog_adapter.py
```

---

### 问题 3: 术语混淆

| 当前名称 | 六边形架构术语 | 说明 |
|---------|---------------|------|
| `IProductCatalogService` | Port (端口) | 接口定义 |
| `ProductCatalogService` | Adapter (适配器) | 接口实现 |

应该使用更明确的命名，避免混淆。

---

## 🎯 标准的六边形架构 + DDD 目录结构

### 理论基础

**六边形架构（Ports and Adapters）核心概念：**

```
        外部世界
           ↓
    ┌──────────────┐
    │   Primary    │ (Driving Adapters: REST API, CLI)
    │   Adapters   │
    └──────────────┘
           ↓
    ┌──────────────┐
    │  Application │
    │     Core     │ ← 业务逻辑核心
    └──────────────┘
           ↓
    ┌──────────────┐
    │  Secondary   │ (Driven Adapters: Database, External API)
    │   Adapters   │
    └──────────────┘
           ↓
        外部系统
```

**Port vs Adapter:**
- **Port（端口）**: 应用核心定义的接口契约
  - Primary Port: 应用提供给外部的接口（如 UseCase）
  - Secondary Port: 应用需要的外部依赖接口（如 Repository、ExternalService）

- **Adapter（适配器）**: 实现 Port 的具体技术
  - Primary Adapter: 调用应用的适配器（如 FastAPI Controller）
  - Secondary Adapter: 被应用调用的适配器（如 SQLAlchemy Repository）

---

### 标准目录结构（推荐方案）

```
context/
├── domain/                    # 领域层（核心业务逻辑）
│   ├── aggregates/            # 聚合根
│   │   ├── order.py
│   │   └── product.py
│   ├── entities/              # 实体
│   │   └── order_item.py
│   ├── vo/                    # 值对象
│   │   ├── money.py
│   │   └── product_info.py    # ✅ 值对象应该在这里
│   ├── events/                # 领域事件
│   │   ├── order_created.py
│   │   └── order_paid.py
│   ├── services/              # 领域服务
│   │   └── pricing_service.py
│   └── ports/                 # ✅ Secondary Ports（被驱动端口）
│       ├── repositories/      # 仓储接口
│       │   ├── i_order_repository.py
│       │   └── i_product_repository.py
│       └── services/          # 外部服务接口
│           └── i_product_catalog_service.py  # ✅ 应该在这里
│
├── application/               # 应用层（用例编排）
│   ├── commands/              # 命令（CQS）
│   │   ├── create_order.py
│   │   └── pay_order.py
│   ├── queries/               # 查询（CQS）
│   │   ├── get_order.py
│   │   └── list_orders.py
│   ├── dto/                   # 数据传输对象
│   │   └── order_dto.py
│   └── services/              # 应用服务（可选）
│       └── order_application_service.py
│
├── infrastructure/            # 基础设施层（技术实现）
│   ├── persistence/           # 持久化相关
│   │   ├── models/            # ORM 模型
│   │   │   ├── order_po.py
│   │   │   └── order_item_po.py
│   │   └── mappers/           # 对象映射器
│   │       ├── order_mapper.py
│   │       └── order_item_mapper.py
│   └── adapters/              # ✅ Secondary Adapters（适配器实现）
│       ├── repositories/      # 仓储适配器
│       │   ├── order_repository.py
│       │   └── product_repository.py
│       └── services/          # 外部服务适配器
│           └── product_catalog_adapter.py  # ✅ 应该叫 adapter
│
└── interfaces/                # 接口层（外部交互）
    ├── api/                   # ✅ Primary Adapters（驱动适配器）
    │   ├── order_controller.py
    │   └── order_presenter.py
    └── cli/                   # 命令行接口（可选）
        └── order_cli.py
```

---

## 🔄 命名规范建议

### 接口（Port）命名

**推荐模式：**
```python
# domain/ports/repositories/i_order_repository.py
class IOrderRepository(Protocol):
    """Order repository port (interface)."""
    pass

# domain/ports/services/i_product_catalog_service.py
class IProductCatalogService(Protocol):
    """Product catalog service port (interface)."""
    pass
```

**命名规则：**
- 以 `I` 开头表示接口（Interface）
- 使用 `Protocol` 或 `ABC` 作为基类
- 放在 `domain/ports/` 目录

---

### 适配器（Adapter）命名

**推荐模式：**
```python
# infrastructure/adapters/repositories/order_repository.py
class OrderRepository(IOrderRepository):
    """Order repository adapter (SQLAlchemy implementation)."""
    pass

# infrastructure/adapters/services/product_catalog_adapter.py
class ProductCatalogAdapter(IProductCatalogService):
    """Product catalog adapter (cross-BC query implementation)."""
    pass
```

**命名规则：**
- 实现类名可以直接用 `XxxRepository`、`XxxAdapter`
- 或者加后缀 `SqlAlchemyOrderRepository`（明确技术栈）
- 放在 `infrastructure/adapters/` 目录

---

## 📋 重构建议（优先级）

### P0 - 立即修复（影响一致性）

1. **移动 Port 到 domain 层**
   ```bash
   # 从
   contexts/ordering/application/ports/
   # 移动到
   contexts/ordering/domain/ports/services/
   ```

2. **更新导入路径**
   - 修改 `create_order.py` 中的导入
   - 修改 API 依赖注入
   - 修改测试导入

### P1 - 改进命名（提高可读性）

3. **重命名 infrastructure/services → infrastructure/adapters**
   ```bash
   # 从
   contexts/ordering/infrastructure/services/
   # 重命名为
   contexts/ordering/infrastructure/adapters/services/
   ```

4. **类名重命名（可选）**
   ```python
   # 从
   class ProductCatalogService
   # 改为
   class ProductCatalogAdapter  # 更明确
   ```

### P2 - 统一规范（长期改进）

5. **统一所有 BC 的目录结构**
   - Catalog BC 添加 `domain/ports/`
   - Identity BC 检查是否符合规范
   - Ordering BC 按新规范调整

6. **值对象位置调整**
   ```bash
   # 从
   contexts/ordering/domain/product_info.py
   # 移动到
   contexts/ordering/domain/vo/product_info.py
   ```

---

## 🎓 为什么使用 domain/ports 而非 application/ports？

### 依赖方向分析

**错误方式（application/ports）:**
```
domain/ → application/ports/ → infrastructure/
  ↑                ↓
  └────────────────┘  # 循环依赖！
```

**正确方式（domain/ports）:**
```
infrastructure/ → domain/ports/ ← application/
                       ↑
                    domain/
```

### 理由

1. **依赖倒置原则（DIP）**
   - Domain 层定义接口（Port）
   - Infrastructure 层实现接口（Adapter）
   - Application 层使用接口，不依赖实现

2. **领域独立性**
   - Port 是领域概念的一部分
   - "Order 需要持久化" 是领域需求
   - "用 PostgreSQL 实现" 是技术细节

3. **可测试性**
   - Domain 层完全独立
   - 可以在没有 Application 层的情况下测试 Domain
   - Mock Port 即可测试领域逻辑

---

## 📚 参考架构实现

### Identity BC（当前最佳实践）

```
contexts/identity/
├── domain/
│   ├── models/
│   │   └── user.py
│   ├── ports/                    ✅ 正确位置
│   │   └── user_repository.py   ✅ 正确命名
│   └── vo/
└── infrastructure/
    └── repositories/              ✅ 适配器实现
        └── user_repository_impl.py
```

### Ecommerce 示例（Bento 框架）

```
modules/order/
├── domain/
│   ├── order.py
│   └── ports/                     ✅ 正确位置
│       └── order_repository.py
├── persistence/                   ✅ 适配器层
│   ├── models/
│   ├── mappers/
│   └── repositories/
│       └── order_repository.py
```

---

## ✅ 最终目标结构

### Ordering BC（重构后）

```
contexts/ordering/
├── domain/
│   ├── order.py
│   ├── order_item.py
│   ├── events/
│   ├── vo/
│   │   └── product_info.py       ✅ 值对象应该在这里
│   └── ports/                     ✅ 接口定义
│       ├── repositories/
│       │   └── i_order_repository.py
│       └── services/
│           └── i_product_catalog_service.py
│
├── application/
│   ├── commands/
│   │   └── create_order.py      → 导入 domain.ports
│   └── queries/
│
└── infrastructure/
    ├── persistence/
    │   ├── models/
    │   └── mappers/
    └── adapters/                  ✅ 适配器实现
        ├── repositories/
        │   └── order_repository.py
        └── services/
            └── product_catalog_adapter.py
```

---

## 🎯 总结

### 当前问题
1. ❌ Port 位置错误（在 application 而非 domain）
2. ⚠️ 缺少明确的 "adapter" 术语
3. ❌ 各 BC 目录结构不一致

### 改进后
1. ✅ Port 统一放在 `domain/ports/`
2. ✅ Adapter 统一放在 `infrastructure/adapters/`
3. ✅ 命名清晰（IXxxService → XxxAdapter）
4. ✅ 符合六边形架构和 DDD 最佳实践

### 核心原则
- **Domain 层定义契约（Port）**
- **Infrastructure 层实现契约（Adapter）**
- **Application 层使用契约（通过 Port）**
- **依赖方向：Infrastructure → Domain ← Application**
