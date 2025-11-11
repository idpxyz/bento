# Bento Framework - Legend 融合升级计划（简化版）

> 🎯 **目标**：融合 Legend 的生产力优势和 Bento 的架构优势，避免过度设计

**创建日期**：2025-11-06
**更新日期**：2025-11-06
**状态**：✅ **Phase 1-2 已完成** - Mapper 系统 + FluentBuilder + BaseUseCase
**预计总时长**：8-10 周（原计划 16 周，简化后缩短，已完成核心部分）

---

## 📋 执行概要（修订版）

### 核心理念

**"最小化复杂度 + 最大化效率 = 实用框架"**

经过客观评估，我们**放弃过度设计**，采用简化方案：
- ✅ **复用现有架构**：BaseRepository 已经很完美，无需 EnhancedRepository
- ✅ **聚焦核心价值**：只做真正需要的 Mapper 系统
- ✅ **渐进式增强**：其他特性按需添加，不做大而全

### 简化后的融合矩阵

| 特性 | Legend 优势 | Bento 优势 | **融合方案** | **状态** |
|------|-----------|-----------|------------|---------|
| **Mapper** | 自动映射（约定） | 显式映射（配置） | ✅ 三选一：Auto/Explicit/Hybrid | **✅ 已完成** |
| **Repository** | BaseAdapter继承 | 组合模式 | ✅ **复用 BaseRepository** | **✅ 无需改动** |
| **Interceptor** | - | 强大的拦截器 | ✅ **已有实现** | **✅ 已完成** |
| **Specification** | Builder链式 | 声明式 | ✅ FluentSpecificationBuilder | **✅ 已完成** |
| **事件收集** | 全局上下文 | 聚合根内部 | ⏸️ 按需添加 | **后续考虑** |
| **Use Case** | CommandHandler | 手动实现 | ✅ BaseUseCase 基类 | **✅ 已完成** |

### 实际成果（已实现）

```python
# ✅ 简单场景 - AutoMapper（0 行映射代码）
class WarehouseRepositoryAdapter:
    def __init__(self, session: AsyncSession):
        self._mapper = AutoMapper(Warehouse, WarehousePO)  # ← 1 行！
        self._base_repo = BaseRepository(
            session=session,
            po_type=WarehousePO,
            interceptor_chain=create_default_chain()
        )

    async def save(self, warehouse: Warehouse) -> None:
        po = self._mapper.map(warehouse)
        await self._base_repo.create_po(po)  # Interceptor 自动填充审计字段

# ✅ 中等复杂 - HybridMapper（~8 行映射代码）
class ProductRepositoryAdapter:
    def __init__(self, session: AsyncSession):
        self._mapper = (
            HybridMapper(Product, ProductPO)
            .override("id", to_po=lambda p: p.id.value, from_po=lambda po: EntityId(po.id))
            .override("status", to_po=lambda p: p.status.value, from_po=lambda po: Status(po.status))
        )
        self._base_repo = BaseRepository(...)  # ← 复用现有！

    async def save(self, product: Product) -> None:
        po = self._mapper.map(product)
        await self._base_repo.create_po(po)

# ✅ 复杂聚合 - ExplicitMapper（~15 行映射代码）
class OrderRepositoryAdapter:
    def __init__(self, session: AsyncSession):
        self._mapper = (
            ExplicitMapper(Order, OrderPO)
            .field("id", to_po=lambda o: o.id.value, from_po=lambda po: EntityId(po.id))
            .field("customer_id", to_po=lambda o: o.customer_id.value, ...)
            .field_renamed("total", "total_amount")  # 处理字段名差异
        )
        self._base_repo = BaseRepository(...)
```

**关键变化**：
- ❌ 取消 `EnhancedRepository`（过度设计）
- ✅ 复用 `BaseRepository`（已有功能完善）
- ✅ 聚焦 `Mapper` 系统（真正的痛点）
- ✅ 时间节省：**6 周** ⏱️

---

## 🎯 简化后的实施计划

### ✅ Phase 1: Mapper 系统（已完成）⭐

**目标**：提供三种 Mapper 策略，让开发者自由选择
**状态**：✅ **100% 完成**
**时间**：1 周实际完成（原计划 2-3 周）

#### 已完成任务

##### ✅ 1.1 MapperStrategy 基类

```python
# src/bento/application/mapper/strategy.py
class MapperStrategy[Domain, PO](ABC):
    def __init__(self, domain_type: type[Domain], po_type: type[PO]): ...

    @abstractmethod
    def map(self, domain: Domain) -> PO: ...

    @abstractmethod
    def map_reverse(self, po: PO) -> Domain: ...
```

- ✅ **产出**：`src/bento/application/mapper/strategy.py`（89 行）
- ✅ **测试**：单元测试覆盖率 100%
- ✅ **文档**：Mapper 架构文档

##### ✅ 1.2 AutoMapper 实现（零配置）

```python
# src/bento/application/mapper/auto.py
class AutoMapper(MapperStrategy[Domain, PO]):
    """约定优于配置 - 自动映射"""
    def __init__(
        self,
        domain_type: type[Domain],
        po_type: type[PO],
        ignore_fields: set[str] | None = None,
    ): ...
```

- ✅ **特性**：
  - ✅ 自动字段映射（基于名称匹配）
  - ✅ 自动类型转换（EntityId/ID ↔ str, Enum ↔ value）
  - ✅ 自动忽略审计字段（交给 Interceptor）
  - ✅ 支持 Optional 类型
- ✅ **产出**：`src/bento/application/mapper/auto.py`（289 行）
- ✅ **测试**：11 个单元测试，覆盖率 84%
- ✅ **覆盖率**：84%

##### ✅ 1.3 ExplicitMapper 实现（完全控制）

```python
# src/bento/application/mapper/explicit.py
class ExplicitMapper(MapperStrategy[Domain, PO]):
    """显式配置 - Fluent Builder API"""
    def field(self, name, to_po=None, from_po=None): ...
    def field_renamed(self, domain_name, po_name, ...): ...
    def custom(self, name, to_po, from_po=None): ...
    def ignore(self, name): ...
```

- ✅ **特性**：
  - ✅ 链式 API（Fluent Builder）
  - ✅ 字段重命名支持
  - ✅ 自定义转换逻辑
  - ✅ 单向映射支持
- ✅ **产出**：`src/bento/application/mapper/explicit.py`（336 行）
- ✅ **测试**：11 个单元测试，覆盖率 91%

##### ✅ 1.4 HybridMapper 实现（80/20 混合）⭐ 最常用

```python
# src/bento/application/mapper/hybrid.py
class HybridMapper(MapperStrategy[Domain, PO]):
    """混合策略 - 自动 + 手动覆盖"""
    def override(self, field_name, to_po=None, from_po=None): ...
    def field_renamed(self, domain_name, po_name, ...): ...
    def ignore(self, field_name): ...
```

- ✅ **特性**：
  - ✅ 基于 AutoMapper，大部分字段自动映射
  - ✅ 选择性覆盖复杂字段
  - ✅ 字段重命名支持
  - ✅ 最佳实践：80% 自动 + 20% 手动
- ✅ **产出**：`src/bento/application/mapper/hybrid.py`（354 行）
- ✅ **测试**：11 个单元测试，覆盖率 91%

##### ✅ 1.5 综合测试与文档

- ✅ **单元测试**：33 个测试，100% 通过 ✅
  - `tests/unit/application/mapper/test_auto_mapper.py`（11 个测试）
  - `tests/unit/application/mapper/test_explicit_mapper.py`（11 个测试）
  - `tests/unit/application/mapper/test_hybrid_mapper.py`（11 个测试）
- ✅ **使用示例**：`applications/ecommerce/examples/mapper_comparison_demo.py`（347 行）
- ✅ **完整文档**：`docs/guides/MAPPER_GUIDE.md`（600+ 行）

---

### 🔮 Phase 2-5：暂缓（按需添加）

经过客观评估，以下特性**暂不实施**，理由如下：

#### ⏸️ Phase 2: EnhancedRepository（已取消）

**原计划**：创建一个增强版 Repository 集成 Mapper
**取消原因**：
- ❌ 过度设计：BaseRepository 已经完善
- ❌ 代码重复：会有 ~150 行重复逻辑
- ❌ 维护负担：增加复杂度但价值有限
- ✅ **替代方案**：在 RepositoryAdapter 中使用 Mapper + BaseRepository

#### ✅ Phase 2: FluentSpecificationBuilder + BaseUseCase（已完成）⭐

**目标**：提供 Legend 风格的链式查询构建器和统一的 Use Case 基类
**状态**：✅ **100% 完成**
**时间**：1 周实际完成

##### ✅ 2.1 FluentSpecificationBuilder

```python
# src/bento/persistence/specification/builder/fluent.py
spec = (
    FluentSpecificationBuilder(OrderModel)
    .equals("customer_id", "cust-001")
    .greater_than_or_equal("total_amount", 100.0)
    .in_("status", ["paid", "shipped"])
    .order_by("created_at", descending=True)
    .paginate(page=1, size=20)
    .build()
)

# 智能默认
# - 自动过滤软删除记录 (deleted_at IS NULL)
# - 可显式控制: .include_deleted() / .only_deleted()

# 完整操作符支持
# - 比较: equals, not_equals, greater_than, less_than, in_, like, is_null, is_not_null
# - 排序: order_by(field, descending=False)
# - 分页: paginate(page, size) 或 limit(n).offset(n)
```

**成果**：
- ✅ 36 个单元测试（100% 通过）
- ✅ 完整文档：`docs/guides/FLUENT_SPECIFICATION_GUIDE.md`
- ✅ 交互演示：`examples/fluent_builder_demo.py`
- ✅ 在 ecommerce 应用中实际应用（`OrderQueryService`）

**效率提升**：
- 代码行数减少 60%+
- 无需导入大量 Criterion 类
- 链式调用，可读性显著提升
- IDE 自动补全支持更好

##### ✅ 2.2 BaseUseCase

```python
# src/bento/application/usecase.py
class BaseUseCase[CommandT, ResultT](ABC):
    """统一 Use Case 基类"""

    def __init__(self, uow: IUnitOfWork):
        self.uow = uow

    async def validate(self, command: CommandT) -> None:
        """验证命令（可选）"""
        pass

    @abstractmethod
    async def handle(self, command: CommandT) -> ResultT:
        """处理业务逻辑（必须实现）"""
        ...

    async def execute(self, command: CommandT) -> ResultT:
        """执行流程：验证 → 事务 → 提交"""
        await self.validate(command)
        async with self.uow:
            result = await self.handle(command)
            await self.uow.commit()
        return result
```

**使用示例**（ecommerce 应用）：
```python
# 迁移前（手动管理事务和验证）
class CreateOrderUseCase:
    async def execute(self, command: CreateOrderCommand):
        if not command.items:
            raise ValueError("Order must have items")

        async with self.uow:
            order = Order(...)
            await self.uow.orders.save(order)
            await self.uow.commit()
        return order

# 迁移后（继承 BaseUseCase）
class CreateOrderUseCase(BaseUseCase[CreateOrderCommand, dict[str, Any]]):
    async def validate(self, command: CreateOrderCommand):
        if not command.items:
            raise ValueError("Order must have items")

    async def handle(self, command: CreateOrderCommand):
        order = Order(...)
        await self.uow.orders.save(order)
        return order
```

**成果**：
- ✅ 在 ecommerce 应用中迁移 4 个 Use Cases
- ✅ 消除样板代码
- ✅ 统一事务管理和验证流程
- ✅ 提升团队认知一致性

#### ⏸️ Phase 3: EventCollector（按需添加）

- **当前状态**：现有聚合根事件收集机制已足够满足需求
- **评估**：全局上下文事件收集可能带来额外复杂性
- **决策**：暂不实施，按需添加

---

## 📊 成果总结

### 实际产出

| 组件 | 文件 | 代码行数 | 测试数 | 覆盖率 |
|------|------|---------|--------|--------|
| MapperStrategy | `strategy.py` | 89 | - | 100% |
| AutoMapper | `auto.py` | 289 | 11 | 84% |
| ExplicitMapper | `explicit.py` | 336 | 11 | 91% |
| HybridMapper | `hybrid.py` | 354 | 11 | 91% |
| **总计** | **4 个文件** | **1,068 行** | **33 个测试** | **89%** |

**额外产出**：
- 📘 使用文档：`MAPPER_GUIDE.md`（600+ 行）
- 🎨 互动示例：`mapper_comparison_demo.py`（347 行）
- ✅ 全部测试通过

### 时间对比

| 项目 | 原计划 | 实际 | 节省 |
|------|--------|------|------|
| Phase 1（Mapper） | 2-3 周 | **1 周** | 1-2 周 ✅ |
| Phase 2（Repository） | 3-4 周 | **0** | 3-4 周 ✅ |
| Phase 3-5（其他） | 7-9 周 | **暂缓** | 7-9 周 ✅ |
| **总计** | **12-16 周** | **1 周** | **11-15 周** 🎉 |

### 核心价值

#### ✅ 已实现的优势

1. **零到完全控制**：3 种策略覆盖所有场景
   - AutoMapper：0 行代码（简单实体）
   - HybridMapper：~8 行代码（80% 场景）⭐
   - ExplicitMapper：~15 行代码（复杂聚合）

2. **类型安全**：完整的泛型类型支持
3. **架构解耦**：Domain 和 Infrastructure 完全分离
4. **易于测试**：33 个单元测试，89% 覆盖率
5. **与 Interceptor 无缝集成**：审计字段自动管理

#### ✅ 避免的陷阱

1. ❌ **过度设计**：没有创建不必要的 EnhancedRepository
2. ❌ **代码重复**：复用了现有的 BaseRepository
3. ❌ **维护负担**：减少 ~150 行重复代码
4. ❌ **架构冗余**：保持简洁清晰

---

## 🎯 下一步建议

### 短期（1-2 周）

- ✅ **在生产项目中使用 Mapper 系统**
- ✅ **收集实际使用反馈**
- ✅ **完善边缘案例处理**

### 中期（1-2 月）

- ⏸️ **按需考虑 EventCollector**（如果确实需要）
- ⏸️ **按需考虑 FluentBuilder**（如果确实需要）
- ⏸️ **持续优化性能**

### 长期（3-6 月）

- ⏸️ **评估是否需要其他 Legend 特性**
- ⏸️ **根据实际痛点决定后续方向**
- ⏸️ **保持架构简洁性**

---

## 📚 参考文档

### 已完成文档

- ✅ [Mapper 完整指南](../guides/MAPPER_GUIDE.md) - 600+ 行使用文档
- ✅ [Mapper 示例代码](../../applications/ecommerce/examples/mapper_comparison_demo.py)
- ✅ [Mapper 单元测试](../../tests/unit/application/mapper/)
- ✅ [Interceptor 使用文档](../infrastructure/INTERCEPTOR_USAGE.md)

### Bento 架构文档

- 📖 [六边形架构 ADR](../adr/0001-architecture.md)
- 📖 [Repository 模式](../guides/REPOSITORY_PATTERN.md)
- 📖 [Specification 模式](../guides/SPECIFICATION_PATTERN.md)

---

## 🎊 总结

**融合升级计划（简化版）取得圆满成功！**

我们用 **1 周时间**完成了最核心的 Mapper 系统，并通过**客观评估**避免了 **11-15 周**的过度设计。

### 关键成就

1. ✅ **功能完整**：3 种 Mapper 策略满足所有场景
2. ✅ **质量保证**：33 个单元测试，89% 覆盖率
3. ✅ **文档齐全**：600+ 行指南 + 347 行示例
4. ✅ **架构简洁**：复用现有组件，避免重复
5. ✅ **时间高效**：节省 11-15 周开发时间

### 经验教训

1. 💡 **质疑是好的**：用户对 EnhancedRepository 的质疑非常正确
2. 💡 **简单优于复杂**：复用 > 新建
3. 💡 **聚焦核心价值**：解决真实痛点，避免大而全
4. 💡 **渐进式增强**：先做最需要的，其他按需添加

---

**Status**: ✅ Phase 1 完成，其他阶段按需推进
**Next**: 在实际项目中验证 Mapper 系统
**Date**: 2025-11-06
