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

from decimal import Decimal

from applications.ecommerce.modules.order.domain.order import (
    Address,
    Discount,
    LineBundle,
    LineCustom,
    LineSimple,
    Money,
    Order,
    OrderItem,
    Payment,
    PaymentCard,
    PaymentPaypal,
    Shipment,
    ShipmentFedex,
    ShipmentLocal,
    TaxLine,
)
from applications.ecommerce.modules.order.persistence.models import (
    OrderDiscountModel,
    OrderItemModel,
    OrderModel,
    OrderTaxLineModel,
)
from bento.application.mapper import AutoMapper
from bento.core.ids import ID


class OrderItemMapper(AutoMapper[OrderItem, OrderItemModel]):
    """Mapper for OrderItem ↔ OrderItemModel conversion.

    Framework automatically handles:
    - id: EntityId ↔ str
    - product_id: ID ↔ str
    - product_name, quantity, unit_price: direct copy
    """

    def __init__(self) -> None:
        """Initialize with automatic type analysis."""
        super().__init__(OrderItem, OrderItemModel, domain_factory=self._build_domain)
        # Explicitly restrict fields to ensure reverse construction calls __init__ with all args
        self.only_fields("product_id", "product_name", "quantity", "unit_price")
        # order_id will be set by parent mapper
        self.ignore_fields("order_id")
        # ensure discriminator is handled by hooks/factory
        self.ignore_fields("kind")
        # explicit converters to bypass SQLAlchemy Mapped[...] typing wrappers
        self.override_field(
            "product_id",
            to_po=lambda v: (None if v is None else (v.value if hasattr(v, "value") else str(v))),
            from_po=lambda v: (None if v is None else ID(str(v))),
        )
        self.override_field(
            "product_name",
            to_po=lambda v: v,
            from_po=lambda v: v,
        )
        self.override_field(
            "quantity",
            to_po=lambda v: v,
            from_po=lambda v: (None if v is None else int(v)),
        )
        # unit_price: Money(amount) ↔ Decimal（currency 由父级 Order.currency 承载）
        self.override_field(
            "unit_price",
            to_po=lambda m: (
                None if m is None else (m.amount if hasattr(m, "amount") else Decimal(str(m)))
            ),
            from_po=lambda v: (None if v is None else Money(Decimal(str(v)), "USD")),
        )

    def after_map(self, domain: OrderItem, po: OrderItemModel) -> None:
        """Ensure kind has a sensible default when constructing transient PO."""
        if isinstance(domain, LineBundle):
            po.kind = "bundle"
        elif isinstance(domain, LineCustom):
            po.kind = "custom"
        else:
            if not getattr(po, "kind", None):
                po.kind = "simple"

    def _build_domain(self, d: dict) -> OrderItem:
        """Construct domain subclass based on kind."""
        kind = d.pop("kind", None)
        if kind is None:
            po = getattr(self, "_po_for_factory", None)
            if po is not None:
                kind = getattr(po, "kind", None)
        ctor = {
            "bundle": LineBundle,
            "custom": LineCustom,
            "simple": LineSimple,
            None: LineSimple,
        }.get(kind, LineSimple)
        return ctor(**d)  # type: ignore[arg-type]

    def before_map_reverse(self, po: OrderItemModel) -> None:
        self._po_for_factory = po

    def after_map_reverse(self, po: OrderItemModel, domain: OrderItem) -> None:
        if hasattr(self, "_po_for_factory"):
            delattr(self, "_po_for_factory")

    # Fallback: when type analysis yields no field mappings (standalone usage in tests)
    def map(self, domain: OrderItem) -> OrderItemModel:  # type: ignore[override]
        try:
            return super().map(domain)
        except AssertionError:
            po = OrderItemModel(
                id=None,
                order_id=None,
                product_id=domain.product_id.value
                if hasattr(domain.product_id, "value")
                else str(domain.product_id),
                product_name=domain.product_name,
                quantity=int(domain.quantity),
                unit_price=domain.unit_price.amount
                if hasattr(domain.unit_price, "amount")
                else Decimal(str(domain.unit_price)),
            )
            # set kind via same logic
            self.after_map(domain, po)
            return po


class OrderDiscountMapper(AutoMapper[Discount, OrderDiscountModel]):
    def __init__(self) -> None:
        super().__init__(Discount, OrderDiscountModel)
        self.ignore_fields("order_id")
        self.override_field(
            "amount",
            to_po=lambda m: (None if m is None else m.amount),
            from_po=lambda v: (None if v is None else Money(Decimal(str(v)), "USD")),
        )


class OrderTaxLineMapper(AutoMapper[TaxLine, OrderTaxLineModel]):
    def __init__(self) -> None:
        super().__init__(TaxLine, OrderTaxLineModel)
        self.ignore_fields("order_id")
        self.override_field(
            "amount",
            to_po=lambda m: (None if m is None else m.amount),
            from_po=lambda v: (None if v is None else Money(Decimal(str(v)), "USD")),
        )


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
        self.register_child("discounts", OrderDiscountMapper(), parent_keys="order_id")
        self.register_child("tax_lines", OrderTaxLineMapper(), parent_keys="order_id")
        # 订单级金额字段使用 Decimal，覆盖策略不再转换为字符串

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
        # If explicit payment object exists, project it to flattened fields
        if isinstance(getattr(domain, "payment", None), Payment):
            p = domain.payment  # type: ignore[assignment]
            if isinstance(p, PaymentCard):
                po.payment_method = "card"
                po.payment_card_last4 = p.last4
                po.payment_card_brand = p.brand
            elif isinstance(p, PaymentPaypal):
                po.payment_method = "paypal"
                po.payment_paypal_payer_id = p.payer_id
        # If explicit shipment object exists, project it
        if isinstance(getattr(domain, "shipment", None), Shipment):
            s = domain.shipment  # type: ignore[assignment]
            if isinstance(s, ShipmentFedex):
                po.shipment_carrier = "fedex"
                po.shipment_tracking_no = s.tracking_no
                po.shipment_service = s.service
            elif isinstance(s, ShipmentLocal):
                po.shipment_carrier = "local"
                po.shipment_tracking_no = s.tracking_no
                po.shipment_service = s.service
        # Project shipping_address if present
        if isinstance(getattr(domain, "shipping_address", None), Address):
            a = domain.shipping_address
            if a:
                po.shipping_address_line1 = a.line1
                po.shipping_city = a.city
                po.shipping_country = a.country

        for name in (
            "payment_method",
            "payment_card_last4",
            "payment_card_brand",
            "payment_paypal_payer_id",
            "shipment_carrier",
            "shipment_tracking_no",
            "shipment_service",
            # order-level money fields
            "discount_amount",
            "tax_amount",
            # currency
            "currency",
        ):
            dv = getattr(domain, name, None)
            if dv is not None and getattr(po, name, None) is None:
                if name in ("discount_amount", "tax_amount") and isinstance(dv, Decimal):
                    setattr(po, name, str(dv))
                else:
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
        # Fallback: rebuild items if child mapping failed silently
        if (not getattr(po, "items", None)) and getattr(domain, "items", None):
            rebuilt = []
            for item in domain.items:
                try:
                    rebuilt.append(
                        OrderItemModel(
                            id=str(item.id.value) if hasattr(item, "id") else None,
                            order_id=str(domain.id.value),
                            product_id=item.product_id.value
                            if hasattr(item.product_id, "value")
                            else str(item.product_id),
                            product_name=item.product_name,
                            quantity=int(item.quantity),
                            unit_price=(
                                item.unit_price.amount
                                if hasattr(item.unit_price, "amount")
                                else Decimal(str(item.unit_price))
                            ),
                        )
                    )
                except Exception:
                    continue
            po.items = rebuilt
        # Ensure item kinds are set based on domain subclasses
        if getattr(domain, "items", None) and getattr(po, "items", None):
            for d_item, p_item in zip(domain.items, po.items, strict=False):
                if getattr(p_item, "kind", None) in (None, ""):
                    if isinstance(d_item, LineBundle):
                        p_item.kind = "bundle"
                    elif isinstance(d_item, LineCustom):
                        p_item.kind = "custom"
                    else:
                        p_item.kind = "simple"

    def before_map_reverse(self, po: OrderModel) -> None:
        """Capture PO for factory use (to hydrate required ctor args)."""
        self._po_for_factory = po

    def after_map_reverse(self, po: OrderModel, domain: Order) -> None:
        """Ensure polymorphic fields are propagated back to domain."""
        # Clear captured reference
        if hasattr(self, "_po_for_factory"):
            delattr(self, "_po_for_factory")
        # Rebuild explicit payment/shipment objects if possible
        if po.payment_method == "card" and (po.payment_card_last4 or po.payment_card_brand):
            domain.payment = PaymentCard(
                last4=po.payment_card_last4 or "",
                brand=po.payment_card_brand or "",
            )
        elif po.payment_method == "paypal" and po.payment_paypal_payer_id:
            domain.payment = PaymentPaypal(payer_id=po.payment_paypal_payer_id)
        else:
            domain.payment = None

        if po.shipment_carrier == "fedex":
            domain.shipment = ShipmentFedex(
                tracking_no=po.shipment_tracking_no or "",
                service=po.shipment_service,
            )
        elif po.shipment_carrier == "local":
            domain.shipment = ShipmentLocal(
                tracking_no=po.shipment_tracking_no,
                service=po.shipment_service,
            )
        else:
            domain.shipment = None
        # Rebuild shipping_address if fields present
        if po.shipping_address_line1 and po.shipping_city and po.shipping_country:
            domain.shipping_address = Address(
                line1=po.shipping_address_line1,
                city=po.shipping_city,
                country=po.shipping_country,
            )
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
        # Money fields: always refresh from PO if present (convert to Decimal)
        if getattr(po, "discount_amount", None) is not None:
            domain.discount_amount = Money(Decimal(str(po.discount_amount)), domain.currency)
        if getattr(po, "tax_amount", None) is not None:
            domain.tax_amount = Money(Decimal(str(po.tax_amount)), domain.currency)
        # Currency (narrow Optional[str] before assignment to str)
        c = getattr(po, "currency", None)
        if c is not None:
            domain.currency = c
        # Fallback: rebuild items if child reverse mapping was skipped
        if (not getattr(domain, "items", None)) and getattr(po, "items", None):
            rebuilt: list[OrderItem] = []
            for item_po in po.items:
                try:
                    ctor = {  # ctor 是子类构造函数
                        "bundle": LineBundle,
                        "custom": LineCustom,
                        "simple": LineSimple,
                        None: LineSimple,
                    }.get(getattr(item_po, "kind", None), LineSimple)
                    rebuilt.append(
                        ctor(
                            product_id=ID(str(item_po.product_id)),
                            product_name=item_po.product_name,
                            quantity=int(item_po.quantity),
                            unit_price=Money(Decimal(str(item_po.unit_price)), domain.currency),
                        )
                    )
                except Exception:
                    # skip invalid rows
                    continue
            domain.items = rebuilt
