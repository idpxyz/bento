"""Order aggregate root and entities."""

from datetime import datetime
from decimal import Decimal

from applications.ecommerce.modules.order.domain.events import (
    OrderCancelled,
    OrderCreated,
    OrderPaid,
)
from applications.ecommerce.modules.order.domain.order_status import OrderStatus
from applications.ecommerce.modules.order.domain.vo import (
    Address,
    Money,
    Payment,
    Shipment,
)
from applications.ecommerce.modules.order.errors import OrderErrors
from bento.core.errors import DomainException
from bento.core.ids import ID
from bento.domain.aggregate import AggregateRoot
from bento.domain.entity import Entity


def _coerce_money(
    value: Money | Decimal | float | str | None,
    *,
    currency: str,
) -> Money | None:
    if value is None:
        return None
    if isinstance(value, Money):
        return value
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, (int, float)):
        amount = Decimal(str(value))
    elif isinstance(value, str):
        amount = Decimal(value)
    else:  # pragma: no cover - defensive
        raise TypeError(f"Unsupported money value type: {type(value)!r}")
    return Money(amount=amount, currency=currency)


def _prepare_money_value(
    value: Money | Decimal | float | str | None,
    *,
    currency: str,
    error_key: str,
) -> Money | None:
    money = _coerce_money(value, currency=currency)
    if money is not None and money.amount < Decimal("0"):
        raise DomainException(
            error_code=OrderErrors.INVALID_ORDER_AMOUNT,
            details={error_key: str(money.amount)},
        )
    return money


def _normalize_money_currency(money: Money | None, *, currency: str) -> Money | None:
    if money is None:
        return None
    if money.currency == currency:
        return money
    return Money(amount=money.amount, currency=currency)


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


class LineSimple(OrderItem):
    """Simple order line (default)."""


class LineBundle(OrderItem):
    """Bundle line (composed product)."""


class LineCustom(OrderItem):
    """Custom line (manual)."""


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
    # Address
    shipping_address: Address | None
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
        self._discount_amount_internal: Money | None = None
        self._tax_amount_internal: Money | None = None
        # Address default
        self.shipping_address = None
        # Currency default
        self._currency = "USD"
        # Price adjustments
        self.discounts = []
        self.tax_lines = []

        # Publish created event immediately for downstream listeners
        self.add_event(
            OrderCreated(
                order_id=ID(self.id.value),
                customer_id=self.customer_id,
                total_amount=float(self.total_amount),
            )
        )

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

    @property
    def currency(self) -> str:
        return self._currency

    @currency.setter
    def currency(self, value: str) -> None:
        self._currency = value
        # Re-normalize existing money fields to keep currency aligned
        self._discount_amount_internal = _normalize_money_currency(
            self._discount_amount_internal, currency=self.currency
        )
        self._tax_amount_internal = _normalize_money_currency(
            self._tax_amount_internal, currency=self.currency
        )

    @property
    def discount_amount(self) -> Money | None:
        return self._discount_amount_internal

    @discount_amount.setter
    def discount_amount(self, value: Money | Decimal | float | str | None) -> None:
        self._discount_amount_internal = _prepare_money_value(
            value, currency=self.currency, error_key="discount_amount"
        )

    @property
    def tax_amount(self) -> Money | None:
        return self._tax_amount_internal

    @tax_amount.setter
    def tax_amount(self, value: Money | Decimal | float | str | None) -> None:
        self._tax_amount_internal = _prepare_money_value(
            value, currency=self.currency, error_key="tax_amount"
        )

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

    def to_dict(self) -> dict:
        return {
            "id": self.id.value if hasattr(self.id, "value") else str(self.id),
            "customer_id": self.customer_id.value
            if hasattr(self.customer_id, "value")
            else str(self.customer_id),
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "items": [
                {
                    "id": (item.id.value if hasattr(item.id, "value") else str(item.id)),
                    "product_id": item.product_id.value
                    if hasattr(item.product_id, "value")
                    else str(item.product_id),
                    "product_name": item.product_name,
                    "quantity": int(item.quantity),
                    "unit_price": str(item.unit_price.amount)
                    if hasattr(item.unit_price, "amount")
                    else str(item.unit_price),
                }
                for item in self.items
            ],
            "items_count": self.items_count,
            "total_amount": float(self.total_amount),
            "created_at": self.created_at,
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
