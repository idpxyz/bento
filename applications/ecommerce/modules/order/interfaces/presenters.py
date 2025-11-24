from __future__ import annotations

from applications.ecommerce.modules.order.domain.order import Order, OrderItem
from applications.ecommerce.modules.order.domain.vo import Money
from bento.presentation.serialization import DumpConfig, dump, register_converter

# Register Money converter once for API presentation:
# Represent as {"amount": "12.34", "currency": "USD"} to preserve precision.
try:
    register_converter(Money, lambda m: {"amount": str(m.amount), "currency": m.currency})
except Exception:
    # If already registered by another module/import, ignore
    pass

order_dump_cfg = DumpConfig(
    include_none=False,
    expand_props_by_type={
        OrderItem: {"subtotal"},
        Order: {"items_count", "total_amount"},
    },
    rename_by_type={
        Order: {"id": "order_id"},
        OrderItem: {"id": "item_id"},
    },
)


def order_to_dict(order: Order) -> dict:
    d = dump(order, config=order_dump_cfg)
    # Ensure key summary fields are present even if serializer filtered Nones
    # and regardless of internal attribute names.
    if "order_id" not in d:
        d["order_id"] = str(getattr(order.id, "value", order.id))
    if "customer_id" not in d and getattr(order, "customer_id", None) is not None:
        d["customer_id"] = str(getattr(order.customer_id, "value", order.customer_id))
    if "status" not in d and getattr(order, "status", None) is not None:
        # Enum or str
        st = getattr(order.status, "value", order.status)
        d["status"] = st
    if "items_count" not in d:
        try:
            d["items_count"] = order.items_count
        except Exception:
            pass
    if "total_amount" not in d:
        try:
            d["total_amount"] = order.total_amount
        except Exception:
            pass
    return d


def orders_to_list(orders: list[Order]) -> list[dict]:
    return [dump(o, config=order_dump_cfg) for o in orders]
