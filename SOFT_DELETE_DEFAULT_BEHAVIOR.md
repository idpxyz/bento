# Soft Delete Default Behavior - 设计决策

## 概述

本文档记录了 Bento 框架中 `EntitySpecificationBuilder` 软删除默认行为的设计决策。

## 设计原则

**安全优先（Secure by Default）**: `EntitySpecificationBuilder` 默认自动排除软删除的记录，防止意外查询到已删除的数据。

## API 设计

### 三种查询状态

```python
from bento.persistence.specification import EntitySpecificationBuilder

# 1. 默认：排除软删除记录（最常见的情况）
spec = EntitySpecificationBuilder().is_active().build()
# SQL: WHERE is_active = true AND deleted_at IS NULL

# 2. 包含软删除记录
spec = EntitySpecificationBuilder().is_active().include_deleted().build()
# SQL: WHERE is_active = true

# 3. 仅查询软删除记录
spec = EntitySpecificationBuilder().include_deleted().only_deleted().build()
# SQL: WHERE deleted_at IS NOT NULL
```

### 为什么不保留 `not_deleted()` 方法？

在设计审查中，我们考虑过保留 `not_deleted()` 方法以实现"向后兼容"，但最终决定移除它，理由如下：

1. **这是一个新项目** - 没有大量外部使用者需要兼容
2. **API 清晰性** - 避免冗余的 no-op 方法
3. **避免混淆** - 三个清晰的状态比四个方法更容易理解
4. **最佳时机** - 在项目早期统一 API，避免将来更大的破坏性变更

## 软删除机制统一

### 使用 `deleted_at` 时间戳

我们将软删除机制统一为只使用 `deleted_at` 时间戳字段：

- **`NULL`** = 记录未删除
- **`非 NULL`** = 记录已删除（保存删除时间）

**优点：**
- **数据完整性** - 同时记录状态和时间
- **避免冗余** - 不需要同时维护 `is_deleted` 和 `deleted_at`
- **查询灵活性** - 可以根据删除时间进行查询和统计
- **行业标准** - 主流框架（Laravel, Rails）的通用做法

## AggregateSpecificationBuilder 的特殊处理

`AggregateSpecificationBuilder` **不应用默认的软删除过滤器**，因为：

1. 聚合根通常使用事件溯源或其他模式
2. 聚合根的生命周期管理与普通实体不同
3. 如果特定聚合需要软删除，应该显式使用 `EntitySpecificationBuilder`

```python
from bento.persistence.specification import AggregateSpecificationBuilder

# 聚合根查询：无默认软删除过滤
spec = AggregateSpecificationBuilder().with_version(5).build()
# SQL: WHERE version = 5  (没有 deleted_at 过滤)
```

## 测试覆盖

### 单元测试 (40 个)
- ✅ `SpecificationBuilder` 基础功能
- ✅ `EntitySpecificationBuilder` 默认行为和方法
- ✅ `AggregateSpecificationBuilder` 版本控制

### 集成测试 (30 个)
- ✅ SQLAlchemy 集成
- ✅ 复杂查询场景
- ✅ 边界情况处理

**总计：70 个测试全部通过** ✓

## 文档更新

1. ✅ 更新 `/workspace/bento/docs/guides/SPECIFICATION_PATTERN.md`
   - 添加软删除默认行为的专门章节
   - 提供清晰的代码示例

2. ✅ 更新 `/workspace/bento/examples/specification_example.py`
   - 移除冗余的 `.not_deleted()` 调用
   - 添加注释说明默认行为

3. ✅ 更新所有测试
   - 反映新的默认行为
   - 调整断言以包含默认过滤器

## 迁移指南

如果你之前使用了 `.not_deleted()` 方法，迁移非常简单：

```python
# 之前
spec = EntitySpecificationBuilder().not_deleted().is_active().build()

# 现在（直接移除 .not_deleted()）
spec = EntitySpecificationBuilder().is_active().build()
# 默认行为已经排除软删除记录
```

## 决策依据

| 方面 | 选择 | 理由 |
|------|------|------|
| **默认行为** | 排除软删除 | 安全优先，符合大多数使用场景 |
| **API 方法** | 3 个方法（无 `not_deleted()`） | 简洁清晰，避免冗余 |
| **软删除字段** | 仅 `deleted_at` | 数据完整，避免冗余 |
| **聚合根** | 无默认过滤 | 符合 DDD 最佳实践 |
| **向后兼容** | 不考虑 | 新项目，追求 API 清晰性 |

## 参考

- **行业实践**: Laravel (deleted_at), Rails (deleted_at), Django (is_deleted)
- **安全原则**: Secure by Default, Fail-Safe Defaults
- **DDD**: Aggregate Root 生命周期管理

---

**创建日期**: 2025-11-06
**版本**: 1.0
**状态**: 已实现并测试通过

