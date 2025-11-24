# 目录结构对比：当前 vs 标准

## ❌ 当前结构（有问题）

```
contexts/ordering/
├── domain/
│   ├── order.py                          ✅ 聚合根位置正确
│   ├── order_item.py                     ✅ 实体位置正确
│   ├── product_info.py                   ⚠️ 应该在 vo/ 子目录
│   └── events/                           ✅ 事件目录正确
│       ├── order_created_event.py
│       └── order_paid_event.py
│
├── application/
│   ├── commands/                         ✅ 命令目录正确
│   │   └── create_order.py
│   ├── queries/                          ✅ 查询目录正确
│   └── ports/                            ❌ 错误！Port 不应在这里
│       └── product_catalog_service.py    ❌ 应该在 domain/ports/
│
└── infrastructure/
    ├── models/                           ✅ 持久化模型正确
    ├── mappers/                          ✅ 映射器正确
    ├── repositories/                     ✅ 仓储实现正确
    └── services/                         ⚠️ 应该叫 adapters/
        └── product_catalog_service.py    ⚠️ 命名不够明确
```

**问题诊断：**

1. **Port 位置错误**
   - ❌ `application/ports/product_catalog_service.py`
   - ✅ 应该是 `domain/ports/services/i_product_catalog_service.py`

2. **值对象位置不规范**
   - ⚠️ `domain/product_info.py`
   - ✅ 应该是 `domain/vo/product_info.py`

3. **Adapter 命名不明确**
   - ⚠️ `infrastructure/services/product_catalog_service.py`
   - ✅ 应该是 `infrastructure/adapters/services/product_catalog_adapter.py`

4. **与 Identity BC 不一致**
   - Identity BC 使用 `domain/ports/` ✅
   - Ordering BC 使用 `application/ports/` ❌

---

## ✅ 标准结构（六边形架构 + DDD）

```
contexts/ordering/
├── domain/                               # 领域层（核心业务逻辑）
│   ├── order.py                          # 聚合根
│   ├── order_item.py                     # 实体
│   ├── vo/                               # ✅ 值对象专用目录
│   │   └── product_info.py               # ✅ 值对象
│   ├── events/                           # 领域事件
│   │   ├── order_created_event.py
│   │   └── order_paid_event.py
│   ├── services/                         # 领域服务（可选）
│   │   └── pricing_service.py
│   └── ports/                            # ✅ Secondary Ports（接口定义）
│       ├── repositories/
│       │   └── i_order_repository.py     # 仓储接口
│       └── services/
│           └── i_product_catalog_service.py  # ✅ 外部服务接口
│
├── application/                          # 应用层（用例编排）
│   ├── commands/                         # 命令（写操作）
│   │   ├── create_order.py
│   │   └── pay_order.py
│   ├── queries/                          # 查询（读操作）
│   │   ├── get_order.py
│   │   └── list_orders.py
│   └── dto/                              # 数据传输对象
│       └── order_dto.py
│
└── infrastructure/                       # 基础设施层（技术实现）
    ├── persistence/                      # 持久化相关
    │   ├── models/                       # ORM 模型
    │   │   ├── order_po.py
    │   │   └── order_item_po.py
    │   └── mappers/                      # 对象映射器
    │       ├── order_mapper.py
    │       └── order_item_mapper.py
    └── adapters/                         # ✅ Secondary Adapters（实现）
        ├── repositories/                 # 仓储适配器
        │   └── order_repository.py
        └── services/                     # 外部服务适配器
            └── product_catalog_adapter.py  # ✅ 反腐败层实现
```

---

## 🔍 核心差异对比

### 1. Port（接口）位置

| 方面 | 当前（错误） | 标准（正确） | 原因 |
|-----|------------|------------|------|
| **路径** | `application/ports/` | `domain/ports/` | Port 是领域契约的一部分 |
| **依赖方向** | Domain → Application | Application → Domain | 依赖倒置原则 |
| **可测试性** | 需要 Application 层 | Domain 层可独立测试 | 核心业务逻辑隔离 |

### 2. Adapter（实现）命名

| 方面 | 当前（不清晰） | 标准（清晰） | 原因 |
|-----|--------------|------------|------|
| **目录名** | `services/` | `adapters/` | 明确表示这是适配器层 |
| **文件名** | `product_catalog_service.py` | `product_catalog_adapter.py` | 明确表示这是 Adapter |
| **类名** | `ProductCatalogService` | `ProductCatalogAdapter` | 避免与 Port 混淆 |

### 3. 值对象位置

| 方面 | 当前（不规范） | 标准（规范） | 原因 |
|-----|--------------|------------|------|
| **路径** | `domain/product_info.py` | `domain/vo/product_info.py` | 值对象应该分组 |
| **组织方式** | 平铺在 domain/ | 按类型分子目录 | 大型项目更易管理 |

---

## 📐 依赖方向对比

### 当前（错误的依赖方向）

```
┌──────────────┐
│   Domain     │
│   (Order)    │
└──────┬───────┘
       │ depends on
       ↓
┌──────────────┐
│ Application  │
│   (Ports)    │  ← ❌ 错误：Domain 依赖 Application
└──────┬───────┘
       │ implements
       ↓
┌──────────────┐
│Infrastructure│
│  (Services)  │
└──────────────┘
```

**问题：** Domain 层依赖 Application 层，违反了分层架构原则。

---

### 标准（正确的依赖方向）

```
┌──────────────┐
│Infrastructure│
│  (Adapters)  │ ← 实现层
└──────┬───────┘
       │ implements
       ↓
┌──────────────┐
│   Domain     │
│   (Ports)    │ ← 接口层（核心）
└──────┬───────┘
       ↑ uses
       │
┌──────────────┐
│ Application  │
│  (Commands)  │ ← 编排层
└──────────────┘
```

**正确：** 所有层都依赖或实现 Domain 层的接口。

---

## 🎯 为什么这样设计？

### 六边形架构（Hexagonal Architecture）原理

```
         ┌─────────────────────────────────────┐
         │         Application Core            │
         │    ┌─────────────────────┐          │
         │    │   Domain Model      │          │
         │    │  (Aggregates, VOs)  │          │
         │    └─────────────────────┘          │
         │              │                       │
         │              ↓                       │
         │    ┌─────────────────────┐          │
         │    │   Domain Ports      │ ← Port   │
         │    │   (Interfaces)      │          │
         │    └─────────────────────┘          │
         └──────────┬──────────┬────────────────┘
                    │          │
         ┌──────────┘          └──────────┐
         ↓                                 ↓
┌────────────────┐              ┌────────────────┐
│   Adapters     │              │   Adapters     │
│  (Database)    │              │  (External     │
│                │              │   Services)    │
└────────────────┘              └────────────────┘
```

**核心思想：**
1. **应用核心**（Domain + Application）定义业务逻辑和接口
2. **适配器**（Infrastructure）实现技术细节
3. **依赖方向**：外层依赖内层，内层不依赖外层

---

## 📊 各 BC 当前状态对比

| BC | Port 位置 | Adapter 位置 | 一致性 | 评分 |
|----|----------|-------------|-------|------|
| **Identity** | `domain/ports/` ✅ | `infrastructure/repositories/` ✅ | 高 | ⭐⭐⭐⭐⭐ |
| **Catalog** | ❌ 无 ports | `infrastructure/repositories/` ✅ | 中 | ⭐⭐⭐ |
| **Ordering** | `application/ports/` ❌ | `infrastructure/services/` ⚠️ | 低 | ⭐⭐ |

**结论：** 各 BC 的目录结构不统一，需要标准化。

---

## 🔄 迁移路径

### 最小改动方案（推荐）

**优先级 P0（必须修复）：**
1. 移动 `application/ports/` → `domain/ports/services/`
2. 重命名接口文件加 `i_` 前缀
3. 更新所有导入路径

**优先级 P1（建议改进）：**
4. 重命名 `infrastructure/services/` → `infrastructure/adapters/services/`
5. 重命名实现类加 `Adapter` 后缀
6. 移动 `domain/product_info.py` → `domain/vo/product_info.py`

**优先级 P2（长期目标）：**
7. 统一所有 BC 的目录结构
8. 添加 README 说明各层职责
9. 建立代码审查清单

### 完全标准化方案

所有 BC 统一使用：
```
context/
├── domain/
│   ├── aggregates/
│   ├── entities/
│   ├── vo/
│   ├── events/
│   ├── services/
│   └── ports/
├── application/
│   ├── commands/
│   ├── queries/
│   └── dto/
├── infrastructure/
│   ├── persistence/
│   │   ├── models/
│   │   └── mappers/
│   └── adapters/
│       ├── repositories/
│       └── services/
└── interfaces/
    └── api/
```

---

## ✅ 验证清单

重构完成后，检查以下项：

- [ ] Port 接口在 `domain/ports/`
- [ ] Adapter 实现在 `infrastructure/adapters/`
- [ ] 值对象在 `domain/vo/`
- [ ] 接口以 `I` 开头或用 `Protocol`
- [ ] 适配器类名包含 `Adapter` 或明确技术栈
- [ ] 所有测试通过
- [ ] 导入路径正确
- [ ] 与其他 BC 目录结构一致

---

## 📚 参考资料

### 标准实现参考

**Identity BC（当前最佳）：**
```python
# domain/ports/user_repository.py
class IUserRepository(Protocol):
    """User repository port (interface)."""
    pass

# infrastructure/repositories/user_repository_impl.py
class UserRepository(IUserRepository):
    """User repository adapter (implementation)."""
    pass
```

**Ecommerce 示例：**
```python
# modules/order/domain/ports/order_repository.py
class IOrderRepository(Protocol):
    pass

# modules/order/persistence/repositories/order_repository.py
class OrderRepository(IOrderRepository):
    pass
```

---

## 🎓 学习资源

1. **Hexagonal Architecture（六边形架构）**
   - Alistair Cockburn 的原始论文
   - "Get Your Hands Dirty on Clean Architecture" - Tom Hombergs

2. **Domain-Driven Design（领域驱动设计）**
   - "Domain-Driven Design" - Eric Evans
   - "Implementing Domain-Driven Design" - Vaughn Vernon

3. **Ports and Adapters（端口与适配器）**
   - Martin Fowler 的博客
   - "Clean Architecture" - Robert C. Martin

---

## 💡 关键要点

### 记住这个依赖规则

> **依赖方向：Infrastructure → Domain ← Application**
>
> - Domain 层定义接口（Port）
> - Infrastructure 层实现接口（Adapter）
> - Application 层使用接口（不依赖实现）
> - Domain 层不依赖任何其他层

### 命名约定

| 类型 | 位置 | 命名模式 | 示例 |
|-----|------|---------|------|
| Port | `domain/ports/` | `IXxxService` 或 `IXxxRepository` | `IProductCatalogService` |
| Adapter | `infrastructure/adapters/` | `XxxAdapter` 或 `XxxRepository` | `ProductCatalogAdapter` |
| Value Object | `domain/vo/` | `XxxVO` 或 直接名称 | `ProductInfo` |

---

## 🎯 总结

### 当前问题
1. ❌ Port 在 `application/ports/`（应该在 `domain/ports/`）
2. ⚠️ Adapter 在 `services/`（应该在 `adapters/`）
3. ⚠️ 值对象位置不规范
4. ❌ 各 BC 结构不一致

### 改进后收益
1. ✅ 符合六边形架构标准
2. ✅ 依赖方向清晰正确
3. ✅ Domain 层完全独立
4. ✅ 易于测试和维护
5. ✅ 各 BC 结构统一
6. ✅ 代码职责明确

**下一步：** 按照 `REFACTOR_PLAN.md` 执行重构。
