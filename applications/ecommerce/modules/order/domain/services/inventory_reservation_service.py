"""Inventory reservation domain service.

This module demonstrates Domain Service best practices for cross-aggregate coordination:
- Coordinates between Order and Inventory aggregates
- Manages inventory reservation lifecycle
- Ensures data consistency across aggregates
- Stateless service design
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4


class ReservationStatus(str, Enum):
    """Status of inventory reservation."""

    PENDING = "pending"  # Reservation requested
    CONFIRMED = "confirmed"  # Reservation confirmed
    EXPIRED = "expired"  # Reservation timed out
    RELEASED = "released"  # Reservation released/cancelled
    FULFILLED = "fulfilled"  # Order completed, inventory deducted


class StockStatus(str, Enum):
    """Product stock availability status."""

    IN_STOCK = "in_stock"  # Available
    LOW_STOCK = "low_stock"  # Below threshold
    OUT_OF_STOCK = "out_of_stock"  # Not available
    DISCONTINUED = "discontinued"  # No longer available


@dataclass
class InventoryItem:
    """Represents an inventory item.

    Best Practice:
    - Encapsulate inventory state
    - Immutable representation for service operations
    """

    product_id: str
    available_quantity: int
    reserved_quantity: int = 0
    total_quantity: int = 0
    low_stock_threshold: int = 10

    def __post_init__(self):
        if self.total_quantity == 0:
            self.total_quantity = self.available_quantity + self.reserved_quantity

    @property
    def stock_status(self) -> StockStatus:
        """Determine stock status based on available quantity."""
        if self.available_quantity == 0:
            return StockStatus.OUT_OF_STOCK
        elif self.available_quantity <= self.low_stock_threshold:
            return StockStatus.LOW_STOCK
        return StockStatus.IN_STOCK


@dataclass
class ReservationRequest:
    """Request to reserve inventory.

    Best Practice:
    - Explicit request object
    - Contains all necessary information
    - Validates input data
    """

    product_id: str
    quantity: int
    order_id: str
    customer_id: str
    reservation_duration_minutes: int = 15  # Default 15 minutes


@dataclass
class Reservation:
    """Represents an inventory reservation.

    Best Practice:
    - Complete reservation state
    - Tracks lifecycle
    - Supports audit trail
    """

    reservation_id: str
    product_id: str
    quantity: int
    order_id: str
    customer_id: str
    status: ReservationStatus
    created_at: datetime
    expires_at: datetime
    released_at: datetime | None = None

    def is_expired(self, current_time: datetime) -> bool:
        """Check if reservation has expired."""
        return self.status == ReservationStatus.PENDING and current_time >= self.expires_at

    def is_active(self) -> bool:
        """Check if reservation is active."""
        return self.status in [ReservationStatus.PENDING, ReservationStatus.CONFIRMED]


class InventoryReservationService:
    """Domain service for inventory reservation management.

    This service demonstrates:
    - Cross-aggregate coordination (Order + Inventory)
    - Reservation lifecycle management
    - Consistency guarantees
    - Time-based business rules

    Best Practices:
    - Stateless service design
    - Operates on aggregates but doesn't own them
    - Encapsulates complex cross-aggregate logic
    - Provides clear transaction boundaries

    Example:
        ```python
        service = InventoryReservationService()

        # Check availability
        available = service.check_availability(
            inventory_item,
            requested_quantity=5
        )

        # Reserve inventory
        request = ReservationRequest(
            product_id="PROD-123",
            quantity=5,
            order_id="ORD-456",
            customer_id="CUST-789"
        )
        reservation = service.reserve_inventory(request, inventory_item)
        ```
    """

    # Default reservation duration (in minutes)
    DEFAULT_RESERVATION_DURATION = 15

    # Low stock threshold percentage
    LOW_STOCK_THRESHOLD_PERCENTAGE = 0.2  # 20% of total stock

    def check_availability(
        self, inventory_item: InventoryItem, requested_quantity: int
    ) -> dict[str, Any]:
        """Check if requested quantity is available.

        Args:
            inventory_item: Current inventory state
            requested_quantity: Quantity requested

        Returns:
            Dictionary with availability information

        Best Practice:
        - Separate query from command
        - Provide detailed availability info
        - Support UI/business decisions
        """
        is_available = inventory_item.available_quantity >= requested_quantity
        stock_status = inventory_item.stock_status

        result = {
            "product_id": inventory_item.product_id,
            "requested_quantity": requested_quantity,
            "available_quantity": inventory_item.available_quantity,
            "is_available": is_available,
            "stock_status": stock_status.value,
        }

        # Add helpful messages
        if not is_available:
            if inventory_item.available_quantity == 0:
                result["message"] = "Product is out of stock"
            else:
                result["message"] = (
                    f"Only {inventory_item.available_quantity} units available. "
                    f"Requested: {requested_quantity}"
                )
        elif stock_status == StockStatus.LOW_STOCK:
            result["message"] = f"Only {inventory_item.available_quantity} units left"
        else:
            result["message"] = "Product is available"

        return result

    def reserve_inventory(
        self,
        request: ReservationRequest,
        inventory_item: InventoryItem,
        current_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Reserve inventory for an order.

        Args:
            request: Reservation request details
            inventory_item: Current inventory state
            current_time: Current timestamp (for testing)

        Returns:
            Reservation result with status

        Best Practice:
        - Command method with clear inputs
        - Returns domain event data
        - Validates business rules
        - Provides audit information
        """
        if current_time is None:
            current_time = datetime.now()

        # Validate availability
        availability = self.check_availability(inventory_item, request.quantity)

        if not availability["is_available"]:
            return {
                "success": False,
                "reason": "insufficient_stock",
                "message": availability["message"],
                "available_quantity": inventory_item.available_quantity,
                "requested_quantity": request.quantity,
            }

        # Create reservation
        reservation_id = str(uuid4())
        expires_at = current_time + timedelta(minutes=request.reservation_duration_minutes)

        reservation = Reservation(
            reservation_id=reservation_id,
            product_id=request.product_id,
            quantity=request.quantity,
            order_id=request.order_id,
            customer_id=request.customer_id,
            status=ReservationStatus.CONFIRMED,
            created_at=current_time,
            expires_at=expires_at,
        )

        # Calculate new inventory state
        new_available = inventory_item.available_quantity - request.quantity
        new_reserved = inventory_item.reserved_quantity + request.quantity

        return {
            "success": True,
            "reservation_id": reservation.reservation_id,
            "product_id": reservation.product_id,
            "quantity": reservation.quantity,
            "order_id": reservation.order_id,
            "status": reservation.status.value,
            "created_at": reservation.created_at.isoformat(),
            "expires_at": reservation.expires_at.isoformat(),
            "new_available_quantity": new_available,
            "new_reserved_quantity": new_reserved,
            "message": f"Successfully reserved {request.quantity} units",
        }

    def release_reservation(
        self,
        reservation: Reservation,
        reason: str = "cancelled",
        current_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Release a reservation back to available inventory.

        Args:
            reservation: Reservation to release
            reason: Reason for release
            current_time: Current timestamp (for testing)

        Returns:
            Release result

        Best Practice:
        - Handle cancellation/timeout scenarios
        - Restore inventory availability
        - Track release reasons for analytics
        """
        if current_time is None:
            current_time = datetime.now()

        # Check if already released
        if not reservation.is_active():
            return {
                "success": False,
                "reason": "already_released",
                "message": f"Reservation already in {reservation.status.value} state",
                "reservation_id": reservation.reservation_id,
            }

        # Release inventory
        released_reservation = Reservation(
            reservation_id=reservation.reservation_id,
            product_id=reservation.product_id,
            quantity=reservation.quantity,
            order_id=reservation.order_id,
            customer_id=reservation.customer_id,
            status=ReservationStatus.RELEASED,
            created_at=reservation.created_at,
            expires_at=reservation.expires_at,
            released_at=current_time,
        )

        return {
            "success": True,
            "reservation_id": released_reservation.reservation_id,
            "product_id": released_reservation.product_id,
            "quantity_released": released_reservation.quantity,
            "status": released_reservation.status.value,
            "released_at": current_time.isoformat(),
            "reason": reason,
            "message": f"Released {reservation.quantity} units back to inventory",
        }

    def fulfill_reservation(
        self, reservation: Reservation, current_time: datetime | None = None
    ) -> dict[str, Any]:
        """Mark reservation as fulfilled (order completed).

        Args:
            reservation: Reservation to fulfill
            current_time: Current timestamp (for testing)

        Returns:
            Fulfillment result

        Best Practice:
        - Final state for reservation lifecycle
        - Deduct from both reserved and total inventory
        - Generate event for downstream systems
        """
        if current_time is None:
            current_time = datetime.now()

        if not reservation.is_active():
            return {
                "success": False,
                "reason": "invalid_state",
                "message": f"Cannot fulfill reservation in {reservation.status.value} state",
                "reservation_id": reservation.reservation_id,
            }

        return {
            "success": True,
            "reservation_id": reservation.reservation_id,
            "product_id": reservation.product_id,
            "quantity_fulfilled": reservation.quantity,
            "status": ReservationStatus.FULFILLED.value,
            "fulfilled_at": current_time.isoformat(),
            "message": f"Order fulfilled, {reservation.quantity} units deducted from inventory",
        }

    def check_expired_reservations(
        self, reservations: list[Reservation], current_time: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Check for and identify expired reservations.

        Args:
            reservations: List of reservations to check
            current_time: Current timestamp (for testing)

        Returns:
            List of expired reservations

        Best Practice:
        - Batch operation for efficiency
        - Support scheduled cleanup jobs
        - Return actionable information
        """
        if current_time is None:
            current_time = datetime.now()

        expired = []
        for reservation in reservations:
            if reservation.is_expired(current_time):
                expired.append(
                    {
                        "reservation_id": reservation.reservation_id,
                        "product_id": reservation.product_id,
                        "quantity": reservation.quantity,
                        "order_id": reservation.order_id,
                        "created_at": reservation.created_at.isoformat(),
                        "expires_at": reservation.expires_at.isoformat(),
                        "expired_duration_minutes": int(
                            (current_time - reservation.expires_at).total_seconds() / 60
                        ),
                    }
                )

        return expired

    def calculate_reservation_metrics(self, reservations: list[Reservation]) -> dict[str, Any]:
        """Calculate metrics for reservations.

        Args:
            reservations: List of reservations

        Returns:
            Metrics dictionary

        Best Practice:
        - Support analytics and monitoring
        - Provide business insights
        - Help optimize reservation policies
        """
        total_reservations = len(reservations)

        if total_reservations == 0:
            return {
                "total_reservations": 0,
                "by_status": {},
                "total_quantity_reserved": 0,
            }

        by_status = {}
        total_quantity = 0

        for reservation in reservations:
            status = reservation.status.value
            by_status[status] = by_status.get(status, 0) + 1

            if reservation.is_active():
                total_quantity += reservation.quantity

        return {
            "total_reservations": total_reservations,
            "by_status": by_status,
            "total_quantity_reserved": total_quantity,
            "active_reservations": by_status.get(ReservationStatus.CONFIRMED.value, 0)
            + by_status.get(ReservationStatus.PENDING.value, 0),
        }

    def recommend_stock_replenishment(
        self, inventory_item: InventoryItem, sales_velocity: float
    ) -> dict[str, Any] | None:
        """Recommend stock replenishment based on inventory levels.

        Args:
            inventory_item: Current inventory state
            sales_velocity: Average units sold per day

        Returns:
            Replenishment recommendation or None

        Best Practice:
        - Proactive inventory management
        - Data-driven recommendations
        - Prevent stockouts
        """
        if inventory_item.stock_status == StockStatus.OUT_OF_STOCK:
            return {
                "product_id": inventory_item.product_id,
                "urgency": "critical",
                "recommended_quantity": max(int(sales_velocity * 30), 100),  # 30 days supply
                "reason": "out_of_stock",
                "message": "Product is out of stock. Immediate replenishment required.",
            }

        if inventory_item.stock_status == StockStatus.LOW_STOCK:
            days_until_stockout = (
                inventory_item.available_quantity / sales_velocity
                if sales_velocity > 0
                else float("inf")
            )

            if days_until_stockout < 7:
                return {
                    "product_id": inventory_item.product_id,
                    "urgency": "high",
                    "recommended_quantity": max(int(sales_velocity * 30), 50),
                    "days_until_stockout": round(days_until_stockout, 1),
                    "reason": "low_stock",
                    "message": f"Stock will run out in {days_until_stockout:.1f} days",
                }

        return None
