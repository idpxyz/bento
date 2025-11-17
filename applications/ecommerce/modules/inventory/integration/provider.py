from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ReserveItem:
    product_id: str
    quantity: int


@dataclass
class ReserveResult:
    success: bool
    reason: str | None = None


class InventoryProvider(Protocol):
    async def reserve(
        self,
        *,
        order_id: str,
        customer_id: str,
        items: list[ReserveItem],
    ) -> ReserveResult: ...

    async def release(self, *, order_id: str) -> None: ...


class InMemoryInventoryProvider:
    """Simple in-memory inventory for tests/local dev.

    Tracks per-product available and reserved quantities and per-order reservations
    to enable releasing on failure paths.
    """

    def __init__(self) -> None:
        self._stock: dict[str, dict[str, int]] = {}  # pid -> {available, reserved}
        self._reservations: dict[str, list[tuple[str, int]]] = {}  # order_id -> [(pid, qty)]

    def set_stock(self, product_id: str, *, available: int) -> None:
        self._stock[product_id] = {"available": available, "reserved": 0}

    async def reserve(
        self,
        *,
        order_id: str,
        customer_id: str,
        items: list[ReserveItem],
    ) -> ReserveResult:
        # Check availability for all items
        for it in items:
            st = self._stock.get(it.product_id) or {"available": 0, "reserved": 0}
            if st["available"] < it.quantity:
                return ReserveResult(success=False, reason="insufficient_stock")

        # Apply reservation
        reserved_pairs: list[tuple[str, int]] = []
        for it in items:
            st = self._stock.setdefault(it.product_id, {"available": 0, "reserved": 0})
            st["available"] -= it.quantity
            st["reserved"] += it.quantity
            reserved_pairs.append((it.product_id, it.quantity))

        self._reservations[order_id] = reserved_pairs
        return ReserveResult(success=True)

    async def release(self, *, order_id: str) -> None:
        pairs = self._reservations.pop(order_id, [])
        for pid, qty in pairs:
            st = self._stock.setdefault(pid, {"available": 0, "reserved": 0})
            st["available"] += qty
            st["reserved"] -= qty
