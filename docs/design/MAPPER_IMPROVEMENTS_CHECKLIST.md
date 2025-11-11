# Mapper 实现改进点检查清单

## 📋 问题状态总览

| 优先级 | 问题 | 状态 | 说明 |
|--------|------|------|------|
| **A. 高优先级** | | | |
| 1 | dataclass 字段反射"误过滤" | ✅ **已修复** | 已移除 isinstance 过滤 |
| 2 | `get_type_hints` 命名空间 | ✅ **已修复** | 已使用模块命名空间 |
| 3 | `register_child` 不污染子 mapper | ✅ **已解决** | 已改为父 mapper 持有 |
| 4 | Enum 解析错误信息 | ✅ **已解决** | 已输出允许值/名称 |
| 5 | ID 策略一致性 | ✅ **已解决** | 优先级清晰 |
| **B. 中优先级** | | | |
| 6 | `MappingContext.extra` 默认值 | ✅ **已解决** | 已改为 `field(default_factory=dict)` |
| 7 | children 多外键回填的兜底策略 | ✅ **已解决** | 已有 try-except 容错 |
| 8 | "简单类型"白名单可扩展 | ✅ **已扩展** | 已添加 datetime/date/UUID/Decimal |
| 9 | 构造回退策略抽象 | ✅ **已抽象** | 已添加 _instantiate_po/_instantiate_domain |
| 10 | TypeVar 显式声明 | ⚠️ **部分解决** | 使用 PEP 695 语法 |
| 11 | 缓存线程安全 | ⚠️ **待评估** | 类级 dict，高并发可能有问题 |
| **C. 低优先级** | | | |
| 12 | `strict/debug` 的行为矩阵文档化 | ❌ **待完善** | 需要文档 |
| 13 | 字段级 override 的 ergonomics | ❌ **待改进** | 当前 API 可用但可优化 |
| 14 | 匹配建议器（strict+whitelist） | ✅ **已实现** | 已有 `_suggest_po_candidates` |
| 15 | 观察性（Logging 域） | ⚠️ **部分实现** | debug 模式有日志但可增强 |
| 16 | 文档与示例 | ⚠️ **部分完成** | 有文档但可补充示例 |

---

## A. 高优先级（需要立即修复）

### 1. dataclass 字段反射"误过滤" ❌

**问题**:
```python
# 当前实现 (auto.py:87)
if isinstance(f.type, type) or isinstance(f.type, str)
```

这会过滤掉 `Optional[List[Item]]`、`Annotated[ID, ...]` 等 typing 类型。

**修复方案**:
```python
# 修复后
if is_dataclass(klass):
    fields_dict = {
        f.name: TypeAnalyzer._unwrap_optional(f.type)  # type: ignore[arg-type]
        for f in dataclass_fields(klass)
        # 移除 isinstance 过滤，统一在 _unwrap_optional 中处理
    }
    cache[klass] = fields_dict
    return fields_dict
```

**验收**: 含 `Optional[List[Item]]` / `Annotated[ID, ...]` 的字段能正确映射。

---

### 2. `get_type_hints` 命名空间 ❌

**问题**:
```python
# 当前实现 (auto.py:94)
hints = get_type_hints(klass, globalns=getattr(klass, "__dict__", {}), localns=None)
```

`ForwardRef` 和延迟注解可能解析失败。

**修复方案**:
```python
# 修复后
import sys
try:
    globalns = vars(sys.modules[klass.__module__])
    hints = get_type_hints(klass, globalns=globalns, localns=None)
    if hints:
        normalized = {k: TypeAnalyzer._unwrap_optional(v) for k, v in hints.items()}
        cache[klass] = normalized
        return normalized
except Exception:
    pass
```

**验收**: 含 `from __future__ import annotations`、跨模块类型别名、ForwardRef 的类能正确解析。

---

### 3. `register_child` 不污染子 mapper ✅

**状态**: ✅ **已解决**

**实现**:
- `parent_keys` 存储在父 mapper 的 `_child_parent_keys` 中
- 提供 `child_parent_keys(field_name)` 只读接口
- 同一子 mapper 可被多个父 mapper 复用

**验收**: ✅ 通过

---

### 4. Enum 解析错误信息 ✅

**状态**: ✅ **已解决**

**实现** (base.py:250+):
```python
allowed_values = ", ".join(repr(m.value) for m in enum_type)
allowed_names = ", ".join(m.name for m in enum_type)
raise ValueError(
    f"Invalid {enum_type.__name__}: {str_value!r}. "
    f"Allowed values: [{allowed_values}]; names: [{allowed_names}]"
) from e
```

**验收**: ✅ 通过

---

### 5. ID 策略一致性 ✅

**状态**: ✅ **已解决**

**实现** (base.py:convert_str_to_id):
- 优先级: `id_type > id_factory > default_id_type`
- 支持自定义 `XxxId(str)` 类型

**验收**: ✅ 通过

---

## B. 中优先级（稳健性/易用性）

### 6. `MappingContext.extra` 默认值 ✅

**状态**: ✅ **已解决**

**实现** (base.py:60+):
```python
extra: dict[str, Any] = field(default_factory=dict)
```

**验收**: ✅ 通过

---

### 7. children 多外键回填的兜底策略 ✅

**状态**: ✅ **已解决**

**实现** (base.py:map_children):
```python
try:
    setattr(child_po, key, value)
except (AttributeError, TypeError, ValueError):
    # ORM 只读/延迟属性或类型不匹配等，保持容错
    pass
```

**验收**: ✅ 通过

---

### 8. "简单类型"白名单可扩展 ⚠️

**问题**:
```python
# 当前实现 (auto.py:145)
def is_simple_type(field_type: type) -> bool:
    return field_type in (str, int, float, bool, bytes)
```

缺少 `datetime`、`date`、`UUID`、`Decimal` 等常见类型。

**改进方案**:
```python
# 方案 1: 扩展白名单
def is_simple_type(field_type: type) -> bool:
    simple_types = (str, int, float, bool, bytes, datetime, date, UUID, Decimal)
    return field_type in simple_types

# 方案 2: 可配置白名单（更灵活）
class TypeAnalyzer:
    _simple_type_whitelist: ClassVar[set[type]] = {str, int, float, bool, bytes}

    @classmethod
    def register_simple_type(cls, typ: type) -> None:
        cls._simple_type_whitelist.add(typ)
```

**验收**: `datetime`、`UUID` 等类型能直接映射，无需 override。

---

### 9. 构造回退策略抽象 ⚠️

**当前实现** (auto.py:550+):
```python
try:
    po = self._po_type(**po_dict)
except TypeError:
    po = self._po_type()
    for k, v in po_dict.items():
        setattr(po, k, v)
```

**改进方案**:
```python
def _instantiate_po(self, po_dict: dict[str, Any]) -> PO:
    """Instantiate PO object with fallback strategy.

    Override this method to customize instantiation logic.
    """
    try:
        return self._po_type(**po_dict)
    except TypeError:
        # Fallback: no-arg constructor + setattr
        po = self._po_type()
        for k, v in po_dict.items():
            setattr(po, k, v)
        return po
```

**验收**: 替换为 Pydantic `model_construct` 或其他工厂方法时，只需重写此方法。

---

### 10. TypeVar 显式声明 ⚠️

**当前实现**: 使用 PEP 695 语法 `class AutoMapper[Domain, PO]`

**评估**: ✅ **合理** - PEP 695 是 Python 3.12+ 的现代语法，无需显式 TypeVar。

**注意**: 如果需要在方法签名中单独使用，可能需要：
```python
from typing import TypeVar
Domain = TypeVar("Domain")
PO = TypeVar("PO")
```

**验收**: mypy/pyright 无告警即可。

---

### 11. 缓存线程安全 ⚠️

**当前实现**:
```python
_fields_cache: ClassVar[dict[type, dict[str, type]]] = {}
_converter_kind_cache: ClassVar[dict[tuple[type, type], str]] = {}
```

**评估**:
- 对于大多数 Web 服务，类级 dict 的读写操作在 Python GIL 下是安全的
- 高并发场景下，理论上存在竞态，但实际影响很小
- 如果需要，可以使用 `functools.lru_cache` 或 `threading.RLock`

**建议**: 先观察，如有问题再优化。

---

## C. 低优先级（体验/可观测性）

### 12. `strict/debug` 的行为矩阵文档化 ❌

**需要补充文档**:
```markdown
| 场景 | strict=False, debug=False | strict=False, debug=True | strict=True, debug=False | strict=True, debug=True |
|------|---------------------------|--------------------------|--------------------------|-------------------------|
| 字段缺失 | 静默忽略 | 记录日志 | 抛出错误（whitelist时） | 抛出错误 + 日志 |
| 类型不匹配 | 静默失败 | 记录日志 | 抛出错误 | 抛出错误 + 日志 |
| 只读字段 | 静默忽略 | 记录日志 | 抛出错误 | 抛出错误 + 日志 |
```

---

### 13. 字段级 override 的 ergonomics ❌

**当前 API**:
```python
mapper.override_field("status", to_po=lambda s: s.value, from_po=lambda v: OrderStatus(v))
```

**改进方案**:
```python
# 便捷方法
mapper.override_enum("status", OrderStatus, as="str")  # 或 "int"
mapper.override_id("order_id", OrderId)  # 或 id_factory
```

---

### 14. 匹配建议器 ✅

**状态**: ✅ **已实现**

**实现**: `_suggest_po_candidates()` 方法在 strict 模式下提供候选字段。

---

### 15. 观察性（Logging） ⚠️

**当前实现**: debug 模式有基本日志。

**改进方案**:
```python
if self._debug_enabled:
    self._logger.debug(
        "AutoMapper: field '%s' converter: %s (domain: %s -> po: %s)",
        field_name, converter_kind, domain_type, po_type
    )
```

---

### 16. 文档与示例 ⚠️

**需要补充**:
- `Optional[List[Item]]` 映射示例
- `Enum↔int` 映射示例
- 多外键（tenant/org/order）完整示例
- 构造回退场景示例

---

## 🔧 修复优先级建议

### 立即修复（A.1, A.2）
1. ✅ 修复 dataclass 字段反射过滤
2. ✅ 修复 `get_type_hints` 命名空间

### 近期改进（B.8, B.9）
3. ⚠️ 扩展简单类型白名单
4. ⚠️ 抽象构造回退策略

### 长期优化（C.12-C.16）
5. 📝 完善文档和示例
6. 🎨 优化 API ergonomics

---

## 📝 测试清单

需要补充的测试用例：

1. ✅ **Optional/Annotated**: `id: Optional[ID]`, `status: Annotated[OrderStatus, 'x']` 往返映射
2. ✅ **Enum 两种持久化**: `Enum↔str` 与 `Enum↔int`
3. ✅ **多外键**: `parent_keys=["tenant_id","org_id","order_id"]`，验证优先级
4. ✅ **构造回退**: PO/Domain 的 `__init__` 不接受参数，走 `setattr` 路径
5. ✅ **strict/debug 行为**: 缺失字段、类型不匹配、只读字段下的行为
6. ✅ **复用子 mapper**: 同一子 mapper 在两个父聚合下 `parent_keys` 独立
7. ✅ **事件清理幂等**: `map_reverse_with_events()` 后 `clear_events()` 被调用一次

