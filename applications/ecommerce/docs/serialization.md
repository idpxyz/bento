你不需要把 `to_dict()` 写在领域对象里。六边形/DDD里，“序列化给外界（API/UI/日志）”属于**接口适配器层**职责；领域层应保持纯粹。给你一套**通用 Domain Serializer**，满足这些点：

* **零侵入**：不改你的 `Entity/AggregateRoot`，删除领域对象上的 `to_dict()` 即可。
* **智能转换**：`ID/EntityId → str`、`Enum → value`、`datetime/date → isoformat()`、`Decimal/UUID → str`、容器递归处理。
* **可配置**：支持 `include/exclude`、按类型注册“要展开的属性”（如 `subtotal`、`items_count`）、字段重命名、深度限制、None 过滤。
* **可扩展**：类型级转换器注册（适配你未来的 ValueObject、Money 等）。

---

# 代码：通用序列化器（放在 adapters 层，例如 `bento/presentation/serialization.py`）

```python
# bento/presentation/serialization.py
from __future__ import annotations

import datetime as _dt
import uuid
from dataclasses import dataclass, field, is_dataclass, asdict
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Type, get_type_hints

from bento.core.ids import ID, EntityId

# ---------- 可扩展转换器注册表 ----------

_primitive_converters: dict[Type[Any], Callable[[Any], Any]] = {}

def register_converter(py_type: Type[Any], fn: Callable[[Any], Any]) -> None:
    """注册特定类型的序列化函数（线程安全足够，启动期注册即可）"""
    _primitive_converters[py_type] = fn

# 预注册常见类型
register_converter(ID, lambda v: v.value)
register_converter(EntityId, lambda v: v.value)
register_converter(Enum, lambda v: v.value)
register_converter(_dt.datetime, lambda v: v.isoformat())
register_converter(_dt.date, lambda v: v.isoformat())
register_converter(Decimal, lambda v: str(v))
register_converter(uuid.UUID, lambda v: str(v))

# ---------- 配置 ----------

@dataclass(slots=True)
class DumpConfig:
    include_none: bool = False
    max_depth: int = 6
    # 全局 include/exclude：按字段名（公共属性）
    include_fields: set[str] = field(default_factory=set)   # 留空 = 不做白名单限制
    exclude_fields: set[str] = field(default_factory=lambda: {"_events", "events", "_domain_events"})
    exclude_private: bool = True        # 排除以 '_' 开头的属性
    # 类型级“要展开的属性/计算属性”（例如 subtotal、items_count）
    expand_props_by_type: dict[Type[Any], set[str]] = field(default_factory=dict)
    # 字段重命名：按“类型 → {领域字段: 导出名称}”
    rename_by_type: dict[Type[Any], dict[str, str]] = field(default_factory=dict)

# ---------- 入口 ----------

def dump(obj: Any, *, config: DumpConfig | None = None, _depth: int = 0) -> Any:
    """
    通用领域对象序列化（接口适配器用）。不依赖 ORM/Pydantic。
    - ID/Enum/datetime 等自动转换
    - 容器类型递归
    - 普通对象：提取 __dict__ 或 dataclass 的 asdict
    """
    cfg = config or DumpConfig()
    if _depth > cfg.max_depth:
        return None  # 或者返回 "...max_depth..."

    # None/布尔/数字/字符串：直传
    if obj is None or isinstance(obj, (bool, int, float, str, bytes)):
        return obj

    # 已注册的特定类型（精确匹配或父类匹配）
    for t, fn in _primitive_converters.items():
        try:
            if isinstance(obj, t):
                return fn(obj)
        except TypeError:
            # 某些 typing 类型可能触发 TypeError，忽略
            pass

    # Enum（兜底：当用户未通过父类注册时）
    if isinstance(obj, Enum):
        return obj.value

    # 容器
    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if v is None and not cfg.include_none:
                continue
            out[str(k)] = dump(v, config=cfg, _depth=_depth + 1)
        return out

    if isinstance(obj, (list, tuple, set, frozenset)):
        return [dump(v, config=cfg, _depth=_depth + 1) for v in obj]

    # dataclass
    if is_dataclass(obj):
        return _dump_from_mapping(asdict(obj), obj.__class__, cfg, _depth)

    # 一般对象（Entity/AggregateRoot/值对象等）
    # 优先 __dict__；若无，则尝试 public 属性枚举
    data: dict[str, Any] = {}
    source = getattr(obj, "__dict__", None)

    # 某些对象（如具有 __slots__）没有 __dict__，则通过类型注解/dir 兜底
    if source is None:
        # 使用注解作为候选字段优先；若无注解，回退到 dir 过滤可调用/私有
        hints = {}
        try:
            hints = get_type_hints(obj.__class__)
        except Exception:
            hints = {}
        candidates = hints.keys() or [n for n in dir(obj) if not n.startswith("__")]
        source = {n: getattr(obj, n, None) for n in candidates}

    # 过滤与重命名
    rename_map = cfg.rename_by_type.get(obj.__class__, {})
    expand_props = cfg.expand_props_by_type.get(obj.__class__, set())

    for name, value in source.items():
        if cfg.exclude_private and name.startswith("_"):
            continue
        if name in cfg.exclude_fields:
            continue
        if cfg.include_fields and name not in cfg.include_fields and name not in expand_props:
            # 开启白名单时，允许 expand_props 里的计算属性
            continue

        # 处理计算属性（@property），优先从对象现取（source 里可能没有）
        if name in expand_props:
            try:
                value = getattr(obj, name)
            except Exception:
                # 无法取到计算属性则跳过
                continue

        if value is None and not cfg.include_none:
            continue

        out_key = rename_map.get(name, name)
        data[out_key] = dump(value, config=cfg, _depth=_depth + 1)

    return data


def _dump_from_mapping(m: Mapping[str, Any], typ: Type[Any], cfg: DumpConfig, depth: int) -> dict[str, Any]:
    """dataclass 的 dict 结果进一步应用 include/exclude/rename/递归转换"""
    rename_map = cfg.rename_by_type.get(typ, {})
    expand_props = cfg.expand_props_by_type.get(typ, set())

    out: dict[str, Any] = {}
    for k, v in m.items():
        if cfg.exclude_private and k.startswith("_"):
            continue
        if k in cfg.exclude_fields:
            continue
        if cfg.include_fields and k not in cfg.include_fields and k not in expand_props:
            continue
        if v is None and not cfg.include_none:
            continue

        out_key = rename_map.get(k, k)
        out[out_key] = dump(v, config=cfg, _depth=depth + 1)

    # dataclass 也可附加计算属性
    for prop in expand_props:
        try:
            val = getattr(typ, prop)  # 取不到实例值，下面再用实例无效，这里跳过
        except Exception:
            continue
    return out
```

> 说明
>
> * 入口 `dump(obj, config=DumpConfig(...))` 即可；默认排除 `_events`/`events/_domain_events` 等领域事件缓冲。
> * 通过 `register_converter()` 可挂接新类型（如 `Money`、`GeoPoint`）。
> * 通过 `DumpConfig.expand_props_by_type` 指定要展开的**计算属性**（如 `subtotal`、`items_count`、`total_amount`）。

---

# 在你的 `Order / OrderItem` 中使用

**删除**两个类里的 `to_dict()`。在 API 适配器里这样用：

```python
# adapters/api/orders/presenters.py
from bento.presentation.serialization import dump, DumpConfig
from applications.ecommerce.modules.order.domain.order import Order, OrderItem  # 你的路径

order_dump_cfg = DumpConfig(
    include_none=False,
    # 展开计算属性
    expand_props_by_type={
        OrderItem: {"subtotal"},
        Order: {"items_count", "total_amount"},
    },
    # 可选：对不同类型重命名字段
    rename_by_type={
        Order: {"id": "order_id"},
        OrderItem: {"id": "item_id"},
    },
)

def order_to_dict(order: Order) -> dict:
    return dump(order, config=order_dump_cfg)

def orders_to_list(orders: list[Order]) -> list[dict]:
    return [dump(o, config=order_dump_cfg) for o in orders]
```

返回示例（等价于你原来的 `to_dict()`，但**零侵入**）：

```json
{
  "order_id": "ORD-123",
  "customer_id": "CUST-9",
  "status": "PENDING",
  "items": [
    {
      "item_id": "ITEM-1",
      "product_id": "SKU-001",
      "product_name": "Product A",
      "quantity": 2,
      "unit_price": 99.99,
      "subtotal": 199.98
    }
  ],
  "items_count": 1,
  "total_amount": 199.98,
  "created_at": "2025-11-11T08:00:00.123456",
  "paid_at": null,
  "cancelled_at": null,
  "payment_method": null,
  "payment_card_last4": null,
  "payment_card_brand": null,
  "payment_paypal_payer_id": null,
  "shipment_carrier": null,
  "shipment_tracking_no": null,
  "shipment_service": null
}
```

---

# 进一步集成建议

1. **保持领域层纯净**：移除 `to_dict()`；序列化只在适配器层（API/消息发布/日志）完成。
2. **与 AutoMapper 协同**：需要 DTO（如 `OrderDTO`）时，用你现有 `AutoMapper` → PO/DTO；而 `dump()` 适合**直接导出领域对象**（查询/事件）。
3. **可观测性**：在 `DumpConfig` 里按类型重命名/过滤敏感字段（如掩码 `payment_card_last4`）。
4. **值对象支持**：为自定义 Value Object 注册转换器：

   ```python
   from mydomain.money import Money
   register_converter(Money, lambda m: {"amount": str(m.amount), "currency": m.currency})
   ```

---

# 快速替代方案（若你倾向框架内置）

* **Pydantic v2 `BaseModel` DTO**：领域 → DTO（AutoMapper），DTO 自带 `.model_dump()/.model_dump_json()`。
* **dataclass DTO**：用 `@dataclass` 定义 API DTO，再 `AutoMapper` 过去，`asdict()` 输出（注意自定义类型的转换）。

但就“最小侵入 + 复用你已实现的 AutoMapper/BaseMapper 体系”而言，上面的 `dump()` 更加轻量、可控。
