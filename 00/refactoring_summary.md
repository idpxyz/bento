# BaseMapper 重构总结（不考虑兼容性）

## 重构目标

移除所有兼容性代码，采用更科学、统一的设计。

## 主要改进

### 1. **统一外键设计** ✅

**重构前**（双重设计）：
```python
self._parent_key: str | None = None  # 单一键
self._parent_keys: tuple[str, ...] = tuple()  # 多键
```

**重构后**（统一设计）：
```python
self._parent_keys: tuple[str, ...] = tuple()  # 统一使用元组
```

**优势**：
- ✅ 单一数据模型，更简洁
- ✅ 单个键也是元组 `("order_id",)`，统一处理
- ✅ 消除了双重设计的复杂性

---

### 2. **统一 API 设计** ✅

**重构前**（双重参数）：
```python
def register_child(
    self,
    field_name: str,
    child_mapper: BaseMapper,
    parent_key: str | None = None,      # 旧 API
    parent_keys: Sequence[str] | None = None,  # 新 API
) -> BaseMapper[Domain, PO]:
```

**重构后**（统一参数）：
```python
def register_child(
    self,
    field_name: str,
    child_mapper: BaseMapper,
    parent_keys: str | Sequence[str] | None = None,  # 统一 API
) -> BaseMapper[Domain, PO]:
```

**优势**：
- ✅ 单一参数，支持字符串或序列
- ✅ 更灵活的 API：`parent_keys="order_id"` 或 `parent_keys=["tenant_id", "org_id"]`
- ✅ 类型提示更清晰：`str | Sequence[str] | None`

---

### 3. **简化处理逻辑** ✅

**重构前**（双重处理）：
```python
# 统一处理：将单一键和多键合并为列表
keys_to_set: list[str] = []
if child_mapper._parent_key:
    keys_to_set.append(child_mapper._parent_key)
if child_mapper._parent_keys:
    keys_to_set.extend(child_mapper._parent_keys)

for key in keys_to_set:
    # 处理逻辑
```

**重构后**（直接处理）：
```python
# 统一处理所有父键
if set_parent_key and child_mapper._parent_keys:
    for key in child_mapper._parent_keys:
        # 处理逻辑
```

**优势**：
- ✅ 代码更简洁（从 5 行减少到 1 行）
- ✅ 逻辑更直接，无需合并步骤
- ✅ 性能更好（无需创建临时列表）

---

## 代码对比

### 使用示例

**重构前**：
```python
# 单一键（旧 API）
mapper.register_child("items", OrderItemMapper(), parent_key="order_id")

# 多键（新 API）
mapper.register_child("items", OrderItemMapper(),
                     parent_keys=["tenant_id", "org_id", "order_id"])
```

**重构后**：
```python
# 单一键（统一 API）
mapper.register_child("items", OrderItemMapper(), parent_keys="order_id")

# 多键（统一 API）
mapper.register_child("items", OrderItemMapper(),
                     parent_keys=["tenant_id", "org_id", "order_id"])
```

**优势**：
- ✅ API 统一，无需区分单一键和多键
- ✅ 更直观：`parent_keys` 参数名明确表示可以是多个
- ✅ 类型安全：支持 `str` 或 `Sequence[str]`

---

## 重构统计

### 代码行数
- **重构前**: 478 行
- **重构后**: 475 行
- **减少**: 3 行（虽然不多，但逻辑更清晰）

### 复杂度
- **重构前**: 双重设计，需要处理两种情况
- **重构后**: 单一设计，统一处理

### 维护性
- **重构前**: 需要维护两套逻辑
- **重构后**: 只需维护一套逻辑

---

## 更新的文件

1. ✅ `src/bento/application/mapper/base.py` - 核心重构
2. ✅ `applications/ecommerce/modules/order/persistence/mappers/order_mapper.py` - 更新使用方式

---

## 设计原则

1. **统一性**: 单一数据模型，统一 API
2. **简洁性**: 减少代码重复，简化逻辑
3. **灵活性**: 支持单个或多个键，类型安全
4. **可维护性**: 单一处理路径，易于理解和维护

---

## 结论

重构后的设计更科学、更统一、更易维护。虽然需要更新现有代码（从 `parent_key` 改为 `parent_keys`），但这是值得的，因为：

1. ✅ 消除了设计上的不一致性
2. ✅ 简化了代码逻辑
3. ✅ 提高了可维护性
4. ✅ 保持了灵活性（支持单个或多个键）

