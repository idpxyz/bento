"""BaseMapper - Intelligent mapper with automatic type conversion.

This module provides BaseMapper, an enhanced mapper that automatically handles:
- ID type conversion (EntityId/ID ↔ str) with support for custom ID types
- Enum conversion (Enum ↔ str/value) with detailed error messages
- Child entity mapping (automatic parent-child relationships)
- Multi-parent keys support (e.g., tenant_id + org_id + order_id)
- Mapping context propagation (tenant_id, org_id, actor_id, etc.)
- Event cleanup (automatic clear_events after map_reverse)
- Batch mapping helpers (map_list, map_reverse_list)

Key features:
- map_reverse_with_events() template method to ensure domain events cleared
- Pluggable id_factory and default_id_type (support custom XxxId)
- Multi-parent keys propagation (e.g., ["tenant_id","org_id","order_id"])
- Optional MappingContext to propagate tenant/org/actor etc.
- Batch helpers: map_list(), map_reverse_list()
- Parent keys stored in parent mapper (avoid polluting child mapper state)

Goal: Reduce mapper code by 80-90% through intelligent conventions.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from bento.application.mappers.strategy import MapperStrategy
from bento.core.ids import ID, EntityId


# ---------- Type Protocols (for enhanced type checking) ----------
@runtime_checkable
class HasId(Protocol):
    """Protocol for objects with an id attribute."""

    id: str | ID | EntityId | Any


@runtime_checkable
class HasEvents(Protocol):
    """Protocol for domain objects that can have events."""

    def clear_events(self) -> None:
        """Clear domain events."""
        ...


# ---------- Context (optional) ----------
@dataclass(slots=True)
class MappingContext:
    """Optional mapping context for propagating tenant/org/actor information.

    Use this when you need to automatically propagate context information
    (like tenant_id, org_id) to child entities during mapping.

    Example:
        ```python
        context = MappingContext(tenant_id="t1", org_id="o1", actor_id="u1",
                                 extra={"channel": "web"})
        mapper = OrderMapper(context=context)
        ```
    """

    tenant_id: str | None = None
    org_id: str | None = None
    actor_id: str | None = None
    extra: dict[str, Any] = field(
        default_factory=dict
    )  # 任意扩展信息（如渠道、来源等）；用 default_factory 避免判空/共享可变默认值


class BaseMapper[Domain, PO](MapperStrategy[Domain, PO]):
    """Base mapper with automatic type conversion and helper methods.

    Automatically handles common conversion patterns:
    1. ID fields: domain.id (EntityId/ID) ↔ po.id (str)
    2. Enum fields: domain.status (Enum) ↔ po.status (str)
    3. Child entities: domain.items (list) ↔ po.items (list)
    4. Events: auto clear_events() after map_reverse
    5. Multi-parent keys: support complex hierarchies (tenant_id + org_id + order_id)
    6. Context propagation: automatically propagate tenant/org/actor info

    Key improvements over base.py:
    - Parent keys stored in parent mapper (avoid polluting child mapper state)
    - MappingContext.extra uses default_factory to avoid mutable default value
    - Better error handling with try-except in map_children
    - Query method child_parent_keys() for introspection

    Example:
        ```python
        class OrderItemMapper(BaseMapper[OrderItem, OrderItemModel]):
            def __init__(self):
                super().__init__(OrderItem, OrderItemModel)

        class OrderMapper(BaseMapper[Order, OrderModel]):
            def __init__(self, context: MappingContext | None = None):
                super().__init__(Order, OrderModel, context=context)
                # Register child entities (parent keys stored in parent mapper)
                self.register_child("items", OrderItemMapper(), parent_keys="order_id")
            # Or with multiple parent keys:
            # self.register_child("items", OrderItemMapper(),
            #                     parent_keys=["tenant_id", "org_id", "order_id"])

            # Only need to implement custom logic!
            # ID, Enum, Events are handled automatically
        ```

    Conventions:
    - Fields ending with '_id' or named 'id': auto-convert to/from ID types
    - Enum fields: auto-convert to/from string values
    - Registered children: auto-map with parent key management
    - Domain events: auto-cleared after map_reverse
    """

    def __init__(
        self,
        domain_type: type[Domain],
        po_type: type[PO],
        *,
        default_id_type: type = ID,
        id_factory: Callable[[str], Any] | None = None,
        context: MappingContext | None = None,
    ) -> None:
        """Initialize base mapper.

        Args:
            domain_type: Domain object type
            po_type: Persistence object type
            default_id_type: Default ID type to use when converting strings (defaults to ID)
            id_factory: Optional factory function for creating custom ID types
            context: Optional mapping context for propagating tenant/org/actor info
        """
        super().__init__(domain_type, po_type)
        # 子映射器注册表（父 mapper 自身维护 parent_keys，避免污染 child mapper）
        self._children: dict[str, BaseMapper] = {}
        self._child_parent_keys: dict[str, tuple[str, ...]] = {}

        # ID 策略
        self._default_id_type = default_id_type
        self._id_factory = id_factory  # 若提供，优先于 default_id_type

        # 可选上下文
        self._context = context

    # ---------- Registration & lookup ----------
    def register_child(
        self,
        field_name: str,
        child_mapper: BaseMapper,
        *,
        parent_keys: str | Sequence[str] | None = None,
    ) -> BaseMapper[Domain, PO]:
        """Register a child entity mapper.

        Parent keys are stored in the parent mapper (not in child mapper)
        to avoid polluting child mapper state. This allows the same child mapper
        to be used by multiple parent mappers with different parent keys.

        Args:
            field_name: Domain field name containing child entities (e.g., "items")
            child_mapper: Mapper for child entities
            parent_keys: Parent foreign key(s). Can be:
                - A single string: "order_id"
                - A sequence of strings: ["tenant_id", "org_id", "order_id"]
                - None: no parent keys

        Returns:
            Self for chaining

        Example:
            ```python
            # Single parent key
            mapper = OrderMapper()
            mapper.register_child("items", OrderItemMapper(), parent_keys="order_id")

            # Multiple parent keys
            mapper.register_child("items", OrderItemMapper(),
                                parent_keys=["tenant_id", "org_id", "order_id"])
            ```
        """
        self._children[field_name] = child_mapper
        if parent_keys:
            if isinstance(parent_keys, str):
                self._child_parent_keys[field_name] = (parent_keys,)
            else:
                self._child_parent_keys[field_name] = tuple(parent_keys)
        return self

    def get_child_mapper(self, field_name: str) -> BaseMapper:
        """Get registered child mapper by field name.

        Args:
            field_name: Field name of the registered child

        Returns:
            Child mapper instance

        Raises:
            KeyError: If no mapper registered for field_name

        Example:
            ```python
            item_mapper = order_mapper.get_child_mapper("items")
            item_model = item_mapper.map(item)
            ```
        """
        return self._children[field_name]

    def child_parent_keys(self, field_name: str) -> tuple[str, ...]:
        """Return configured parent keys for a given child field.

        Args:
            field_name: Field name of the registered child

        Returns:
            Tuple of parent key names (empty tuple if not set)

        Example:
            ```python
            keys = order_mapper.child_parent_keys("items")
            # Returns: ("order_id",) or ("tenant_id", "org_id", "order_id")
            ```
        """
        return self._child_parent_keys.get(field_name, tuple())

    # ---------- Abstract mapping methods ----------
    @abstractmethod
    def map(self, domain: Domain) -> PO:
        """Map domain to PO.

        Note: Override and use helper methods like:
        - convert_id_to_str()
        - convert_enum_to_str()
        - map_children()

        Implementations should validate domain type if needed:
            ```python
            if not isinstance(domain, self._domain_type):
                raise TypeError(f"Expected {self._domain_type}, got {type(domain)}")
            ```
        """
        ...

    @abstractmethod
    def map_reverse(self, po: PO) -> Domain:
        """Map PO to domain.

        Note: Override and use helper methods like:
        - convert_str_to_id()
        - convert_str_to_enum()
        - map_reverse_children()

        Events are automatically cleared after this method.

        Implementations should validate PO type if needed:
            ```python
            if not isinstance(po, self._po_type):
                raise TypeError(f"Expected {self._po_type}, got {type(po)}")
            ```
        """
        ...

    # ---------- Template method to enforce events cleanup ----------
    def map_reverse_with_events(self, po: PO) -> Domain:
        """Recommended entry-point for PO -> Domain mapping.

        Guarantees events clearing afterwards. Use this instead of map_reverse()
        when you want to ensure domain events are automatically cleared.

        Args:
            po: Persistence object to map from

        Returns:
            Domain object with events cleared
        """
        d = self.map_reverse(po)
        self.auto_clear_events(d)
        return d

    # ---------- Batch helpers ----------
    def map_list(self, domains: Iterable[Domain]) -> list[PO]:
        """Map a list of domain objects to PO objects.

        Args:
            domains: Iterable of domain objects

        Returns:
            List of PO objects
        """
        return [self.map(d) for d in domains]

    def map_reverse_list(self, pos: Iterable[PO], *, with_events: bool = True) -> list[Domain]:
        """Map a list of PO objects to domain objects.

        Args:
            pos: Iterable of PO objects
            with_events: Whether to automatically clear events (default: True)

        Returns:
            List of domain objects
        """
        if with_events:
            return [self.map_reverse_with_events(p) for p in pos]
        return [self.map_reverse(p) for p in pos]

    # ==================== Helper Methods ====================

    # --- ID conversion ---
    def convert_id_to_str(self, id_value: Any) -> str | None:
        """Convert ID/EntityId to string.

        Args:
            id_value: ID, EntityId, or already a string

        Returns:
            String representation of ID

        Note:
            Supports Protocol-based type checking for objects with id attribute.
        """
        if id_value is None:
            return None
        if isinstance(id_value, (EntityId, ID)):
            return id_value.value
        # 支持 Protocol 类型（HasId）
        if isinstance(id_value, HasId):
            id_attr = getattr(id_value, "id", None)
            if id_attr is not None:
                return self.convert_id_to_str(id_attr)
        return str(id_value)

    def convert_str_to_id(
        self,
        str_value: str | None,
        id_type: type | None = None,
    ) -> EntityId | ID | Any | None:
        """Convert string to ID/EntityId/custom ID type.

        Priority: provided id_type > id_factory > default_id_type

        Args:
            str_value: String ID value
            id_type: Target ID type (ID, EntityId, or custom XxxId).
                If None, uses id_factory or default_id_type

        Returns:
            ID, EntityId, or custom ID instance

        Example:
            ```python
            # Use default ID type
            order_id = self.convert_str_to_id("123")  # Returns ID("123")

            # Use specific ID type
            order_id = self.convert_str_to_id("123", id_type=EntityId)  # Returns EntityId("123")

            # Custom ID type (if id_factory is set)
            custom_id = self.convert_str_to_id("123")  # Uses id_factory or default_id_type
            ```
        """
        if str_value is None:
            return None
        if id_type is not None:
            return self._construct_id(id_type, str_value)
        if self._id_factory is not None:
            return self._id_factory(str_value)
        return self._construct_id(self._default_id_type, str_value)

    @staticmethod
    def _construct_id(id_cls: type, raw: str) -> Any:
        """Construct an ID instance from a string.

        Compatible with bento.core.ids.ID/EntityId and custom XxxId(str) constructors.
        """
        if id_cls in (EntityId, ID):
            return id_cls(raw)
        return id_cls(raw)

    # --- Enum conversion ---
    def convert_enum_to_str(self, enum_value: Enum | None) -> str | None:
        """Convert Enum to string value.

        Args:
            enum_value: Enum instance

        Returns:
            String value of enum
        """
        if enum_value is None:
            return None
        if isinstance(enum_value, Enum):
            return str(enum_value.value)
        return str(enum_value)

    def convert_str_to_enum(self, str_value: str | None, enum_type: type[Enum]) -> Enum | None:
        """Convert string to Enum.

        Args:
            str_value: String enum value or name
            enum_type: Target enum type

        Returns:
            Enum instance

        Raises:
            ValueError: If string doesn't match any enum value or name, with detailed error message

        Example:
            ```python
            status = self.convert_str_to_enum("PAID", OrderStatus)  # Returns OrderStatus.PAID
            status = self.convert_str_to_enum("PAID", OrderStatus)  # Also works by name
            ```
        """
        if str_value is None:
            return None
        try:
            return enum_type(str_value)  # match value
        except ValueError:
            try:
                return enum_type[str_value]  # match name
            except KeyError as e:
                allowed_values = ", ".join(repr(m.value) for m in enum_type)

                allowed_names = ", ".join(m.name for m in enum_type)

                raise ValueError(
                    f"Invalid {enum_type.__name__}: {str_value!r}. "
                    f"Allowed values: [{allowed_values}]; names: [{allowed_names}]"
                ) from e

    # --- Children mapping (with multi-FK propagation) ---
    def map_children(
        self,
        domain: Domain,
        po: PO,
        field_name: str,
        set_parent_keys: bool = True,
    ) -> list[Any]:
        """Map child entities from domain to PO.

        Automatically propagates parent keys and context information
        (tenant_id, org_id) when available. Parent keys are retrieved from
        the parent mapper's _child_parent_keys dictionary (not from child mapper).

        Args:
            domain: Domain object containing children
            po: PO object (used for setting parent key if needed)
            field_name: Field name containing children
            set_parent_keys: Whether to set parent foreign key(s) on child POs

        Returns:
            List of child POs

        Example:
            ```python
            # In map() method:
            order_model.items = self.map_children(order, order_model, "items")
            ```
        """
        if field_name not in self._children:
            raise ValueError(f"Child mapper not registered for field: {field_name}")

        child_mapper = self._children[field_name]
        children = getattr(domain, field_name, []) or []
        child_pos: list[Any] = []

        # Compute parent id value once
        domain_id = getattr(domain, "id", None)
        parent_id_value = (
            self.convert_id_to_str(domain_id) if domain_id is not None else getattr(po, "id", None)
        )

        for child in children:
            child_po = child_mapper.map(child)

            if set_parent_keys:
                keys = self._child_parent_keys.get(field_name, ())
                if keys:
                    for key in keys:
                        try:
                            if key == "tenant_id" and self._context and self._context.tenant_id:
                                setattr(child_po, key, self._context.tenant_id)
                            elif key == "org_id" and self._context and self._context.org_id:
                                setattr(child_po, key, self._context.org_id)
                            elif key in ("order_id", "parent_id", "aggregate_id"):
                                if parent_id_value is not None:
                                    setattr(child_po, key, parent_id_value)
                            else:
                                # 其它键尝试从 domain / po / context.extra 里兜底
                                if hasattr(domain, key):
                                    setattr(child_po, key, getattr(domain, key))
                                elif hasattr(po, key):
                                    setattr(child_po, key, getattr(po, key))
                                elif self._context and key in self._context.extra:
                                    setattr(child_po, key, self._context.extra[key])
                        except (AttributeError, TypeError, ValueError):
                            # ORM 只读/延迟属性或类型不匹配等，保持容错；
                            # 是否抛错交由上层 AutoMapper(debug/strict) 控制。
                            pass

            child_pos.append(child_po)

        return child_pos

    def map_reverse_children(self, po: PO, field_name: str) -> list[Any]:
        """Map child entities from PO to domain.

        Args:
            po: PO object containing child POs
            field_name: Field name containing child POs

        Returns:
            List of domain children

        Example:
            ```python
            # In map_reverse() method:
            order.items = self.map_reverse_children(order_model, "items")
            ```
        """
        if field_name not in self._children:
            raise ValueError(f"Child mapper not registered for field: {field_name}")

        child_mapper = self._children[field_name]
        child_pos = getattr(po, field_name, []) or []
        return [child_mapper.map_reverse(child_po) for child_po in child_pos]

    # --- Events cleanup ---
    def auto_clear_events(self, domain: Domain) -> None:
        """Automatically clear domain events if the method exists.

        Args:
            domain: Domain object that might have events

        Note:
            This is automatically called by map_reverse_with_events().
            You can also call it manually at the end of map_reverse() implementation.

        The method uses Protocol-based type checking for better type safety.
        """
        # 使用 Protocol 进行类型检查（运行时仍然使用 hasattr）
        if isinstance(domain, HasEvents):
            domain.clear_events()
        elif hasattr(domain, "clear_events"):
            domain.clear_events()


__all__ = ["BaseMapper", "MappingContext"]
