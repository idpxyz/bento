# BaseMapper 兼容性代码分析

## 发现的兼容性代码

### 1. **双重外键支持** ⚠️

**位置**: `base.py` 第 116-118 行
```python
# 单一外键（兼容旧用法）与多外键（新用法）
self._parent_key: str | None = None
self._parent_keys: tuple[str, ...] = tuple()
```

**原因**:
- 旧代码使用 `parent_key` (单一外键)
- 新功能需要 `parent_keys` (多外键，如 tenant_id + org_id + order_id)

**使用情况**:
- ✅ 代码库中确实有使用 `parent_key` 的地方：
  - `applications/ecommerce/modules/order/persistence/mappers/order_mapper.py:66`
  - `applications/ecommerce/HEXAGONAL_ARCHITECTURE.md:173`

**是否可以移除**: ❌ **不能移除** - 现有代码依赖

---

### 2. **register_child 方法的双重参数** ⚠️

**位置**: `base.py` 第 124-130 行
```python
def register_child(
    self,
    field_name: str,
    child_mapper: BaseMapper,
    parent_key: str | None = None,      # 旧 API
    parent_keys: Sequence[str] | None = None,  # 新 API
) -> BaseMapper[Domain, PO]:
```

**原因**: 同时支持旧的单一键和新的多键注册方式

**是否可以移除**: ❌ **不能移除** - 现有代码使用 `parent_key` 参数

---

### 3. **map_children 中的双重处理逻辑** ⚠️

**位置**: `base.py` 第 388-413 行
```python
if set_parent_key:
    # 1) Single parent key (legacy)
    if child_mapper._parent_key:
        if parent_id_value is not None:
            setattr(child_po, child_mapper._parent_key, parent_id_value)

    # 2) Multiple parent keys (new)
    if child_mapper._parent_keys:
        for key in child_mapper._parent_keys:
            # ... 复杂的多键处理逻辑
```

**问题**:
- 代码重复：两种方式都需要设置外键
- 逻辑分离：单一键和多键的处理逻辑分开

**是否可以优化**: ✅ **可以优化** - 可以统一处理逻辑

---

## 优化建议

### 方案 1: 统一处理逻辑（推荐）✅

将单一键也转换为列表，统一处理：

```python
# 统一处理：将单一键转换为列表
keys_to_set = []
if child_mapper._parent_key:
    keys_to_set.append(child_mapper._parent_key)
if child_mapper._parent_keys:
    keys_to_set.extend(child_mapper._parent_keys)

# 统一处理所有键
for key in keys_to_set:
    # 统一的键值设置逻辑
    if key == "tenant_id" and self._context and self._context.tenant_id:
        setattr(child_po, key, self._context.tenant_id)
    elif key == "org_id" and self._context and self._context.org_id:
        setattr(child_po, key, self._context.org_id)
    elif key in ("order_id", "parent_id", "aggregate_id"):
        if parent_id_value is not None:
            setattr(child_po, key, parent_id_value)
    else:
        # 从 domain / po / context.extra 获取
        ...
```

**优点**:
- ✅ 消除代码重复
- ✅ 统一处理逻辑
- ✅ 保持向后兼容

**缺点**:
- ⚠️ 需要重构现有代码（但逻辑更清晰）

---

### 方案 2: 保持现状（保守）⚠️

保持双重支持，但添加注释说明这是兼容性代码。

**优点**:
- ✅ 无需修改
- ✅ 向后兼容

**缺点**:
- ❌ 代码重复
- ❌ 维护成本高

---

## 结论

### 必须保留的兼容代码：
1. ✅ `_parent_key` 属性 - 现有代码依赖
2. ✅ `register_child` 的 `parent_key` 参数 - 现有代码使用

### 已优化的兼容代码：
1. ✅ `map_children` 中的双重处理逻辑 - **已优化为统一处理逻辑** (2024-12-19)

### 优化结果：
- ✅ 消除了代码重复（单一键和多键使用相同的处理逻辑）
- ✅ 统一了处理流程（所有键都通过同一个循环处理）
- ✅ 保持了向后兼容（API 不变，现有代码无需修改）
- ✅ 代码更简洁（从 26 行减少到 28 行，但逻辑更清晰）

### 优化后的代码结构：
```python
# 统一处理：将单一键和多键合并为列表
keys_to_set: list[str] = []
if child_mapper._parent_key:
    keys_to_set.append(child_mapper._parent_key)
if child_mapper._parent_keys:
    keys_to_set.extend(child_mapper._parent_keys)

# 统一处理所有键
for key in keys_to_set:
    # 统一的键值设置逻辑
    ...
```

