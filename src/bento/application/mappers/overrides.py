from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from .auto import AutoMapper


def register_decimal_str_overrides(
    mapper: AutoMapper[Any, Any],
    *field_names: str,
) -> None:
    """Register Decimal ↔ str overrides for given field names on mapper.

    Usage:
        register_decimal_str_overrides(mapper, "total_amount", "tax_amount")
    """

    def to_po_decimal(v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, Decimal):
            return str(v)
        return str(v)

    def from_po_decimal(v: Any) -> Decimal | None:
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))

    for fn in field_names:
        mapper.override_field(fn, to_po=to_po_decimal, from_po=from_po_decimal)


def register_custom_overrides(
    mapper: AutoMapper[Any, Any],
    field_to_overrides: dict[str, tuple[Callable[[Any], Any], Callable[[Any], Any]]],
) -> None:
    """Batch register custom overrides for fields.

    Args:
        mapper: AutoMapper instance
        field_to_overrides: {field_name: (to_po, from_po)}
    """
    for field_name, (to_po, from_po) in field_to_overrides.items():
        mapper.override_field(field_name, to_po=to_po, from_po=from_po)
