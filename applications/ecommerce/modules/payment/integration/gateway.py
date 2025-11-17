from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class PaymentAuthorizationRequest:
    order_id: str
    customer_id: str
    amount: float
    currency: str = "USD"
    method: str = "card"
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class PaymentAuthorizationResult:
    authorized: bool
    authorization_id: str | None = None
    failure_reason: str | None = None


class PaymentGateway(Protocol):
    async def authorize(self, req: PaymentAuthorizationRequest) -> PaymentAuthorizationResult: ...


class FakePaymentGateway:
    """In-memory fake gateway with per-order outcomes for tests and local dev."""

    def __init__(self, default_success: bool = True) -> None:
        self.default_success = default_success
        self._order_overrides: dict[str, PaymentAuthorizationResult] = {}

    def set_override(self, order_id: str, *, success: bool, reason: str | None = None) -> None:
        if success:
            self._order_overrides[order_id] = PaymentAuthorizationResult(
                authorized=True, authorization_id=f"auth-{order_id}", failure_reason=None
            )
        else:
            self._order_overrides[order_id] = PaymentAuthorizationResult(
                authorized=False, authorization_id=None, failure_reason=reason or "payment_failed"
            )

    async def authorize(self, req: PaymentAuthorizationRequest) -> PaymentAuthorizationResult:
        if req.order_id in self._order_overrides:
            return self._order_overrides[req.order_id]
        if self.default_success:
            return PaymentAuthorizationResult(
                authorized=True,
                authorization_id=f"auth-{req.order_id}",
                failure_reason=None,
            )
        return PaymentAuthorizationResult(
            authorized=False,
            authorization_id=None,
            failure_reason="payment_failed",
        )
