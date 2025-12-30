# Bento Framework 架构指南总结

## 📚 完整文档索引

1. **[ARCHITECTURE_SERVICES_PLACEMENT.md](./ARCHITECTURE_SERVICES_PLACEMENT.md)** - Services 正确放置指南
2. **[ARCHITECTURE_SPECIFICATION_PLACEMENT.md](./ARCHITECTURE_SPECIFICATION_PLACEMENT.md)** - Specification 正确放置指南
3. **[USING_REPOSITORY_MIXINS.md](./USING_REPOSITORY_MIXINS.md)** - Repository Mixins 使用指南

## 🎯 核心架构原则

### 1. 依赖方向（六边形架构）

```
Interfaces → Application → Domain ← Infrastructure
   (UI)      (用例编排)   (业务核心)  (技术实现)
```

**金科玉律**：
- ✅ 外层依赖内层
- ✅ 内层不知道外层
- ✅ Domain 层不依赖任何框架

### 2. 标准目录结构

```
contexts/ordering/
├── domain/                              # 领域层（最内层）
│   ├── order.py                         # ✅ 聚合根
│   ├── order_item.py                    # ✅ 实体
│   ├── services/                        # ✅ Domain Services（谨慎使用）
│   │   └── pricing_service.py          # 跨聚合根的纯业务逻辑
│   └── ports/                           # ✅ 端口定义
│       ├── repositories/                # Repository 接口
│       └── services/                    # 外部服务接口
│
├── application/                         # 应用层
│   ├── commands/                        # ✅ Command Handlers
│   ├── queries/                         # ✅ Query Handlers
│   ├── services/                        # ✅ Application Services
│   │   └── order_analytics_service.py  # 查询、统计、编排
│   └── event_handlers/                  # ✅ Event Handlers
│
├── infrastructure/                      # 基础设施层
│   ├── repositories/                    # ✅ Repository 实现
│   ├── specifications/                  # ✅ Query Specifications
│   │   └── order_query_spec.py         # 查询构建器
│   ├── models/                          # ✅ PO 模型
│   └── adapters/
│       └── services/                    # ✅ 外部服务实现
│
└── interfaces/                          # 接口层
    └── order_api.py                     # ✅ REST API
```

## 🔑 关键决策

### 业务逻辑放在哪里？

```
业务逻辑
    │
    ├─ 只涉及单个聚合根？
    │   └─ ✅ 聚合根内部方法（domain/order.py）
    │
    ├─ 跨多个聚合根？
    │   ├─ 需要访问数据库？
    │   │   └─ ✅ Application Service (application/services/)
    │   └─ 不需要访问数据库？
    │       └─ ✅ Domain Service (domain/services/)
    │
    └─ 需要外部服务或Repository？
        └─ ✅ Application Service (application/services/)
```

### Specification 放在哪里？

```
Specification
    │
    ├─ 纯业务规则（不依赖框架）？
    │   └─ ✅ domain/specifications/ (很少需要)
    │       例：OrderBusinessRules.can_be_cancelled()
    │
    └─ 查询构建器（依赖持久化框架）？
        └─ ✅ infrastructure/specifications/
            例：OrderQuerySpec.amount_greater_than()
```

## 📋 实战检查清单

### ✅ 正确的实践

```python
# ✅ 聚合根方法
class Order:
    def add_item(self, ...):
        """添加订单项"""
        pass

    def calculate_total(self):
        """计算总额"""
        pass

# ✅ Domain Service（跨聚合根）
class PricingService:
    def calculate_price(self, product, customer, promotions):
        """涉及多个聚合根的定价"""
        pass

# ✅ Application Service（查询统计）
class OrderAnalyticsService:
    def __init__(self, repo):
        self._repo = repo  # 依赖 Repository

    async def get_stats(self):
        return await self._repo.sum_field("total")

# ✅ Query Specification（基础设施层）
class OrderQuerySpec(SpecificationBuilder):
    def amount_greater_than(self, amount):
        """查询构建器"""
        pass
```

### ❌ 常见错误

```python
# ❌ 错误：Domain 层依赖基础设施
# domain/specifications/order_spec.py
from bento.persistence.specification import ...  # ❌

# ❌ 错误：不需要的 Domain Service
class OrderDomainService:
    def calculate_total(self, order):
        return sum(...)  # 应该在 Order 内部

# ❌ 错误：在 Application Service 中写业务逻辑
class CreateOrderUseCase:
    async def handle(self, command):
        # ❌ 直接计算折扣
        if customer.is_vip():
            price *= 0.95
        # 应该调用 Domain Service 或聚合根方法
```

## 🎯 你的项目评估

| 组件 | 当前位置 | 评估 |
|------|---------|------|
| OrderAnalyticsService | `application/services/` | ✅ 正确 |
| OrderQuerySpec | `infrastructure/specifications/` | ✅ 正确（已修正）|
| Order.add_item() | `domain/order.py` | ✅ 正确 |
| IPaymentService | `domain/ports/services/` | ✅ 正确 |

## 📖 延伸阅读

- **DDD 蓝皮书**: Eric Evans - Domain-Driven Design
- **六边形架构**: Alistair Cockburn - Hexagonal Architecture
- **整洁架构**: Robert Martin - Clean Architecture

## 💡 记住

1. **聚合根优先** - 80% 的业务逻辑应该在聚合根内
2. **Domain Service 谨慎使用** - 只在真正跨聚合根时
3. **Application Service 负责编排** - 协调 Repository 和外部服务
4. **Specification 分两种** - 业务规则 vs 查询构建器
5. **依赖方向正确** - Domain 不依赖任何外部

---

**你的架构理解非常准确！继续保持！** 🎉
