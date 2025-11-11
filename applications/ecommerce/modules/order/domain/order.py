"""Order aggregate root and entities."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from applications.ecommerce.modules.order.domain.events import (
    OrderCancelled,
    OrderCreated,
    OrderPaid,
)
from applications.ecommerce.modules.order.domain.order_status import OrderStatus
from applications.ecommerce.modules.order.errors import OrderErrors
from bento.core.errors import DomainException
from bento.core.ids import ID
from bento.domain.aggregate import AggregateRoot
from bento.domain.entity import Entity


class Payment:
    """Abstract payment value object."""

    method: str


class PaymentCard(Payment):
    def __init__(self, last4: str, brand: str) -> None:
        self.method = "card"
        self.last4 = last4
        self.brand = brand


class PaymentPaypal(Payment):
    def __init__(self, payer_id: str) -> None:
        self.method = "paypal"
        self.payer_id = payer_id


class Shipment:
    """Abstract shipment value object."""

    carrier: str


class ShipmentFedex(Shipment):
    def __init__(self, tracking_no: str, service: str | None = None) -> None:
        self.carrier = "fedex"
        self.tracking_no = tracking_no
        self.service = service


class ShipmentLocal(Shipment):
    def __init__(self, tracking_no: str | None = None, service: str | None = None) -> None:
        self.carrier = "local"
        self.tracking_no = tracking_no
        self.service = service


class Address:
    """Simple postal address value object."""

    def __init__(self, line1: str, city: str, country: str) -> None:
        self.line1 = line1
        self.city = city
        self.country = country


class Money:
    """Simple money value object with explicit currency."""

    def __init__(self, amount: Decimal, currency: str) -> None:
        self.amount = amount
        self.currency = currency

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Money):
            return self.amount == other.amount and self.currency == other.currency
        if isinstance(other, (int, float, Decimal)):
            return self.amount == Decimal(str(other))
        return False


class OrderItem(Entity):
    """Order item entity.

    Represents a product in an order with quantity and price.
    """

    product_id: ID
    product_name: str
    quantity: int
    unit_price: "Money"  # type: ignore[assignment]

    def __init__(
        self,
        product_id: ID,
        product_name: str,
        quantity: int,
        unit_price: Money | Decimal | float,
        currency: str | None = None,
    ) -> None:
        """Initialize order item.

        Args:
            product_id: Product identifier
            product_name: Product name
            quantity: Quantity ordered
            unit_price: Price per unit

        Raises:
            DomainException: If quantity is invalid
        """
        from bento.core.ids import EntityId

        super().__init__(id=EntityId.generate())

        if quantity <= 0:
            raise DomainException(
                error_code=OrderErrors.INVALID_QUANTITY, details={"quantity": quantity}
            )

        # normalize unit_price to Money
        if isinstance(unit_price, Money):
            price = unit_price
        else:
            amount = unit_price if isinstance(unit_price, Decimal) else Decimal(str(unit_price))
            price = Money(amount=amount, currency=currency or "USD")
        if price.amount <= Decimal("0"):
            raise DomainException(
                error_code=OrderErrors.INVALID_ORDER_AMOUNT,
                details={"unit_price": str(price.amount)},
            )

        self.product_id = product_id
        self.product_name = product_name
        self.quantity = quantity
        self.unit_price: Money = price

    @property
    def subtotal(self) -> Decimal:
        """Calculate subtotal for this item."""
        return Decimal(self.quantity) * self.unit_price.amount

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id.value,
            "product_id": self.product_id.value,
            "product_name": self.product_name,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "subtotal": self.subtotal,
        }


class LineSimple(OrderItem):
    """Simple order line (default)."""

    pass


class LineBundle(OrderItem):
    """Bundle line (composed product)."""

    pass


class LineCustom(OrderItem):
    """Custom line (manual)."""

    pass


class Order(AggregateRoot):
    """Order aggregate root.

    Manages the order lifecycle and business rules.

    Example:
        ```python
        # Create order
        order = Order(order_id=ID.generate(), customer_id=customer_id)

        # Add items
        order.add_item(
            product_id=product_id,
            product_name="Product A",
            quantity=2,
            unit_price=99.99
        )

        # Pay order
        order.pay()

        # Cancel order
        order.cancel(reason="Customer request")
        ```
    """

    # Polymorphic/discriminator-ready fields (optional, declared for type analysis)
    payment_method: str | None
    payment_card_last4: str | None
    payment_card_brand: str | None
    payment_paypal_payer_id: str | None
    shipment_carrier: str | None
    shipment_tracking_no: str | None
    shipment_service: str | None
    # Explicit polymorphic objects (optional, for richer domain usage)
    payment: Payment | None
    shipment: Shipment | None
    # Order-level money fields
    discount_amount: Money | None
    tax_amount: Money | None
    # Address
    shipping_address: Address | None
    # Currency for monetary values
    currency: str
    # Discounts / Taxes
    discounts: list["Discount"]
    tax_lines: list["TaxLine"]

    def __init__(
        self,
        order_id: ID,
        customer_id: ID,
    ) -> None:
        """Initialize order.

        Args:
            order_id: Order identifier
            customer_id: Customer identifier
        """
        super().__init__(order_id)
        self.customer_id = customer_id
        self.items: list[OrderItem] = []
        self.status = OrderStatus.PENDING
        self.created_at = datetime.now()
        self.paid_at: datetime | None = None
        self.cancelled_at: datetime | None = None
        # Initialize optional discriminators
        self.payment_method = None  # e.g., "card", "paypal", "cod"
        self.payment_card_last4 = None
        self.payment_card_brand = None
        self.payment_paypal_payer_id = None
        self.shipment_carrier = None  # e.g., "local", "fedex", "dhl"
        self.shipment_tracking_no = None
        self.shipment_service = None
        # Polymorphic objects default
        self.payment = None
        self.shipment = None
        # Money fields default
        self.discount_amount = None
        self.tax_amount = None
        # Address default
        self.shipping_address = None
        # Currency default
        self.currency = "USD"
        # Price adjustments
        self.discounts = []
        self.tax_lines = []
        # Publish created event
        self.add_event(
            OrderCreated(
                order_id=ID(self.id.value),
                customer_id=self.customer_id,
                total_amount=float(self.total_amount),
            )
        )

        # Note: OrderCreated event will be published after items are added
        # to ensure total_amount is accurate

    @property
    def total_amount(self) -> float:
        """Calculate total amount of the order."""
        total = Decimal("0")
        for item in self.items:
            total += item.subtotal
        return float(total)

    @property
    def total_money(self) -> Money:
        """Return total as Money with order currency."""
        # total_amount is float; reconstruct Decimal from precise sum
        precise = Decimal("0")
        for item in self.items:
            precise += item.subtotal
        for d in self.discounts:
            precise -= d.amount.amount
        for t in self.tax_lines:
            precise += t.amount.amount
        return Money(precise, self.currency)

    @property
    def total_amount_float(self) -> float:
        """Compatibility helper: total as float (for legacy checks/tests)."""
        return float(self.total_amount)

    @property
    def items_count(self) -> int:
        """Get total number of items."""
        return len(self.items)

    def add_item(
        self,
        product_id: ID,
        product_name: str,
        quantity: int,
        unit_price: Money | Decimal | float,
        currency: str | None = None,
    ) -> None:
        """Add an item to the order.

        Args:
            product_id: Product identifier
            product_name: Product name
            quantity: Quantity to order
            unit_price: Price per unit

        Raises:
            DomainException: If order cannot be modified
        """
        # Business rule: Cannot modify paid or cancelled orders
        if self.status == OrderStatus.PAID:
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_PAID,
                details={"order_id": self.id.value, "status": self.status.value},
            )

        if self.status == OrderStatus.CANCELLED:
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_CANCELLED,
                details={"order_id": self.id.value, "status": self.status.value},
            )

        # Create and add item
        item = OrderItem(
            product_id=product_id,
            product_name=product_name,
            quantity=quantity,
            unit_price=unit_price,
            currency=currency or self.currency,
        )
        self.items.append(item)

    def remove_item(self, item_id: ID) -> None:
        """Remove an item from the order.

        Args:
            item_id: Item identifier to remove

        Raises:
            DomainException: If order cannot be modified or item not found
        """
        # Business rule: Cannot modify paid or cancelled orders
        if self.status == OrderStatus.PAID:
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_PAID, details={"order_id": self.id.value}
            )

        if self.status == OrderStatus.CANCELLED:
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_CANCELLED, details={"order_id": self.id.value}
            )

        # Remove item
        self.items = [item for item in self.items if item.id != item_id]

    def pay(self) -> None:
        """Pay for the order.

        Raises:
            DomainException: If order cannot be paid
        """
        # Business rule: Order must have items
        if not self.items:
            raise DomainException(
                error_code=OrderErrors.EMPTY_ORDER_ITEMS, details={"order_id": self.id.value}
            )

        # Business rule: Cannot pay twice
        if self.status == OrderStatus.PAID:
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_PAID, details={"order_id": self.id.value}
            )

        # Business rule: Cannot pay cancelled order
        if self.status == OrderStatus.CANCELLED:
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_CANCELLED, details={"order_id": self.id.value}
            )

        # Change status
        self.status = OrderStatus.PAID
        self.paid_at = datetime.now()

        # Publish paid event
        self.add_event(
            OrderPaid(
                order_id=ID(self.id.value),
                customer_id=self.customer_id,
                total_amount=self.total_amount,
                paid_at=self.paid_at,
            )
        )

    def cancel(self, reason: str | None = None) -> None:
        """Cancel the order.

        Args:
            reason: Optional cancellation reason

        Raises:
            DomainException: If order cannot be cancelled
        """
        # Business rule: Cannot cancel paid order
        if self.status == OrderStatus.PAID:
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_PAID,
                details={
                    "order_id": self.id.value,
                    "message": "Cannot cancel paid order. Request refund instead.",
                },
            )

        # Business rule: Cannot cancel twice
        if self.status == OrderStatus.CANCELLED:
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_CANCELLED, details={"order_id": self.id.value}
            )

        # Change status
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.now()

        # Publish cancelled event
        self.add_event(
            OrderCancelled(
                order_id=ID(self.id.value),
                customer_id=self.customer_id,
                reason=reason,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert order to dictionary.

        Returns:
            Dictionary representation of the order
        """
        return {
            "id": self.id.value,
            "customer_id": self.customer_id.value,
            "status": self.status.value,
            "items": [item.to_dict() for item in self.items],
            "items_count": self.items_count,
            "total_amount": self.total_amount,
            "created_at": self.created_at.isoformat(),
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "payment_method": self.payment_method,
            "payment_card_last4": self.payment_card_last4,
            "payment_card_brand": self.payment_card_brand,
            "payment_paypal_payer_id": self.payment_paypal_payer_id,
            "shipment_carrier": self.shipment_carrier,
            "shipment_tracking_no": self.shipment_tracking_no,
            "shipment_service": self.shipment_service,
        }


class Discount:
    """Order discount value (amount off)."""

    id: ID
    amount: Money
    reason: str | None

    def __init__(self, amount: Money, reason: str | None = None, id: ID | None = None) -> None:
        self.id = id or ID.generate()
        self.amount = amount
        self.reason = reason


class TaxLine:
    """Order tax value (amount added)."""

    id: ID
    amount: Money
    tax_type: str | None

    def __init__(self, amount: Money, tax_type: str | None = None, id: ID | None = None) -> None:
        self.id = id or ID.generate()
        self.amount = amount
        self.tax_type = tax_type
