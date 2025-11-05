"""Tests for Inventory Reservation Service.

This test suite demonstrates:
- Domain service testing patterns
- Cross-aggregate coordination testing
- Time-based business logic testing
- State transition validation
"""

from datetime import datetime, timedelta

from applications.ecommerce.modules.order.domain.services import (
    InventoryItem,
    InventoryReservationService,
    Reservation,
    ReservationRequest,
    ReservationStatus,
    StockStatus,
)


class TestInventoryItem:
    """Test InventoryItem value object."""

    def test_inventory_item_creation(self):
        """Test creating an inventory item."""
        item = InventoryItem(product_id="PROD-123", available_quantity=100, reserved_quantity=20)

        assert item.product_id == "PROD-123"
        assert item.available_quantity == 100
        assert item.reserved_quantity == 20
        assert item.total_quantity == 120

    def test_inventory_item_stock_status_in_stock(self):
        """Test in-stock status."""
        item = InventoryItem(product_id="PROD-123", available_quantity=50)

        assert item.stock_status == StockStatus.IN_STOCK

    def test_inventory_item_stock_status_low_stock(self):
        """Test low-stock status."""
        item = InventoryItem(product_id="PROD-123", available_quantity=5, low_stock_threshold=10)

        assert item.stock_status == StockStatus.LOW_STOCK

    def test_inventory_item_stock_status_out_of_stock(self):
        """Test out-of-stock status."""
        item = InventoryItem(product_id="PROD-123", available_quantity=0)

        assert item.stock_status == StockStatus.OUT_OF_STOCK


class TestReservation:
    """Test Reservation value object."""

    def test_reservation_is_expired(self):
        """Test reservation expiry check."""
        now = datetime(2025, 1, 1, 12, 0, 0)
        reservation = Reservation(
            reservation_id="RES-123",
            product_id="PROD-123",
            quantity=5,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )

        # Not expired yet
        assert not reservation.is_expired(now + timedelta(minutes=10))

        # Expired
        assert reservation.is_expired(now + timedelta(minutes=20))

    def test_reservation_is_active(self):
        """Test reservation active status."""
        now = datetime(2025, 1, 1, 12, 0, 0)

        # Active states
        pending = Reservation(
            reservation_id="RES-1",
            product_id="PROD-123",
            quantity=5,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.PENDING,
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        assert pending.is_active()

        confirmed = Reservation(
            reservation_id="RES-2",
            product_id="PROD-123",
            quantity=5,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.CONFIRMED,
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        assert confirmed.is_active()

        # Inactive states
        released = Reservation(
            reservation_id="RES-3",
            product_id="PROD-123",
            quantity=5,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.RELEASED,
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        assert not released.is_active()


class TestInventoryReservationService:
    """Test InventoryReservationService domain service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = InventoryReservationService()
        self.current_time = datetime(2025, 1, 1, 12, 0, 0)

    def test_check_availability_sufficient_stock(self):
        """Test availability check with sufficient stock."""
        item = InventoryItem(product_id="PROD-123", available_quantity=100)

        result = self.service.check_availability(item, requested_quantity=50)

        assert result["is_available"] is True
        assert result["available_quantity"] == 100
        assert result["requested_quantity"] == 50
        assert result["stock_status"] == StockStatus.IN_STOCK.value
        assert "available" in result["message"].lower()

    def test_check_availability_insufficient_stock(self):
        """Test availability check with insufficient stock."""
        item = InventoryItem(product_id="PROD-123", available_quantity=10)

        result = self.service.check_availability(item, requested_quantity=20)

        assert result["is_available"] is False
        assert result["available_quantity"] == 10
        assert result["requested_quantity"] == 20
        assert "only 10 units available" in result["message"].lower()

    def test_check_availability_out_of_stock(self):
        """Test availability check when out of stock."""
        item = InventoryItem(product_id="PROD-123", available_quantity=0)

        result = self.service.check_availability(item, requested_quantity=5)

        assert result["is_available"] is False
        assert result["stock_status"] == StockStatus.OUT_OF_STOCK.value
        assert "out of stock" in result["message"].lower()

    def test_check_availability_low_stock_warning(self):
        """Test availability check shows low stock warning."""
        item = InventoryItem(product_id="PROD-123", available_quantity=5, low_stock_threshold=10)

        result = self.service.check_availability(item, requested_quantity=3)

        assert result["is_available"] is True
        assert result["stock_status"] == StockStatus.LOW_STOCK.value
        assert "only 5 units left" in result["message"].lower()

    def test_reserve_inventory_success(self):
        """Test successful inventory reservation."""
        item = InventoryItem(product_id="PROD-123", available_quantity=100)
        request = ReservationRequest(
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
            reservation_duration_minutes=15,
        )

        result = self.service.reserve_inventory(request, item, self.current_time)

        assert result["success"] is True
        assert result["product_id"] == "PROD-123"
        assert result["quantity"] == 10
        assert result["order_id"] == "ORD-456"
        assert result["status"] == ReservationStatus.CONFIRMED.value
        assert result["new_available_quantity"] == 90
        assert result["new_reserved_quantity"] == 10
        assert "reservation_id" in result

    def test_reserve_inventory_insufficient_stock(self):
        """Test reservation fails with insufficient stock."""
        item = InventoryItem(product_id="PROD-123", available_quantity=5)
        request = ReservationRequest(
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
        )

        result = self.service.reserve_inventory(request, item, self.current_time)

        assert result["success"] is False
        assert result["reason"] == "insufficient_stock"
        assert result["available_quantity"] == 5
        assert result["requested_quantity"] == 10

    def test_reserve_inventory_exact_quantity(self):
        """Test reservation with exact available quantity."""
        item = InventoryItem(product_id="PROD-123", available_quantity=10)
        request = ReservationRequest(
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
        )

        result = self.service.reserve_inventory(request, item, self.current_time)

        assert result["success"] is True
        assert result["new_available_quantity"] == 0
        assert result["new_reserved_quantity"] == 10

    def test_reserve_inventory_expiration_time(self):
        """Test reservation sets correct expiration time."""
        item = InventoryItem(product_id="PROD-123", available_quantity=100)
        request = ReservationRequest(
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
            reservation_duration_minutes=30,
        )

        result = self.service.reserve_inventory(request, item, self.current_time)

        expected_expiry = self.current_time + timedelta(minutes=30)
        assert result["expires_at"] == expected_expiry.isoformat()

    def test_release_reservation_success(self):
        """Test successful reservation release."""
        reservation = Reservation(
            reservation_id="RES-123",
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.CONFIRMED,
            created_at=self.current_time,
            expires_at=self.current_time + timedelta(minutes=15),
        )

        result = self.service.release_reservation(
            reservation, reason="cancelled", current_time=self.current_time
        )

        assert result["success"] is True
        assert result["reservation_id"] == "RES-123"
        assert result["quantity_released"] == 10
        assert result["status"] == ReservationStatus.RELEASED.value
        assert result["reason"] == "cancelled"

    def test_release_reservation_already_released(self):
        """Test releasing already released reservation."""
        reservation = Reservation(
            reservation_id="RES-123",
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.RELEASED,
            created_at=self.current_time,
            expires_at=self.current_time + timedelta(minutes=15),
            released_at=self.current_time,
        )

        result = self.service.release_reservation(reservation, current_time=self.current_time)

        assert result["success"] is False
        assert result["reason"] == "already_released"

    def test_release_reservation_fulfilled(self):
        """Test releasing fulfilled reservation."""
        reservation = Reservation(
            reservation_id="RES-123",
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.FULFILLED,
            created_at=self.current_time,
            expires_at=self.current_time + timedelta(minutes=15),
        )

        result = self.service.release_reservation(reservation, current_time=self.current_time)

        assert result["success"] is False
        assert result["reason"] == "already_released"

    def test_fulfill_reservation_success(self):
        """Test successful reservation fulfillment."""
        reservation = Reservation(
            reservation_id="RES-123",
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.CONFIRMED,
            created_at=self.current_time,
            expires_at=self.current_time + timedelta(minutes=15),
        )

        result = self.service.fulfill_reservation(reservation, current_time=self.current_time)

        assert result["success"] is True
        assert result["reservation_id"] == "RES-123"
        assert result["quantity_fulfilled"] == 10
        assert result["status"] == ReservationStatus.FULFILLED.value

    def test_fulfill_reservation_invalid_state(self):
        """Test fulfilling reservation in invalid state."""
        reservation = Reservation(
            reservation_id="RES-123",
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.RELEASED,
            created_at=self.current_time,
            expires_at=self.current_time + timedelta(minutes=15),
            released_at=self.current_time,
        )

        result = self.service.fulfill_reservation(reservation, current_time=self.current_time)

        assert result["success"] is False
        assert result["reason"] == "invalid_state"

    def test_check_expired_reservations(self):
        """Test checking for expired reservations."""
        reservations = [
            # Expired
            Reservation(
                reservation_id="RES-1",
                product_id="PROD-123",
                quantity=10,
                order_id="ORD-1",
                customer_id="CUST-1",
                status=ReservationStatus.PENDING,
                created_at=self.current_time - timedelta(minutes=30),
                expires_at=self.current_time - timedelta(minutes=5),
            ),
            # Not expired
            Reservation(
                reservation_id="RES-2",
                product_id="PROD-123",
                quantity=5,
                order_id="ORD-2",
                customer_id="CUST-2",
                status=ReservationStatus.PENDING,
                created_at=self.current_time,
                expires_at=self.current_time + timedelta(minutes=15),
            ),
            # Already released (shouldn't be in expired list)
            Reservation(
                reservation_id="RES-3",
                product_id="PROD-123",
                quantity=3,
                order_id="ORD-3",
                customer_id="CUST-3",
                status=ReservationStatus.RELEASED,
                created_at=self.current_time - timedelta(minutes=30),
                expires_at=self.current_time - timedelta(minutes=5),
            ),
        ]

        expired = self.service.check_expired_reservations(
            reservations, current_time=self.current_time
        )

        assert len(expired) == 1
        assert expired[0]["reservation_id"] == "RES-1"
        assert expired[0]["quantity"] == 10
        assert expired[0]["expired_duration_minutes"] == 5

    def test_check_expired_reservations_empty_list(self):
        """Test checking expired reservations with empty list."""
        expired = self.service.check_expired_reservations([], current_time=self.current_time)

        assert expired == []

    def test_calculate_reservation_metrics(self):
        """Test calculating reservation metrics."""
        reservations = [
            Reservation(
                reservation_id="RES-1",
                product_id="PROD-123",
                quantity=10,
                order_id="ORD-1",
                customer_id="CUST-1",
                status=ReservationStatus.CONFIRMED,
                created_at=self.current_time,
                expires_at=self.current_time + timedelta(minutes=15),
            ),
            Reservation(
                reservation_id="RES-2",
                product_id="PROD-123",
                quantity=5,
                order_id="ORD-2",
                customer_id="CUST-2",
                status=ReservationStatus.CONFIRMED,
                created_at=self.current_time,
                expires_at=self.current_time + timedelta(minutes=15),
            ),
            Reservation(
                reservation_id="RES-3",
                product_id="PROD-123",
                quantity=3,
                order_id="ORD-3",
                customer_id="CUST-3",
                status=ReservationStatus.RELEASED,
                created_at=self.current_time,
                expires_at=self.current_time + timedelta(minutes=15),
            ),
        ]

        metrics = self.service.calculate_reservation_metrics(reservations)

        assert metrics["total_reservations"] == 3
        assert metrics["by_status"]["confirmed"] == 2
        assert metrics["by_status"]["released"] == 1
        assert metrics["total_quantity_reserved"] == 15  # Only active reservations
        assert metrics["active_reservations"] == 2

    def test_calculate_reservation_metrics_empty(self):
        """Test metrics with no reservations."""
        metrics = self.service.calculate_reservation_metrics([])

        assert metrics["total_reservations"] == 0
        assert metrics["by_status"] == {}
        assert metrics["total_quantity_reserved"] == 0

    def test_recommend_stock_replenishment_out_of_stock(self):
        """Test replenishment recommendation for out of stock."""
        item = InventoryItem(product_id="PROD-123", available_quantity=0)
        sales_velocity = 10.0  # 10 units per day

        recommendation = self.service.recommend_stock_replenishment(item, sales_velocity)

        assert recommendation is not None
        assert recommendation["urgency"] == "critical"
        assert recommendation["product_id"] == "PROD-123"
        assert recommendation["recommended_quantity"] >= 100
        assert recommendation["reason"] == "out_of_stock"

    def test_recommend_stock_replenishment_low_stock_urgent(self):
        """Test replenishment recommendation for low stock (urgent)."""
        item = InventoryItem(product_id="PROD-123", available_quantity=20, low_stock_threshold=30)
        sales_velocity = 5.0  # 5 units per day (will run out in 4 days)

        recommendation = self.service.recommend_stock_replenishment(item, sales_velocity)

        assert recommendation is not None
        assert recommendation["urgency"] == "high"
        assert recommendation["days_until_stockout"] == 4.0
        assert recommendation["reason"] == "low_stock"

    def test_recommend_stock_replenishment_not_needed(self):
        """Test no replenishment needed for sufficient stock."""
        item = InventoryItem(product_id="PROD-123", available_quantity=200)
        sales_velocity = 5.0  # 5 units per day (40 days supply)

        recommendation = self.service.recommend_stock_replenishment(item, sales_velocity)

        assert recommendation is None

    def test_recommend_stock_replenishment_low_stock_not_urgent(self):
        """Test no urgent recommendation when low stock but sufficient time."""
        item = InventoryItem(product_id="PROD-123", available_quantity=50, low_stock_threshold=60)
        sales_velocity = 5.0  # 5 units per day (10 days supply)

        recommendation = self.service.recommend_stock_replenishment(item, sales_velocity)

        assert recommendation is None


class TestReservationLifecycle:
    """Test complete reservation lifecycle scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = InventoryReservationService()
        self.current_time = datetime(2025, 1, 1, 12, 0, 0)

    def test_complete_successful_order_flow(self):
        """Test complete flow: reserve -> fulfill."""
        # Step 1: Check availability
        item = InventoryItem(product_id="PROD-123", available_quantity=100)
        availability = self.service.check_availability(item, requested_quantity=10)
        assert availability["is_available"] is True

        # Step 2: Reserve inventory
        request = ReservationRequest(
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
        )
        reserve_result = self.service.reserve_inventory(request, item, self.current_time)
        assert reserve_result["success"] is True

        # Step 3: Fulfill order
        reservation = Reservation(
            reservation_id=reserve_result["reservation_id"],
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.CONFIRMED,
            created_at=self.current_time,
            expires_at=self.current_time + timedelta(minutes=15),
        )
        fulfill_result = self.service.fulfill_reservation(
            reservation, current_time=self.current_time
        )
        assert fulfill_result["success"] is True
        assert fulfill_result["status"] == ReservationStatus.FULFILLED.value

    def test_cancelled_order_flow(self):
        """Test flow: reserve -> cancel/release."""
        # Reserve
        item = InventoryItem(product_id="PROD-123", available_quantity=100)
        request = ReservationRequest(
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
        )
        reserve_result = self.service.reserve_inventory(request, item, self.current_time)
        assert reserve_result["success"] is True

        # Cancel/Release
        reservation = Reservation(
            reservation_id=reserve_result["reservation_id"],
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.CONFIRMED,
            created_at=self.current_time,
            expires_at=self.current_time + timedelta(minutes=15),
        )
        release_result = self.service.release_reservation(
            reservation, reason="customer_cancelled", current_time=self.current_time
        )
        assert release_result["success"] is True
        assert release_result["reason"] == "customer_cancelled"

    def test_expired_reservation_cleanup(self):
        """Test identifying and handling expired reservations."""
        # Create expired reservation
        expired_reservation = Reservation(
            reservation_id="RES-123",
            product_id="PROD-123",
            quantity=10,
            order_id="ORD-456",
            customer_id="CUST-789",
            status=ReservationStatus.PENDING,
            created_at=self.current_time - timedelta(minutes=30),
            expires_at=self.current_time - timedelta(minutes=5),
        )

        # Check for expired
        expired_list = self.service.check_expired_reservations(
            [expired_reservation], current_time=self.current_time
        )
        assert len(expired_list) == 1

        # Release expired reservation
        release_result = self.service.release_reservation(
            expired_reservation, reason="timeout", current_time=self.current_time
        )
        assert release_result["success"] is True
