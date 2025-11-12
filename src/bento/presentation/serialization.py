from __future__ import annotations

import datetime as _dt
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass, field, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, get_type_hints

from bento.core.ids import ID, EntityId

# ---------- Extensible converter registry ----------

_primitive_converters: dict[type[Any], Callable[[Any], Any]] = {}


def register_converter(py_type: type[Any], fn: Callable[[Any], Any]) -> None:
    """Register a custom converter for a Python type."""
    _primitive_converters[py_type] = fn


# Pre-register common types
register_converter(ID, lambda v: v.value)
register_converter(EntityId, lambda v: v.value)
register_converter(Enum, lambda v: v.value)
register_converter(
    _dt.datetime,
    lambda v: v.astimezone(_dt.UTC).isoformat().replace("+00:00", "Z")
    if v.tzinfo
    else v.replace(tzinfo=_dt.UTC).isoformat().replace("+00:00", "Z"),
)
register_converter(_dt.date, lambda v: v.isoformat())
register_converter(Decimal, lambda v: str(v))
register_converter(uuid.UUID, lambda v: str(v))


# ---------- Configuration ----------


@dataclass(slots=True)
class DumpConfig:
    include_none: bool = False
    max_depth: int = 6
    # Global include/exclude by public attribute name
    include_fields: set[str] = field(default_factory=set)  # empty = no whitelist restriction
    exclude_fields: set[str] = field(
        default_factory=lambda: {"_events", "events", "_domain_events"}
    )
    exclude_private: bool = True  # exclude attributes starting with "_"
    # Expand computed properties by type (e.g., subtotal, items_count)
    expand_props_by_type: dict[type[Any], set[str]] = field(default_factory=dict)
    # Field rename map per type: {Type: {domain_field: exported_name}}
    rename_by_type: dict[type[Any], dict[str, str]] = field(default_factory=dict)


# ---------- Entry ----------


def dump(obj: Any, *, config: DumpConfig | None = None, _depth: int = 0) -> Any:
    """Generic domain object serializer for adapters.
    - ID/Enum/datetime/Decimal/UUID auto-conversion
    - Recursive for containers
    - Regular objects: use __dict__ or dataclass asdict
    """
    cfg = config or DumpConfig()
    if _depth > cfg.max_depth:
        return None

    # None/bool/number/str/bytes: pass through
    if obj is None or isinstance(obj, (bool, int, float, str, bytes)):
        return obj

    # Registered primitive converters (exact or parent types)
    for t, fn in _primitive_converters.items():
        try:
            if isinstance(obj, t):
                return fn(obj)
        except TypeError:
            # Some typing constructs may raise TypeError; ignore and continue
            pass

    # Enum fallback if user didn't rely on Enum base registration
    if isinstance(obj, Enum):
        return obj.value

    # Containers
    if isinstance(obj, Mapping):
        # Normalize ID-like mappings: {"value": "..."} -> "..."
        try:
            if set(obj.keys()) == {"value"}:
                return dump(obj.get("value"), config=cfg, _depth=_depth + 1)
        except Exception:
            pass
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if v is None and not cfg.include_none:
                continue
            out[str(k)] = dump(v, config=cfg, _depth=_depth + 1)
        return out

    if isinstance(obj, (list, tuple, set, frozenset)):
        return [dump(v, config=cfg, _depth=_depth + 1) for v in obj]

    # Dataclass (instance only; dataclass classes also return True for is_dataclass)
    if is_dataclass(obj) and not isinstance(obj, type):
        return _dump_from_mapping(asdict(obj), obj.__class__, cfg, _depth)

    # General objects (Entity/AggregateRoot/Value Objects/others)
    # Prefer __dict__; if absent, use type hints/dir as fallback
    data: dict[str, Any] = {}
    source = getattr(obj, "__dict__", None)

    if source is None:
        hints = {}
        try:
            hint_target = obj if isinstance(obj, type) else obj.__class__
            hints = get_type_hints(hint_target)
        except Exception:
            hints = {}
        candidates: Iterable[str] = hints.keys() or [n for n in dir(obj) if not n.startswith("__")]
        source = {n: getattr(obj, n, None) for n in candidates}

    target_type = obj if isinstance(obj, type) else obj.__class__
    rename_map = cfg.rename_by_type.get(target_type, {})
    expand_props = cfg.expand_props_by_type.get(target_type, set())

    for name, value in source.items():
        if cfg.exclude_private and name.startswith("_"):
            continue
        if name in cfg.exclude_fields:
            continue
        if cfg.include_fields and name not in cfg.include_fields and name not in expand_props:
            continue

        # Computed properties
        if name in expand_props:
            try:
                value = getattr(obj, name)
            except Exception:
                continue

        if value is None and not cfg.include_none:
            continue

        out_key = rename_map.get(name, name)
        data[out_key] = dump(value, config=cfg, _depth=_depth + 1)

    # Add computed properties that are not present in __dict__
    for prop in expand_props:
        if prop in source:
            continue
        try:
            value = getattr(obj, prop)
        except Exception:
            continue
        if value is None and not cfg.include_none:
            continue
        out_key = rename_map.get(prop, prop)
        data[out_key] = dump(value, config=cfg, _depth=_depth + 1)

    return data


def _dump_from_mapping(
    m: Mapping[str, Any], typ: type[Any], cfg: DumpConfig, depth: int
) -> dict[str, Any]:
    """Apply include/exclude/rename/recursion to dataclass mapping."""
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

    return out
