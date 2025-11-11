# AutoMapper 实现对比分析

## 核心差异

### 1. **构造函数参数** ⭐⭐⭐

#### auto.py
```python
def __init__(
    self,
    domain_type: type[Domain],
    po_type: type[PO],
    *,
    include_none: bool = False,
    strict: bool = False,
    debug: bool = False,
    map_children_auto: bool = True,
) -> None:
    super().__init__(domain_type, po_type)  # 无法传递 BaseMapper 参数
```

#### auto_new.py
```python
def __init__(
    self,
    domain_type: type[Domain],
    po_type: type[PO],
    *,
    include_none: bool = False,
    strict: bool = False,
    debug: bool = False,
    map_children_auto: bool = True,
    default_id_type: type = ID,  # ✅ 新增
    id_factory: Callable[[str], Any] | None = None,  # ✅ 新增
    context=None,  # MappingContext | None  # ✅ 新增
) -> None:
    super().__init__(
        domain_type, po_type,
        default_id_type=default_id_type,
        id_factory=id_factory,
        context=context,
    )
```

**优势**: auto_new.py 可以透传 BaseMapper 的所有参数，支持自定义 ID 类型和 MappingContext

---

### 2. **类型分析能力** ⭐⭐⭐

#### auto.py
```python
@staticmethod
def _unwrap_optional(field_type: type) -> type:
    """只处理 Optional/Union[..., None]"""
    origin = get_origin(field_type)
    if origin is Union:
        args = [t for t in get_args(field_type) if t is not type(None)]
        return args[0] if args else field_type
    return field_type

def get_fields(klass: type) -> dict[str, type]:
    if is_dataclass(klass):
        for field in dataclass_fields(klass):
            fields_dict[field.name] = field.type  # ❌ 未规范化
```

#### auto_new.py
```python
@staticmethod
def _unwrap_annotated(t: type) -> type:
    """✅ 处理 Annotated 类型"""
    if get_origin(t) is Annotated:
        return get_args(t)[0]
    return t

@staticmethod
def _unwrap_optional(field_type: type) -> type:
    """✅ 先处理 Annotated，再处理 Optional"""
    field_type = TypeAnalyzer._unwrap_annotated(field_type)
    origin = get_origin(field_type)
    if origin is Union:
        args = [t for t in get_args(field_type) if t is not type(None)]
        return args[0] if args else field_type
    return field_type

def get_fields(klass: type) -> dict[str, type]:
    if is_dataclass(klass):
        d = {
            f.name: TypeAnalyzer._unwrap_optional(f.type)  # ✅ 规范化类型
            for f in dataclass_fields(klass)
            if isinstance(f.type, type) or isinstance(f.type, str)
        }
```

**优势**: auto_new.py 支持 `Annotated` 类型，并且规范化所有类型（unwrap optional）

---

### 3. **类型推断能力** ⭐⭐

#### auto.py
```python
def _infer_converters(self, domain_type: type, po_type: type):
    if self._analyzer.is_id_type(domain_type) and po_type is str:
        kind = "id"
    elif self._analyzer.is_enum_type(domain_type) and po_type is str:
        kind = "enum"  # ✅ 只支持 Enum ↔ str
    elif domain_type == po_type and self._analyzer.is_simple_type(domain_type):
        kind = "simple"
```

#### auto_new.py
```python
def _infer_converters(self, domain_type: type, po_type: type):
    d_unwrapped = unwrap(domain_type)  # ✅ 先 unwrap
    p_unwrapped = unwrap(po_type)

    if self._analyzer.is_id_type(d_unwrapped) and p_unwrapped is str:
        kind = "id"
    elif self._analyzer.is_enum_type(d_unwrapped) and p_unwrapped is str:
        kind = "enum"  # ✅ Enum ↔ str
    elif self._analyzer.is_enum_type(d_unwrapped) and p_unwrapped is int:
        kind = "enum_int"  # ✅ 新增：Enum ↔ int
    elif d_unwrapped == p_unwrapped and self._analyzer.is_simple_type(d_unwrapped):
        kind = "simple"
```

**优势**: auto_new.py 支持 Enum ↔ int 映射，并且先 unwrap 类型再判断

---

### 4. **错误处理** ⭐⭐

#### auto.py
```python
if self._map_children_auto and self._children:
    for field_name in self._children.keys():
        try:
            child_pos = self.map_children(domain, po, field_name)
            setattr(po, field_name, child_pos)
        except Exception:
            pass  # ❌ 静默忽略所有错误
```

#### auto_new.py
```python
if self._map_children_auto and self._children:
    for field_name in self._children.keys():
        try:
            child_pos = self.map_children(domain, po, field_name, set_parent_keys=True)
            setattr(po, field_name, child_pos)
        except Exception as e:
            if self._debug_enabled:
                self._logger.exception("map_children failed for '%s': %s", field_name, e)
            if self._strict:
                raise  # ✅ strict 模式抛出异常
```

**优势**: auto_new.py 提供更好的错误处理和调试支持

---

### 5. **类型参数语法** ⚠️

#### auto.py
```python
from typing import TypeVar
Domain = TypeVar("Domain")
PO = TypeVar("PO")

class AutoMapper[Domain, PO](BaseMapper[Domain, PO]):
    # 使用 PEP 695 语法，但需要 TypeVar
```

#### auto_new.py
```python
from typing import TypeVar
Domain = TypeVar("Domain")  # ⚠️ 冗余
PO = TypeVar("PO")  # ⚠️ 冗余

class AutoMapper[Domain, PO](BaseMapper[Domain, PO]):
    # 使用 PEP 695 语法，但还保留了 TypeVar（不一致）
```

**问题**: auto_new.py 保留了 TypeVar，但实际上 PEP 695 不需要它们

---

### 6. **代码质量**

| 方面 | auto.py | auto_new.py |
|------|---------|-------------|
| 代码行数 | 703 | 584 |
| 类型处理 | 基础 | 完善（Annotated, unwrap） |
| 错误处理 | 静默忽略 | 可配置（strict/debug） |
| BaseMapper 集成 | 不完整 | 完整 |
| 文档 | 详细 | 简洁 |

---

## 结论

### ✅ 推荐使用 `auto_new.py`（需要小修复）

**优势**:
1. ✅ 功能更完整（支持 BaseMapper 所有参数）
2. ✅ 类型处理更完善（Annotated, enum_int）
3. ✅ 错误处理更健壮（strict/debug 模式）
4. ✅ 代码更简洁（584 vs 703 行）

**需要修复**:
1. ⚠️ 移除冗余的 TypeVar（PEP 695 不需要）
2. ⚠️ 修复 context 参数的类型注解

### 修复建议

```python
# 移除 TypeVar（PEP 695 不需要）
# Domain = TypeVar("Domain")  # 删除
# PO = TypeVar("PO")  # 删除

# 修复 context 类型注解
from bento.application.mapper.base import MappingContext

def __init__(
    ...,
    context: MappingContext | None = None,  # 修复类型注解
) -> None:
```

