from __future__ import annotations

from decimal import Decimal


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

    def __repr__(self) -> str:
        return f"Money(amount={self.amount!r}, currency={self.currency!r})"
