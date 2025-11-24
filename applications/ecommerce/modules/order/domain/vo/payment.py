class Payment:
    """Abstract payment value object."""

    method: str


class PaymentCard(Payment):
    def __init__(self, last4: str, brand: str) -> None:
        self.method = "card"
        self.last4 = last4
        self.brand = brand

    def __repr__(self) -> str:
        return f"PaymentCard(last4={self.last4!r}, brand={self.brand!r})"


class PaymentPaypal(Payment):
    def __init__(self, payer_id: str) -> None:
        self.method = "paypal"
        self.payer_id = payer_id

    def __repr__(self) -> str:
        return f"PaymentPaypal(payer_id={self.payer_id!r})"
