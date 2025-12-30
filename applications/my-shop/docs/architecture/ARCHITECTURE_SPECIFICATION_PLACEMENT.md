# Specification 正确放置位置指南

## 🏗️ 符合 DDD 和六边形架构的目录结构

```
contexts/ordering/
├── domain/                              # 领域层（最内层，不依赖外部）
│   ├── order.py                         # 聚合根
│   ├── order_item.py                    # 实体
│   ├── specifications/                  # ✅ 业务规则 Specification
│   │   └── order_business_rules.py     # 纯业务规则，不涉及持久化
│   └── ports/                           # 端口（接口）
│       └── repositories/
│           └── i_order_repository.py    # Repository 接口
│
├── application/                         # 应用层（用例编排）
│   ├── commands/
│   └── services/
│
└── infrastructure/                      # 基础设施层（技术实现）
    ├── repositories/
    │   └── order_repository_impl.py     # Repository 实现
    ├── specifications/                  # ✅ 查询 Specification
    │   └── order_query_spec.py          # 查询构建器（依赖持久化框架）
    └── models/
        └── order_po.py                   # 持久化对象
```

## 📝 两种 Specification 的区别

### 1. Domain Specification（业务规则）

**位置**：`domain/specifications/`

**特点**：
- ✅ 表达业务规则和业务概念
- ✅ 完全独立于技术实现
- ✅ 可以在领域层直接使用
- ✅ 不依赖任何框架

**示例**：
```python
# domain/specifications/order_business_rules.py

class OrderBusinessRules:
    """订单业务规则

    纯粹的业务逻辑，不涉及持久化或查询
    """

    @staticmethod
    def can_be_cancelled(order: Order) -> bool:
        """订单是否可以取消"""
        return order.status == OrderStatus.PENDING

    @staticmethod
    def requires_approval(order: Order) -> bool:
        """订单是否需要审批"""
        return order.total >= 10000.0

    @staticmethod
    def is_high_value(order: Order) -> bool:
        """是否高价值订单"""
        return order.total >= 1000.0

    @staticmethod
    def is_bulk_order(order: Order) -> bool:
        """是否批量订单"""
        return len(order.items) >= 10


# 使用方式（在领域服务中）
class OrderDomainService:
    def process_order(self, order: Order):
        if OrderBusinessRules.requires_approval(order):
            # 需要审批流程
            pass

        if OrderBusinessRules.is_high_value(order):
            # 触发特殊处理
            pass
```

### 2. Query Specification（查询规格）

**位置**：`infrastructure/specifications/` 或 `infrastructure/repositories/`

**特点**：
- ✅ 构建数据库查询
- ✅ 依赖持久化框架
- ✅ 技术实现细节
- ✅ 仅在 Repository 或 Application 层使用

**示例**：
```python
# infrastructure/specifications/order_query_spec.py

from bento.persistence.specification.builder import SpecificationBuilder
from bento.persistence.specification.criteria.comparison import (
    EqualsCriterion,
    GreaterThanCriterion,
)

class OrderQuerySpec(SpecificationBuilder):
    """订单查询规格

    用于构建数据库查询，属于基础设施层
    """

    def customer_id_equals(self, customer_id: str) -> "OrderQuerySpec":
        """筛选特定客户的订单"""
        self.add_criterion(EqualsCriterion("customer_id", customer_id))
        return self

    def amount_greater_than(self, amount: float) -> "OrderQuerySpec":
        """筛选金额大于指定值的订单"""
        self.add_criterion(GreaterThanCriterion("total", amount))
        return self

    # ... 其他查询条件


# 使用方式（在应用层或基础设施层）
class OrderAnalyticsService:
    async def get_high_value_orders(self, min_amount: float):
        spec = OrderQuerySpec().amount_greater_than(min_amount)
        return await self._repo.find(spec)
```

## 🔄 重构建议

### 当前代码的问题

```python
# ❌ 错误：domain 层依赖 infrastructure 层
# domain/specifications/order_spec.py
from bento.persistence.specification.builder import SpecificationBuilder

class OrderSpec(SpecificationBuilder):  # Domain 层不应该依赖持久化框架
    ...
```

### 推荐的重构方案

#### 方案 1：移动到 Infrastructure 层（推荐）

```bash
# 移动文件
mv contexts/ordering/domain/specifications/ \
   contexts/ordering/infrastructure/specifications/
```

```python
# infrastructure/specifications/order_query_spec.py
from bento.persistence.specification.builder import SpecificationBuilder

class OrderQuerySpec(SpecificationBuilder):
    """订单查询规格 - 基础设施层"""
    # ... 保持代码不变
```

```python
# 更新导入
# application/services/order_analytics_service.py
from contexts.ordering.infrastructure.specifications import OrderQuerySpec
```

#### 方案 2：如果需要 Domain Specification

如果你确实需要表达业务规则，可以**同时**保留两者：

```python
# ✅ domain/specifications/order_business_rules.py
class OrderBusinessRules:
    """业务规则（领域层）"""

    @staticmethod
    def can_be_cancelled(order: Order) -> bool:
        return order.status == OrderStatus.PENDING

    @staticmethod
    def is_high_value(order: Order) -> bool:
        return order.total >= 1000.0


# ✅ infrastructure/specifications/order_query_spec.py
class OrderQuerySpec(SpecificationBuilder):
    """查询规格（基础设施层）"""

    def customer_id_equals(self, customer_id: str):
        ...

    def amount_greater_than(self, amount: float):
        ...
```

## 📚 参考其他项目的实践

### Catalog Context 的结构

```
contexts/catalog/
├── domain/
│   ├── product.py              # 聚合根
│   ├── category.py
│   └── ports/                  # 端口定义
│       └── repositories/
│
├── infrastructure/
│   ├── repositories/           # Repository 实现
│   └── models/                 # PO 模型
```

目前 Catalog 没有 Specification，如果要加，应该放在：
```
contexts/catalog/infrastructure/specifications/  # ✅ 查询规格
```

或者（如果需要业务规则）：
```
contexts/catalog/domain/specifications/  # ✅ 业务规则（不依赖框架）
```

## 🎯 总结和建议

### 当前问题
- ❌ `domain/specifications/order_spec.py` 依赖了持久化框架
- ❌ 违反了依赖倒置原则
- ❌ Domain 层不应该知道数据库查询的存在

### 推荐做法

**立即行动**：
1. 将 `order_spec.py` 移动到 `infrastructure/specifications/`
2. 重命名为 `order_query_spec.py`（更明确表达用途）
3. 更新所有导入语句

**可选**：
- 如果需要表达业务规则，在 `domain/specifications/` 创建纯业务规则类
- 命名为 `order_business_rules.py` 或类似名称

### 快速修复命令

```bash
# 1. 创建 infrastructure/specifications 目录
mkdir -p contexts/ordering/infrastructure/specifications

# 2. 移动文件
mv contexts/ordering/domain/specifications/order_spec.py \
   contexts/ordering/infrastructure/specifications/order_query_spec.py

# 3. 更新 __init__.py
# infrastructure/specifications/__init__.py
echo 'from .order_query_spec import OrderQuerySpec
__all__ = ["OrderQuerySpec"]' > contexts/ordering/infrastructure/specifications/__init__.py

# 4. 删除旧目录
rm -rf contexts/ordering/domain/specifications/
```

然后更新导入：
```python
# Before
from contexts.ordering.domain.specifications import OrderSpec

# After
from contexts.ordering.infrastructure.specifications import OrderQuerySpec as OrderSpec
# 或者
from contexts.ordering.infrastructure.specifications import OrderQuerySpec
```

## 🏛️ 六边形架构的黄金法则

1. **Domain 层**：
   - ✅ 不依赖任何外部框架
   - ✅ 只包含业务逻辑和业务概念
   - ✅ 定义接口（Ports），不依赖实现

2. **Infrastructure 层**：
   - ✅ 实现 Domain 层定义的接口
   - ✅ 可以依赖任何技术框架
   - ✅ 包含技术实现细节

3. **依赖方向**：
   ```
   Interface → Application → Domain ← Infrastructure
   （外层依赖内层，内层不知道外层）
   ```

遵循这些原则，代码将更：
- ✅ 易于测试（Domain 层可以完全隔离测试）
- ✅ 易于维护（技术更换不影响业务逻辑）
- ✅ 易于理解（清晰的层次边界）
