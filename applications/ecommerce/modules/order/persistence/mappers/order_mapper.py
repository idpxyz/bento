"""Order domain-to-persistence mapper using AutoMapper.

This mapper handles bidirectional conversion between:
- Order (domain aggregate) ↔ OrderModel (persistence object)
- OrderItem (domain entity) ↔ OrderItemModel (persistence object)

Key features:
- Zero-config automatic mapping via type analysis
- Automatic ID/Enum conversion
- Automatic child entity mapping
- Automatic event cleanup

Note:
    Audit fields (created_at, updated_at, etc.) are populated by Interceptors.
"""

from applications.ecommerce.modules.order.domain.order import Order, OrderItem
from applications.ecommerce.modules.order.persistence.models import OrderItemModel, OrderModel
from bento.application.mapper import AutoMapper


class OrderItemMapper(AutoMapper[OrderItem, OrderItemModel]):
    """Mapper for OrderItem ↔ OrderItemModel conversion.

    Framework automatically handles:
    - id: EntityId ↔ str
    - product_id: ID ↔ str
    - product_name, quantity, unit_price: direct copy
    """

    def __init__(self) -> None:
        """Initialize with automatic type analysis."""
        super().__init__(OrderItem, OrderItemModel)
        # order_id will be set by parent mapper
        self.ignore_fields("order_id")

    def after_map(self, domain: OrderItem, po: OrderItemModel) -> None:
        """Ensure kind has a sensible default when constructing transient PO."""
        if not getattr(po, "kind", None):
            po.kind = "simple"


class OrderMapper(AutoMapper[Order, OrderModel]):
    """Mapper for Order ↔ OrderModel conversion.

    Framework automatically handles:
    - id, customer_id: ID ↔ str
    - status: OrderStatus (Enum) ↔ str
    - paid_at, cancelled_at: datetime (direct copy)
    - items: automatic child mapping via registered mapper
    - Event cleanup after map_reverse

    Example:
        ```python
        mapper = OrderMapper()

        # Domain to Persistence
        order = Order(order_id=ID.generate(), customer_id=customer_id)
        order_model = mapper.map(order)

        # Persistence to Domain
        order_model = session.get(OrderModel, order_id)
        order = mapper.map_reverse(order_model)
        ```
    """

    def __init__(self) -> None:
        """Initialize with automatic type analysis and child registration."""
        super().__init__(
            Order,
            OrderModel,
            # Wire factories now (straight-through); ready for future polymorphism
            domain_factory=self._build_domain,
            po_factory=self._build_po,
        )
        # Register child entity mapper - items are automatically mapped
        self.register_child("items", OrderItemMapper(), parent_keys="order_id")

    def _build_domain(self, d: dict) -> Order:
        """Domain factory: place to enforce invariants or polymorphic construction."""
        # Adapt keys to domain constructor (Order expects order_id instead of id)
        d2 = dict(d)
        if "id" in d2 and "order_id" not in d2:
            d2["order_id"] = d2.pop("id")
        # If required keys are missing, hydrate from PO captured in before_map_reverse
        po = getattr(self, "_po_for_factory", None)
        if po is not None:
            if "order_id" not in d2 and hasattr(po, "id"):
                d2["order_id"] = po.id
            if "customer_id" not in d2 and hasattr(po, "customer_id"):
                d2["customer_id"] = po.customer_id
        return Order(**d2)  # type: ignore[arg-type]

    @staticmethod
    def _build_po(d: dict) -> OrderModel:
        """PO factory: place to construct ORM/Pydantic models or handle polymorphism."""
        # Infer discriminators if missing (simple heuristics)
        d2 = dict(d)
        if not d2.get("payment_method"):
            if d2.get("payment_card_last4") or d2.get("payment_card_brand"):
                d2["payment_method"] = "card"
            elif d2.get("payment_paypal_payer_id"):
                d2["payment_method"] = "paypal"
        if not d2.get("shipment_carrier"):
            if d2.get("shipment_tracking_no"):
                # naive default; real code can examine tracking patterns
                d2["shipment_carrier"] = "fedex"
        return OrderModel(**d2)  # type: ignore[arg-type]

    # Bridge missing inferred fields (e.g., SQLAlchemy Mapped typing edge cases)
    def after_map(self, domain: Order, po: OrderModel) -> None:
        """Ensure polymorphic fields are propagated when not inferred."""
        for name in (
            "payment_method",
            "payment_card_last4",
            "payment_card_brand",
            "payment_paypal_payer_id",
            "shipment_carrier",
            "shipment_tracking_no",
            "shipment_service",
        ):
            dv = getattr(domain, name, None)
            if dv is not None and getattr(po, name, None) is None:
                setattr(po, name, dv)
        # Heuristic inference when still missing
        if getattr(po, "payment_method", None) is None:
            if getattr(po, "payment_card_last4", None) or getattr(po, "payment_card_brand", None):
                po.payment_method = "card"
            elif getattr(po, "payment_paypal_payer_id", None):
                po.payment_method = "paypal"
        if getattr(po, "shipment_carrier", None) is None and getattr(
            po, "shipment_tracking_no", None
        ):
            po.shipment_carrier = "fedex"

    def before_map_reverse(self, po: OrderModel) -> None:
        """Capture PO for factory use (to hydrate required ctor args)."""
        self._po_for_factory = po

    def after_map_reverse(self, po: OrderModel, domain: Order) -> None:
        """Ensure polymorphic fields are propagated back to domain."""
        # Clear captured reference
        if hasattr(self, "_po_for_factory"):
            delattr(self, "_po_for_factory")
        for name in (
            "payment_method",
            "payment_card_last4",
            "payment_card_brand",
            "payment_paypal_payer_id",
            "shipment_carrier",
            "shipment_tracking_no",
            "shipment_service",
        ):
            pv = getattr(po, name, None)
            if pv is not None and getattr(domain, name, None) is None:
                setattr(domain, name, pv)
