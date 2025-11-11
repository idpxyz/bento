# BaseMapper 实现对比分析

## 文件概览
- `base.py`: 原始实现（292 行）
- `base_new.py`: 增强实现（245 行）

---

## 核心差异对比

### 1. **构造函数增强** ⭐⭐⭐

#### base.py
```python
def __init__(self, domain_type: type[Domain], po_type: type[PO]) -> None:
    super().__init__(domain_type, po_type)
    self._children: dict[str, BaseMapper] = {}
    self._parent_key: str | None = None
```

#### base_new.py
```python
def __init__(
    self,
    domain_type: type[Domain],
    po_type: type[PO],
    *,
    default_id_type: type = ID,
    id_factory: Callable[[str], Any] | None = None,
    context: MappingContext | None = None,
) -> None:
    super().__init__(domain_type, po_type)
    self._children: dict[str, BaseMapper] = {}
    self._parent_key: str | None = None
    self._parent_keys: tuple[str, ...] = tuple()  # 新增：多外键支持

    self._default_id_type = default_id_type  # 新增：可配置 ID 类型
    self._id_factory = id_factory  # 新增：自定义 ID 工厂
    self._context = context  # 新增：映射上下文
```

**优势**:
- ✅ 支持自定义 ID 类型（如 `OrderId`, `CustomerId`）
- ✅ 支持映射上下文（tenant_id, org_id 等）
- ✅ 更灵活的扩展性

---

### 2. **多外键支持** ⭐⭐⭐

#### base.py
```python
# 只支持单一外键
self._parent_key: str | None = None

def register_child(
    self, field_name: str, child_mapper: "BaseMapper", parent_key: str | None = None
) -> "BaseMapper[Domain, PO]":
    if parent_key:
        child_mapper._parent_key = parent_key
```

#### base_new.py
```python
# 支持单一和多外键
self._parent_key: str | None = None
self._parent_keys: tuple[str, ...] = tuple()

def register_child(
    self,
    field_name: str,
    child_mapper: BaseMapper,
    parent_key: str | None = None,
    parent_keys: Sequence[str] | None = None,  # 新增
) -> BaseMapper[Domain, PO]:
    if parent_key:
        child_mapper._parent_key = parent_key
    if parent_keys:  # 新增
        child_mapper._parent_keys = tuple(parent_keys)
```

**优势**:
- ✅ 支持多租户场景（tenant_id + org_id + order_id）
- ✅ 更复杂的层级关系支持

---

### 3. **ID 转换增强** ⭐⭐

#### base.py
```python
def convert_str_to_id(self, str_value: str | None, id_type: type = ID) -> EntityId | ID | None:
    if str_value is None:
        return None
    if id_type == EntityId or id_type.__name__ == "EntityId":
        return EntityId(str_value)
    return ID(str_value)
```

#### base_new.py
```python
def convert_str_to_id(
    self,
    str_value: str | None,
    id_type: type | None = None,  # 可选参数
) -> EntityId | ID | Any | None:
    if str_value is None:
        return None
    if id_type is not None:
        return self._construct_id(id_type, str_value)
    if self._id_factory is not None:  # 优先使用工厂
        return self._id_factory(str_value)
    return self._construct_id(self._default_id_type, str_value)  # 使用默认类型

@staticmethod
def _construct_id(id_cls: type, raw: str) -> Any:
    if id_cls in (EntityId, ID):
        return id_cls(raw)
    return id_cls(raw)  # 支持自定义 XxxId(str)
```

**优势**:
- ✅ 支持自定义 ID 类型（如 `OrderId`, `CustomerId`）
- ✅ 支持 ID 工厂函数
- ✅ 优先级：`id_type` > `id_factory` > `default_id_type`

---

### 4. **Enum 错误信息增强** ⭐

#### base.py
```python
def convert_str_to_enum(self, str_value: str | None, enum_type: type[Enum]) -> Enum | None:
    try:
        return enum_type(str_value)
    except ValueError:
        try:
            return enum_type[str_value]
        except KeyError as e:
            raise ValueError(f"Invalid enum '{enum_type.__name__}': {str_value}") from e
```

#### base_new.py
```python
def convert_str_to_enum(self, str_value: str | None, enum_type: type[Enum]) -> Enum | None:
    try:
        return enum_type(str_value)
    except ValueError:
        try:
            return enum_type[str_value]
        except KeyError as e:
            allowed_values = ", ".join(repr(m.value) for m in enum_type)
            allowed_names = ", ".join(m.name for m in enum_type)
            raise ValueError(
                f"Invalid {enum_type.__name__}: {str_value!r}. "
                f"Allowed values: [{allowed_values}]; names: [{allowed_names}]"
            ) from e
```

**优势**:
- ✅ 更详细的错误信息，显示所有允许的值和名称
- ✅ 更好的调试体验

---

### 5. **批量映射方法** ⭐⭐

#### base.py
❌ 无批量方法

#### base_new.py
```python
def map_list(self, domains: Iterable[Domain]) -> list[PO]:
    return [self.map(d) for d in domains]

def map_reverse_list(self, pos: Iterable[PO], *, with_events: bool = True) -> list[Domain]:
    if with_events:
        return [self.map_reverse_with_events(po) for po in pos]
    return [self.map_reverse(po) for po in pos]
```

**优势**:
- ✅ 便捷的批量转换
- ✅ 可选的自动清理事件

---

### 6. **模板方法模式** ⭐⭐

#### base.py
```python
# 需要手动调用
def map_reverse(self, po: PO) -> Domain:
    # 实现...
    self.auto_clear_events(domain)  # 需要手动调用
    return domain
```

#### base_new.py
```python
# 提供模板方法
def map_reverse_with_events(self, po: PO) -> Domain:
    """Recommended entry-point for PO -> Domain mapping."""
    d = self.map_reverse(po)
    self.auto_clear_events(d)
    return d
```

**优势**:
- ✅ 强制事件清理，避免遗漏
- ✅ 更清晰的 API 设计

---

### 7. **映射上下文支持** ⭐⭐⭐

#### base.py
❌ 无上下文支持

#### base_new.py
```python
@dataclass(slots=True)
class MappingContext:
    tenant_id: str | None = None
    org_id: str | None = None
    actor_id: str | None = None
    extra: dict[str, Any] | None = None

# 在 map_children 中使用
if key == "tenant_id" and self._context and self._context.tenant_id:
    setattr(child_po, key, self._context.tenant_id)
elif key == "org_id" and self._context and self._context.org_id:
    setattr(child_po, key, self._context.org_id)
# ...
```

**优势**:
- ✅ 支持多租户场景
- ✅ 自动传播上下文信息（tenant_id, org_id 等）
- ✅ 可扩展的 extra 字段

---

### 8. **子实体映射增强** ⭐⭐

#### base.py
```python
def map_children(
    self, domain: Domain, po: PO, field_name: str, set_parent_key: bool = True
) -> list[Any]:
    # 只支持单一 parent_key
    if set_parent_key and child_mapper._parent_key:
        setattr(child_po, child_mapper._parent_key, parent_id_value)
```

#### base_new.py
```python
def map_children(
    self,
    domain: Domain,
    po: PO,
    field_name: str,
    *,
    set_parent_keys: bool = True,  # 参数名更清晰
) -> list[Any]:
    # 支持单一和多外键
    if child_mapper._parent_key:
        # 单一外键逻辑
    if child_mapper._parent_keys:
        # 多外键逻辑，支持从 context 获取
```

**优势**:
- ✅ 支持多外键场景
- ✅ 自动从 context 获取 tenant_id, org_id
- ✅ 更灵活的键值来源（domain / po / context.extra）

---

## 功能对比表

| 功能 | base.py | base_new.py |
|------|---------|-------------|
| 单一外键支持 | ✅ | ✅ |
| 多外键支持 | ❌ | ✅ |
| 自定义 ID 类型 | ❌ | ✅ |
| ID 工厂函数 | ❌ | ✅ |
| 映射上下文 | ❌ | ✅ |
| 批量映射方法 | ❌ | ✅ |
| 模板方法（事件清理） | ❌ | ✅ |
| Enum 详细错误信息 | ❌ | ✅ |
| 文档完整性 | ✅ | ⚠️ (较简洁) |

---

## 使用场景对比

### base.py 适合：
- ✅ 简单的单租户应用
- ✅ 单一外键关系
- ✅ 标准 ID/EntityId 类型
- ✅ 不需要批量操作

### base_new.py 适合：
- ✅ 多租户 SaaS 应用
- ✅ 复杂的外键关系（多键）
- ✅ 自定义 ID 类型（强类型）
- ✅ 需要批量操作
- ✅ 需要上下文传播（tenant_id, org_id 等）

---

## 建议

### 推荐使用 `base_new.py`，因为：
1. **向后兼容**: 保留了所有 base.py 的功能
2. **功能更强大**: 多外键、上下文、自定义 ID
3. **更现代**: 使用 PEP 695 类型参数
4. **更灵活**: 支持复杂业务场景

### 迁移建议：
1. 逐步迁移现有 mapper 到 base_new.py
2. 利用新特性（如 MappingContext）优化多租户场景
3. 使用自定义 ID 类型增强类型安全

---

## 代码质量对比

| 方面 | base.py | base_new.py |
|------|---------|-------------|
| 代码行数 | 292 | 245 |
| 文档注释 | 详细 | 简洁 |
| 类型提示 | ✅ | ✅ |
| 可扩展性 | 中等 | 高 |
| 复杂度 | 低 | 中高 |

