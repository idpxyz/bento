"""AutoMapper - Zero-config automatic mapper with type inference.

This module provides AutoMapper that automatically:
1. Analyzes Domain and PO field types
2. Infers conversion rules (ID, Enum, simple fields, Annotated types)
3. Generates mapping logic automatically
4. Allows selective overrides for special cases
5. Supports BaseMapper features (custom ID types, MappingContext)

Goal: Reduce mapper code by 90%+ with intelligent automation.
"""

from __future__ import annotations

import inspect
import logging
import types
from collections.abc import Callable
from dataclasses import MISSING, is_dataclass
from dataclasses import fields as dataclass_fields
from enum import Enum
from typing import Annotated, Any, ClassVar, Union, get_args, get_origin, get_type_hints

from bento.application.mapper.base import BaseMapper, MappingContext
from bento.core.ids import ID, EntityId


# -----------------------------
# Field mapping descriptor
# -----------------------------
class FieldMapping:
    """Represents a field mapping rule between a domain field and a PO field."""

    def __init__(
        self,
        domain_field: str,
        po_field: str,
        domain_type: type | None = None,
        po_type: type | None = None,
        to_po_converter: Callable[[Any], Any] | None = None,
        from_po_converter: Callable[[Any], Any] | None = None,
    ):
        self.domain_field = domain_field
        self.po_field = po_field
        self.domain_type = domain_type
        self.po_type = po_type
        self.to_po_converter = to_po_converter
        self.from_po_converter = from_po_converter


# -----------------------------
# Type analyzer (reflection)
# -----------------------------
class TypeAnalyzer:
    """Analyzes types and infers conversion rules (IDs, Enums, simple types, lists)."""

    _fields_cache: ClassVar[dict[type, dict[str, type]]] = {}

    @staticmethod
    def _unwrap_annotated(t: type) -> type:
        """Unwrap Annotated type to get the inner type."""
        if get_origin(t) is Annotated:
            return get_args(t)[0]
        return t

    @staticmethod
    def _unwrap_optional(field_type: type) -> type:
        """Return inner type if Optional/Union[..., None]; also unwrap Annotated."""
        field_type = TypeAnalyzer._unwrap_annotated(field_type)
        origin = get_origin(field_type)
        # Handle both typing.Union (Union[X, Y]) and types.UnionType (X | Y in Python 3.10+)
        is_union = origin is Union or (hasattr(types, "UnionType") and origin is types.UnionType)
        if is_union:
            args = [t for t in get_args(field_type) if t is not type(None)]  # noqa: E721
            return args[0] if args else field_type
        return field_type

    @staticmethod
    def get_fields(klass: type) -> dict[str, type]:
        """Return {field_name: normalized_type} for dataclass/typed class/ORM-like class."""
        cache = TypeAnalyzer._fields_cache
        if klass in cache:
            return cache[klass]

        # dataclass 优先
        if is_dataclass(klass):
            # 移除 isinstance 过滤，统一在 _unwrap_optional 中处理
            # 这样可以正确处理 Optional[List[T]]、Annotated[T, ...] 等 typing 类型
            d = {
                f.name: TypeAnalyzer._unwrap_optional(f.type)  # type: ignore[arg-type]
                for f in dataclass_fields(klass)
            }
            cache[klass] = d
            return d

        # typing hints（为 postponed annotations / ForwardRef 提供 ns，并做 normalize）
        try:
            # 使用模块命名空间以正确解析 ForwardRef 和延迟注解
            import sys

            globalns = (
                vars(sys.modules[klass.__module__]) if klass.__module__ in sys.modules else {}
            )
            hints = get_type_hints(klass, globalns=globalns, localns=None)
            if hints:
                normalized = {k: TypeAnalyzer._unwrap_optional(v) for k, v in hints.items()}
                cache[klass] = normalized
                return normalized
        except Exception:
            pass

        # __annotations__ 兜底
        ann = {}
        if hasattr(klass, "__annotations__"):
            ann = {
                k: TypeAnalyzer._unwrap_optional(v) for k, v in dict(klass.__annotations__).items()
            }
            cache[klass] = ann
            return ann

        # 最后尝试基于类属性的简单推断（极端兜底）
        fields_dict: dict[str, type] = {}
        for name, value in inspect.getmembers(klass):
            if not name.startswith("_") and not callable(value):
                fields_dict[name] = type(value)
        cache[klass] = fields_dict
        return fields_dict

    @staticmethod
    def is_id_type(field_type: type) -> bool:
        """True if field_type is ID/EntityId (after unwrap)."""
        field_type = TypeAnalyzer._unwrap_optional(field_type)
        if field_type in (ID, EntityId):
            return True
        # 兼容按名判断（迁移期/跨模块）
        type_name = getattr(field_type, "__name__", str(field_type))
        return type_name in ("ID", "EntityId")

    @staticmethod
    def is_enum_type(field_type: type) -> bool:
        """True if field_type is an Enum subclass (after unwrap)."""
        field_type = TypeAnalyzer._unwrap_optional(field_type)
        try:
            return isinstance(field_type, type) and issubclass(field_type, Enum)
        except TypeError:
            return False

    @staticmethod
    def is_list_type(field_type: type) -> bool:
        """True if field_type is list[...] (after unwrap)."""
        field_type = TypeAnalyzer._unwrap_optional(field_type)
        return get_origin(field_type) in (list,)

    @staticmethod
    def is_simple_type(field_type: type) -> bool:
        """True if field_type is a builtin scalar-like type.

        Supports common types: str, int, float, bool, bytes, datetime, date, UUID, Decimal.
        """
        from datetime import date, datetime
        from decimal import Decimal
        from uuid import UUID

        field_type = TypeAnalyzer._unwrap_optional(field_type)
        return field_type in (str, int, float, bool, bytes, datetime, date, UUID, Decimal)


# -----------------------------
# AutoMapper
# -----------------------------
class AutoMapper[Domain, PO](BaseMapper[Domain, PO]):
    """Automatic mapper with zero configuration.

    Automatically analyzes Domain and PO types and generates mapping logic.
    Users only need to override special cases.

    Key features:
    - Analyzes Domain/PO field types automatically
    - Infers conversion (ID ↔ str, Enum ↔ str/int, simple copy)
    - Supports Annotated types and Optional unwrapping
    - Auto-constructs objects
    - Auto-maps children via BaseMapper.map_children()
    - Supports BaseMapper features (custom ID types, MappingContext)
    - Allows selective overrides, aliasing, whitelist, and ignores

    Example:
        ```python
        # Minimal configuration - framework handles everything!
        class OrderItemMapper(AutoMapper[OrderItem, OrderItemModel]):
            def __init__(self):
                super().__init__(OrderItem, OrderItemModel)
                self.ignore_fields("order_id")  # Optional: ignore specific fields

        class OrderMapper(AutoMapper[Order, OrderModel]):
            def __init__(self, context: MappingContext | None = None):
                super().__init__(Order, OrderModel, context=context)
                # Optional: specify parent keys for child entities
                self.register_child("items", OrderItemMapper(), parent_keys="order_id")

            # No map() or map_reverse() needed for simple cases!
            # Framework auto-generates based on field analysis
        ```

    Advanced usage with overrides:
        ```python
        class OrderMapper(AutoMapper[Order, OrderModel]):
            def __init__(self):
                super().__init__(Order, OrderModel)
                self.register_child("items", OrderItemMapper(), parent_keys="order_id")

                # Override specific field conversion
                self.override_field(
                    "status",
                    to_po=lambda status: status.value,
                    from_po=lambda value: OrderStatus(value)
                )
        ```
    """

    _converter_kind_cache: ClassVar[dict[tuple[type, type], str]] = {}

    def __init__(
        self,
        domain_type: type[Domain],
        po_type: type[PO],
        *,
        include_none: bool = False,
        strict: bool = False,
        debug: bool = False,
        map_children_auto: bool = True,
        default_id_type: type = ID,
        id_factory: Callable[[str], Any] | None = None,
        domain_factory: Callable[[dict[str, Any]], Domain] | None = None,
        po_factory: Callable[[dict[str, Any]], PO] | None = None,
        context: MappingContext | None = None,
    ) -> None:
        """Initialize auto mapper with type analysis.

        Args:
            domain_type: Domain object type
            po_type: Persistence object type
            include_none: Whether to include None values in mapping
            strict: Whether to raise errors for unmapped fields (when whitelist provided)
            debug: Enable debug logging
            map_children_auto: Whether to automatically map child entities
            default_id_type: Default ID type to use when converting strings
            id_factory: Optional factory function for creating custom ID types
            domain_factory: Optional factory to construct domain objects from dict
            po_factory: Optional factory to construct PO objects from dict
            context: Optional mapping context for propagating tenant/org/actor info
        """
        super().__init__(
            domain_type,
            po_type,
            default_id_type=default_id_type,
            id_factory=id_factory,
            context=context,
        )

        self._analyzer = TypeAnalyzer()
        self._field_mappings: dict[str, FieldMapping] | None = None  # 延迟初始化
        self._ignored_fields: set[str] = set()
        self._overrides: dict[str, tuple[Callable, Callable]] = {}
        self._aliases: dict[str, str] = {}
        self._only_fields: set[str] | None = None

        self._include_none: bool = include_none
        self._strict: bool = strict
        self._debug_enabled: bool = debug
        self._logger = logging.getLogger(__name__)
        self._map_children_auto: bool = map_children_auto
        self._domain_factory = domain_factory
        self._po_factory = po_factory

        # 延迟初始化：首次使用时才分析类型（性能优化）
        # 如果 strict 模式，立即分析以便早期发现错误
        if strict:
            self._ensure_analyzed()

    # -------------------------
    # Analysis & inference
    # -------------------------
    def _ensure_analyzed(self) -> None:
        """Ensure type analysis is completed (lazy initialization)."""
        if self._field_mappings is None:
            self._analyze_types()

    def _analyze_types(self) -> None:
        """Analyze Domain and PO types to build field mappings."""
        domain_fields = self._analyzer.get_fields(self._domain_type)
        po_fields = self._analyzer.get_fields(self._po_type)

        # 不区分大小写匹配表
        po_fields_ci = {name.lower(): name for name in po_fields.keys()}

        for domain_field, domain_type in domain_fields.items():
            if domain_field.startswith("_"):
                continue
            if self._only_fields is not None and domain_field not in self._only_fields:
                continue

            po_field = self._find_po_field(domain_field, po_fields, po_fields_ci)
            if po_field is None:
                if self._debug_enabled:
                    self._logger.debug(
                        "AutoMapper: no PO field matched for domain '%s'", domain_field
                    )
                continue

            po_type = po_fields.get(po_field)
            if po_type is None:
                continue

            to_po, from_po = self._infer_converters(domain_type, po_type)

            if self._debug_enabled:
                self._logger.debug(
                    "AutoMapper: map '%s'(%s) -> '%s'(%s)",
                    domain_field,
                    getattr(domain_type, "__name__", str(domain_type)),
                    po_field,
                    getattr(po_type, "__name__", str(po_type)),
                )

            if self._field_mappings is None:
                self._field_mappings = {}
            self._field_mappings[domain_field] = FieldMapping(
                domain_field=domain_field,
                po_field=po_field,
                domain_type=domain_type,
                po_type=po_type,
                to_po_converter=to_po,
                from_po_converter=from_po,
            )

        # strict + whitelist：找出未映射字段并给建议
        if self._strict and self._only_fields is not None:
            # 确保 _field_mappings 已初始化（即使为空）
            if self._field_mappings is None:
                self._field_mappings = {}
            unmatched = [
                f
                for f in self._only_fields
                if f not in self._field_mappings and f not in self._ignored_fields
            ]
            if unmatched:
                suggestions: dict[str, list[str]] = {}
                for f in unmatched:
                    suggestions[f] = self._suggest_po_candidates(f, po_fields, po_fields_ci)
                parts: list[str] = []
                for f in unmatched:
                    sugg = suggestions.get(f) or []
                    parts.append(f"{f} -> candidates: {', '.join(sugg[:5])}")
                raise ValueError("AutoMapper strict mode: unmapped fields. " + "; ".join(parts))

    def _infer_converters(
        self, domain_type: type, po_type: type
    ) -> tuple[Callable[[Any], Any] | None, Callable[[Any], Any] | None]:
        """Infer conversion functions (with Optional unwrapped)."""
        unwrap = self._analyzer._unwrap_optional
        d_unwrapped = unwrap(domain_type)
        p_unwrapped = unwrap(po_type)

        key = (d_unwrapped, p_unwrapped)
        kind = self._converter_kind_cache.get(key)
        if kind is None:
            if self._analyzer.is_id_type(d_unwrapped) and p_unwrapped is str:
                kind = "id"
            elif self._analyzer.is_enum_type(d_unwrapped) and p_unwrapped is str:
                kind = "enum"
            elif self._analyzer.is_enum_type(d_unwrapped) and p_unwrapped is int:
                kind = "enum_int"  # 可选：启用枚举存 int 的映射
            elif d_unwrapped == p_unwrapped and self._analyzer.is_simple_type(d_unwrapped):
                kind = "simple"
            else:
                kind = "none"
            self._converter_kind_cache[key] = kind

        if kind == "id":
            return (
                lambda v: self.convert_id_to_str(v),
                lambda v: self.convert_str_to_id(v, d_unwrapped),
            )
        if kind == "enum":
            return (
                lambda v: self.convert_enum_to_str(v),
                lambda v: self.convert_str_to_enum(v, d_unwrapped),
            )
        if kind == "enum_int":
            return (
                lambda v: (None if v is None else (v.value if isinstance(v, Enum) else int(v))),
                lambda v: (None if v is None else d_unwrapped(int(v))),
            )
        if kind == "simple":
            return (lambda v: v, lambda v: v)
        return (None, None)

    # -------------------------
    # Public configuration API
    # -------------------------
    def alias_field(self, domain_field: str, po_field: str) -> AutoMapper[Domain, PO]:
        """Declare an alias mapping between domain and PO field names."""
        self._aliases[domain_field] = po_field
        if self._field_mappings is not None and domain_field in self._field_mappings:
            mapping = self._field_mappings[domain_field]
            mapping.po_field = po_field
        return self

    def only_fields(self, *field_names: str) -> AutoMapper[Domain, PO]:
        """Restrict automatic mapping to a whitelist of domain fields."""
        self._only_fields = set(field_names)
        if self._field_mappings is not None:
            self._field_mappings.clear()
        self._field_mappings = None  # 重置，下次使用时重新分析
        if self._strict:
            self._ensure_analyzed()  # strict 模式立即分析
        return self

    def ignore_fields(self, *field_names: str) -> AutoMapper[Domain, PO]:
        """Ignore specific fields during automatic mapping.

        Args:
            *field_names: Field names to ignore

        Returns:
            Self for chaining
        """
        self._ignored_fields.update(field_names)
        if self._field_mappings is not None:
            for f in field_names:
                self._field_mappings.pop(f, None)
        return self

    def override_field(
        self,
        field_name: str,
        to_po: Callable[[Any], Any],
        from_po: Callable[[Any], Any],
    ) -> AutoMapper[Domain, PO]:
        """Override conversion for a specific field.

        Args:
            field_name: Field name to override
            to_po: Conversion function domain → PO
            from_po: Conversion function PO → domain

        Returns:
            Self for chaining
        """
        self._overrides[field_name] = (to_po, from_po)
        if self._field_mappings is not None and field_name in self._field_mappings:
            mapping = self._field_mappings[field_name]
            mapping.to_po_converter = to_po
            mapping.from_po_converter = from_po
        return self

    def rebuild_mappings(self) -> AutoMapper[Domain, PO]:
        """Rebuild field mappings applying current aliases/ignores/whitelist/overrides."""
        self._field_mappings = None  # 重置，下次使用时重新分析
        self._ensure_analyzed()  # 立即重建
        # 重新应用 overrides 与 ignore
        assert self._field_mappings is not None
        for field_name, (to_po, from_po) in self._overrides.items():
            if field_name in self._field_mappings:
                m = self._field_mappings[field_name]
                m.to_po_converter = to_po
                m.from_po_converter = from_po
        for field_name in list(self._ignored_fields):
            self._field_mappings.pop(field_name, None)
        return self

    # -------------------------
    # Matching helpers
    # -------------------------
    def _find_po_field(
        self, domain_field: str, po_fields: dict[str, type], po_fields_ci: dict[str, str]
    ) -> str | None:
        """Find matching PO field for a domain field."""
        # 显式别名优先
        if domain_field in self._aliases:
            alias = self._aliases[domain_field]
            if alias in po_fields:
                return alias
            alias_ci = po_fields_ci.get(alias.lower())
            if alias_ci:
                return alias_ci
            return None

        def to_snake(name: str) -> str:
            if not name:
                return name
            out = []
            for ch in name:
                out.append("_" + ch.lower() if ch.isupper() else ch)
            s = "".join(out)
            return s[1:] if s.startswith("_") else s

        def to_camel(name: str) -> str:
            if not name:
                return name
            parts = name.split("_")
            return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])

        base = domain_field
        base_nid = base[:-3] if base.endswith("_id") else base

        candidates_ordered = [
            base,
            base_nid,
            f"{base_nid}_id",
            to_snake(base),
            to_snake(base_nid),
            f"{to_snake(base_nid)}_id",
            to_camel(base),
            to_camel(base_nid),
            to_camel(f"{base_nid}_id"),
        ]

        seen = set()
        for cand in candidates_ordered:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if cand in po_fields:
                return cand
            ci = po_fields_ci.get(cand.lower())
            if ci:
                return ci
        return None

    def _suggest_po_candidates(
        self, domain_field: str, po_fields: dict[str, type], po_fields_ci: dict[str, str]
    ) -> list[str]:
        """Return a list of plausible PO field names for a domain field."""

        def to_snake(name: str) -> str:
            if not name:
                return name
            out = []
            for ch in name:
                out.append("_" + ch.lower() if ch.isupper() else ch)
            s = "".join(out)
            return s[1:] if s.startswith("_") else s

        def to_camel(name: str) -> str:
            if not name:
                return name
            parts = name.split("_")
            return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])

        base = domain_field
        base_nid = base[:-3] if base.endswith("_id") else base

        candidates_ordered = [
            base,
            base_nid,
            f"{base_nid}_id",
            to_snake(base),
            to_snake(base_nid),
            f"{to_snake(base_nid)}_id",
            to_camel(base),
            to_camel(base_nid),
            to_camel(f"{base_nid}_id"),
        ]

        results: list[str] = []
        seen: set[str] = set()
        for cand in candidates_ordered:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if cand in po_fields:
                results.append(cand)
            else:
                ci = po_fields_ci.get(cand.lower())
                if ci:
                    results.append(ci)
        return results

    # -------------------------
    # Instantiation helpers (可覆写以支持自定义构造策略)
    # -------------------------
    def _instantiate_po(self, po_dict: dict[str, Any]) -> PO:
        """Instantiate PO object with fallback strategy.

        Override this method to customize instantiation logic
        (e.g., for Pydantic model_construct, custom factories, etc.).

        Args:
            po_dict: Dictionary of field values

        Returns:
            PO instance
        """
        # Custom factory first (for Pydantic/ORM/special constructors)
        if self._po_factory is not None:
            try:
                return self._po_factory(po_dict)
            except Exception as e:
                raise TypeError(
                    f"AutoMapper: po_factory failed for {self._po_type.__name__} "
                    f"with keys: {list(po_dict.keys())}. Error: {e}"
                ) from e
        try:
            return self._po_type(**po_dict)
        except TypeError:
            # Fallback: handle dataclass with required fields
            if is_dataclass(self._po_type):
                # Get default values for missing fields
                field_defaults = {}
                for f in dataclass_fields(self._po_type):
                    if f.default is not MISSING:
                        field_defaults[f.name] = f.default
                    elif f.default_factory is not MISSING:
                        field_defaults[f.name] = f.default_factory()
                # Merge defaults with provided values
                merged = {**field_defaults, **po_dict}
                try:
                    return self._po_type(**merged)
                except TypeError:
                    # Last resort: create with minimal fields and setattr
                    po = object.__new__(self._po_type)
                    for k, v in merged.items():
                        setattr(po, k, v)
                    return po
            else:
                # Non-dataclass: no-arg constructor + setattr
                try:
                    po = self._po_type()
                    for k, v in po_dict.items():
                        setattr(po, k, v)
                    return po
                except Exception as e:
                    raise TypeError(
                        f"AutoMapper: failed to construct {self._po_type.__name__} "
                        f"from keys: {list(po_dict.keys())}. "
                        f"Consider providing po_factory or override mapping. Error: {e}"
                    ) from e

    def _instantiate_domain(self, domain_dict: dict[str, Any]) -> Domain:
        """Instantiate Domain object with fallback strategy.

        Override this method to customize instantiation logic.

        Args:
            domain_dict: Dictionary of field values

        Returns:
            Domain instance
        """
        from dataclasses import fields as dataclass_fields
        from dataclasses import is_dataclass

        # Custom factory first (enforce invariants/complex construction)
        if self._domain_factory is not None:
            try:
                return self._domain_factory(domain_dict)
            except Exception as e:
                raise TypeError(
                    f"AutoMapper: domain_factory failed for {self._domain_type.__name__} "
                    f"with keys: {list(domain_dict.keys())}. Error: {e}"
                ) from e
        try:
            return self._domain_type(**domain_dict)
        except TypeError:
            # Fallback: handle dataclass with required fields
            if is_dataclass(self._domain_type):
                # Get default values for missing fields
                field_defaults = {}
                for f in dataclass_fields(self._domain_type):
                    if f.default is not MISSING:
                        field_defaults[f.name] = f.default
                    elif f.default_factory is not MISSING:
                        field_defaults[f.name] = f.default_factory()
                # Merge defaults with provided values
                merged = {**field_defaults, **domain_dict}
                try:
                    return self._domain_type(**merged)
                except TypeError:
                    # Last resort: create with minimal fields and setattr
                    domain = object.__new__(self._domain_type)
                    for k, v in merged.items():
                        setattr(domain, k, v)
                    return domain
            else:
                # Non-dataclass: no-arg constructor + setattr
                try:
                    domain = self._domain_type()
                    for k, v in domain_dict.items():
                        setattr(domain, k, v)
                    return domain
                except Exception as e:
                    raise TypeError(
                        f"AutoMapper: failed to construct {self._domain_type.__name__} "
                        f"from keys: {list(domain_dict.keys())}. "
                        f"Consider providing domain_factory or override mapping. Error: {e}"
                    ) from e

    # -------------------------
    # Mapping (Domain -> PO)
    # -------------------------
    def map(self, domain: Domain) -> PO:
        """Automatically map domain to PO using inferred rules.

        Args:
            domain: Domain object

        Returns:
            PO object

        Raises:
            TypeError: If domain is not an instance of the expected domain type
        """
        # 运行时类型验证
        if not isinstance(domain, self._domain_type):
            raise TypeError(
                f"Expected instance of {self._domain_type.__name__}, got {type(domain).__name__}"
            )

        self._ensure_analyzed()  # 延迟初始化
        self.before_map(domain)
        po_dict: dict[str, Any] = {}

        # _ensure_analyzed() 确保 _field_mappings 不为 None
        assert self._field_mappings is not None, "Field mappings should be initialized"
        for field_name, mapping in self._field_mappings.items():
            if field_name in self._ignored_fields:
                continue
            if field_name in self._children:
                # 子实体单独处理
                continue

            domain_value = getattr(domain, mapping.domain_field, None)
            if domain_value is None and not self._include_none:
                continue

            po_value = (
                mapping.to_po_converter(domain_value) if mapping.to_po_converter else domain_value
            )
            po_dict[mapping.po_field] = po_value

        # 为子字段提供占位，便于构造器（如 dataclass）不报缺参
        if self._map_children_auto and self._children:
            po_fields = self._analyzer.get_fields(self._po_type)
            for child_field in self._children.keys():
                if child_field in po_fields and child_field not in po_dict:
                    po_dict[child_field] = []

        # 构造 PO 实例（支持回退策略）
        po = self._instantiate_po(po_dict)

        # 自动子实体映射 + 多外键回填
        if self._map_children_auto and self._children:
            for field_name in self._children.keys():
                try:
                    child_pos = self.map_children(domain, po, field_name, set_parent_keys=True)
                    setattr(po, field_name, child_pos)
                except Exception as e:
                    if self._debug_enabled:
                        self._logger.exception("map_children failed for '%s': %s", field_name, e)
                    if self._strict:
                        raise

        self.after_map(domain, po)
        return po

    # -------------------------
    # Reverse mapping (PO -> Domain)
    # -------------------------
    def map_reverse(self, po: PO) -> Domain:
        """Automatically map PO to domain using inferred rules.

        Args:
            po: PO object

        Returns:
            Domain object

        Raises:
            TypeError: If po is not an instance of the expected PO type
        """
        # 运行时类型验证
        if not isinstance(po, self._po_type):
            raise TypeError(
                f"Expected instance of {self._po_type.__name__}, got {type(po).__name__}"
            )

        self._ensure_analyzed()  # 延迟初始化
        self.before_map_reverse(po)
        domain_dict: dict[str, Any] = {}

        # _ensure_analyzed() 确保 _field_mappings 不为 None
        assert self._field_mappings is not None, "Field mappings should be initialized"
        for field_name, mapping in self._field_mappings.items():
            if field_name in self._ignored_fields:
                continue
            if field_name in self._children:
                continue

            po_value = getattr(po, mapping.po_field, None)
            if po_value is None and not self._include_none:
                continue

            domain_value = (
                mapping.from_po_converter(po_value) if mapping.from_po_converter else po_value
            )
            domain_dict[mapping.domain_field] = domain_value

        # 为子字段提供占位，便于构造器（如 dataclass）不报缺参
        if self._map_children_auto and self._children:
            domain_fields = self._analyzer.get_fields(self._domain_type)
            for child_field in self._children.keys():
                if child_field in domain_fields and child_field not in domain_dict:
                    domain_dict[child_field] = []

        # 构造 Domain 实例（支持回退策略）
        domain = self._instantiate_domain(domain_dict)

        # 事件清理（遵循 BaseMapper 约定）
        self.auto_clear_events(domain)

        # 自动子实体反向映射
        if self._map_children_auto and self._children:
            for field_name in self._children.keys():
                try:
                    children = self.map_reverse_children(po, field_name)
                    setattr(domain, field_name, children)
                except Exception as e:
                    if self._debug_enabled:
                        self._logger.exception(
                            "map_reverse_children failed for '%s': %s", field_name, e
                        )
                    if self._strict:
                        raise

        self.after_map_reverse(po, domain)
        return domain

    # -------------------------
    # Hooks (override as needed)
    # -------------------------
    def before_map(self, domain: Domain) -> None:  # noqa: D401
        """Hook before mapping domain → PO (override if needed)."""
        return None

    def after_map(self, domain: Domain, po: PO) -> None:  # noqa: D401
        """Hook after mapping domain → PO (override if needed)."""
        return None

    def before_map_reverse(self, po: PO) -> None:  # noqa: D401
        """Hook before mapping PO → domain (override if needed)."""
        return None

    def after_map_reverse(self, po: PO, domain: Domain) -> None:  # noqa: D401
        """Hook after mapping PO → domain (override if needed)."""
        return None


__all__ = ["AutoMapper", "TypeAnalyzer", "FieldMapping"]
