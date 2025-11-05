# Phase 3: Mapper 系统 - 启动指南

**阶段**: Phase 3 - Mapper 系统  
**预计时长**: 2-3 周  
**开始时间**: 2025-11-04  
**状态**: 🟡 准备开始  

---

## 🎯 阶段目标

迁移对象映射系统，实现 Domain ↔ DTO ↔ PO 之间的类型安全转换。

**核心价值**:
- ✅ 类型安全的对象转换
- ✅ 自动映射支持（减少样板代码）
- ✅ 自定义映射支持（复杂场景）
- ✅ 可组合的映射策略
- ✅ Registry 管理映射器

---

## 📊 当前状态

### ✅ 已完成的基础

- ✅ **Mapper Protocol** (`application/ports/mapper.py`)
  - `Mapper`, `BidirectionalMapper`, `CollectionMapper`, `BidirectionalCollectionMapper`

- ✅ **POMapper 基础实现** (`infrastructure/mapper/po_mapper.py`)
  - 基础的 AR ↔ PO 映射
  - 自动映射支持
  - 自定义映射重写点

### 🎯 需要完善

- ⏳ **高级映射策略** (AutoMapping, CompositeMapping)
- ⏳ **Mapper Registry** (注册表管理)
- ⏳ **Mapper Builder** (流式 API)
- ⏳ **DTO/VO Mapper** (应用层映射)
- ⏳ **类型转换器** (ValueObject, 嵌套对象)

---

## 📋 任务清单

### 3.1 Mapper Core 增强（1 周）

#### Task 3.1.1: 映射策略实现

**文件**: `src/infrastructure/mapper/core/strategies.py`

**参考**: `old/infrastructure/mapper/core/strategies.py`

**需要实现**:
- ✅ `AutoMappingStrategy`: 自动字段映射
- ✅ `ExplicitMappingStrategy`: 显式字段映射
- ✅ `CustomMappingStrategy`: 自定义转换函数
- ✅ `CompositeMappingStrategy`: 组合多种策略

**要求**:
```python
class AutoMappingStrategy:
    """基于字段名自动映射"""
    def map(self, source: Any, target_type: type) -> Any: ...

class CompositeMappingStrategy:
    """组合多种策略"""
    def add_strategy(self, strategy: MappingStrategy) -> None: ...
    def map(self, source: Any, target_type: type) -> Any: ...
```

#### Task 3.1.2: 映射上下文

**文件**: `src/infrastructure/mapper/core/context.py`

**功能**:
- 映射上下文管理
- 循环引用检测
- 嵌套映射支持
- 映射缓存

#### Task 3.1.3: 类型转换器

**文件**: `src/infrastructure/mapper/core/converter.py`

**功能**:
- ValueObject 转换 (`.value` 提取)
- 日期时间转换
- 枚举转换
- 集合转换 (List, Dict, Set)

---

### 3.2 Mapper Registry 和 Builder（1 周）

#### Task 3.2.1: Mapper Registry

**文件**: `src/infrastructure/mapper/registry/`

**参考**: `old/infrastructure/mapper/registry/`

**需要实现**:
- ✅ `MapperRegistry`: 全局映射器注册表
- ✅ `POMapperRegistry`: PO 映射器注册表
- ✅ `DTOMapperRegistry`: DTO 映射器注册表
- ✅ `VOMapperRegistry`: VO 映射器注册表

**使用示例**:
```python
from infrastructure.mapper.registry import MapperRegistry

# 注册映射器
MapperRegistry.register(User, UserPO, UserPOMapper())

# 获取映射器
mapper = MapperRegistry.get_mapper(User, UserPO)
```

#### Task 3.2.2: Mapper Builder

**文件**: `src/infrastructure/mapper/builder.py`

**参考**: `old/infrastructure/mapper/core/mapper.py` (MapperBuilder)

**需要实现**:
- ✅ 流式 API 构建映射器
- ✅ 字段映射配置
- ✅ 自定义转换函数
- ✅ 忽略字段

**使用示例**:
```python
from infrastructure.mapper import MapperBuilder

mapper = (MapperBuilder.for_types(User, UserDTO)
    .map("id", "user_id")
    .map("email", "email_address")
    .map_custom("full_name", lambda u: f"{u.first_name} {u.last_name}")
    .ignore("password")
    .build())
```

---

### 3.3 DTO/PO/VO Base Classes（1 周）

#### Task 3.3.1: DTO Base

**文件**: `src/infrastructure/mapper/dto/base.py`

**参考**: `old/infrastructure/mapper/dto/base.py`

**功能**:
- DTO 基类定义
- 序列化支持
- 验证支持

#### Task 3.3.2: VO Base

**文件**: `src/infrastructure/mapper/vo/base.py`

**参考**: `old/infrastructure/mapper/vo/base.py`

**功能**:
- VO 映射器基类
- 值对象转换支持

---

### 3.4 增强 POMapper（可选）

#### Task 3.4.1: 集成高级策略

**文件**: `src/infrastructure/mapper/po_mapper.py` (增强)

**功能**:
- 集成 `AutoMappingStrategy`
- 集成 `CompositeMappingStrategy`
- 支持嵌套对象映射
- 支持集合映射

---

## 🎯 优先级排序

### 高优先级 ⭐⭐⭐⭐⭐

1. **映射策略** (Task 3.1.1)
   - 核心功能，其他组件依赖
   - 工作量：3-4 天

2. **Mapper Builder** (Task 3.2.2)
   - 提升开发体验
   - 工作量：2-3 天

### 中优先级 ⭐⭐⭐⭐

3. **Mapper Registry** (Task 3.2.1)
   - 便于管理映射器
   - 工作量：2 天

4. **类型转换器** (Task 3.1.3)
   - 处理复杂类型转换
   - 工作量：2-3 天

### 低优先级 ⭐⭐⭐

5. **映射上下文** (Task 3.1.2)
   - 处理循环引用等高级场景
   - 工作量：1-2 天

6. **DTO/VO Base** (Task 3.3)
   - 应用层映射（可选）
   - 工作量：2-3 天

---

## 📁 目标目录结构

```
src/infrastructure/mapper/
├── __init__.py
├── po_mapper.py          # ✅ 已存在（基础实现）
├── core/
│   ├── __init__.py
│   ├── strategies.py     # ⏳ 映射策略
│   ├── context.py        # ⏳ 映射上下文
│   └── converter.py     # ⏳ 类型转换器
├── registry/
│   ├── __init__.py
│   ├── base.py           # ⏳ 基础注册表
│   ├── po.py             # ⏳ PO 映射器注册表
│   ├── dto.py            # ⏳ DTO 映射器注册表
│   └── vo.py             # ⏳ VO 映射器注册表
├── builder.py            # ⏳ Mapper Builder
├── dto/
│   ├── __init__.py
│   └── base.py           # ⏳ DTO 基类
└── vo/
    ├── __init__.py
    └── base.py           # ⏳ VO 基类
```

---

## 💡 实现建议

### 第一步：映射策略（核心）

**为什么先做**:
- 这是 Mapper 的核心功能
- POMapper 可以立即增强
- 其他功能依赖它

**实现顺序**:
1. `AutoMappingStrategy` (最简单)
2. `ExplicitMappingStrategy`
3. `CustomMappingStrategy`
4. `CompositeMappingStrategy`

### 第二步：Mapper Builder

**为什么第二步**:
- 提升开发体验
- 使映射器创建更简单
- 依赖策略实现

### 第三步：Registry 和其他

**为什么最后**:
- 增强功能
- 可以逐步完善

---

## 📚 参考资源

### Old 系统参考

- `old/infrastructure/mapper/core/strategies.py` - 策略实现
- `old/infrastructure/mapper/core/mapper.py` - Builder 实现
- `old/infrastructure/mapper/registry/` - Registry 实现
- `old/infrastructure/mapper/po/base.py` - POMapper 参考

### 文档参考

- `docs/design/ADAPTER_MAPPER_DESIGN.md` - 架构设计
- `docs/design/ADAPTER_MAPPER_COMPLETE.md` - 完成报告

---

## ✅ 检查清单

### Phase 3 开始前

- [x] Phase 2 核心功能完成
- [x] Mapper Protocol 已定义
- [x] POMapper 基础实现完成
- [ ] 阅读 old 系统的 Mapper 实现
- [ ] 理解映射策略的工作原理

### Phase 3 进行中

- [ ] 实现映射策略
- [ ] 实现 Mapper Builder
- [ ] 实现 Mapper Registry
- [ ] 增强 POMapper
- [ ] 编写单元测试
- [ ] 编写使用示例

### Phase 3 完成标准

- [ ] 所有核心功能实现
- [ ] 单元测试覆盖率 > 80%
- [ ] 文档完整
- [ ] 使用示例可用

---

## 🎯 预期成果

### 完成后的能力

- ✅ **自动映射**: 简单场景零配置
- ✅ **自定义映射**: 复杂场景灵活配置
- ✅ **流式 API**: Builder 模式，代码简洁
- ✅ **Registry 管理**: 全局映射器管理
- ✅ **类型安全**: 完整的类型注解
- ✅ **性能优化**: 映射缓存、批量转换

### 使用体验

```python
# 简单场景：自动映射
class UserPOMapper(POMapper[User, UserPO]):
    def __init__(self):
        super().__init__(User, UserPO, auto_map=True)

# 复杂场景：Builder
mapper = (MapperBuilder.for_types(Order, OrderDTO)
    .map("id", "order_id")
    .map_custom("total", lambda o: o.calculate_total())
    .build())

# Registry 管理
MapperRegistry.register(User, UserPO, mapper)
mapper = MapperRegistry.get_mapper(User, UserPO)
```

---

## 📝 总结

### 关键要点

1. **已有基础**: POMapper 基础实现已完成
2. **核心任务**: 映射策略和 Builder
3. **循序渐进**: 从简单到复杂
4. **质量保证**: 测试和文档并重

### 下一步行动

**立即开始**: Task 3.1.1 - 映射策略实现

**理由**:
- 这是核心功能
- 其他组件依赖它
- 可以立即增强 POMapper

---

**准备开始 Phase 3！** 🚀

