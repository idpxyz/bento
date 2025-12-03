"""Presenters for converting order domain objects to API responses."""

from contexts.ordering.domain.models.order import Order, OrderItem


def order_item_to_dict(item: OrderItem) -> dict:
    """Convert OrderItem to dictionary."""
    return {
        "id": str(item.id),
        "product_id": str(item.product_id),  # 转换 ID 对象为字符串
        "product_name": item.product_name,
        "quantity": item.quantity,
        "unit_price": float(item.unit_price),
        "subtotal": float(item.subtotal),
    }


def order_to_dict(order: Order) -> dict:
    """Convert Order aggregate to dictionary for API response."""
    return {
        "id": str(order.id),
        "customer_id": str(order.customer_id),  # 转换 ID 对象为字符串
        "items": [order_item_to_dict(item) for item in order.items],
        "total": float(order.total),
        "status": order.status.value if hasattr(order.status, "value") else order.status,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
    }
