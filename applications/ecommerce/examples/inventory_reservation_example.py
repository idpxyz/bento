"""Example usage of Inventory Reservation Service.

This example demonstrates:
- How to use the inventory reservation service
- Common workflow patterns
- Cross-aggregate coordination
- Best practices for domain services
"""

from datetime import datetime

from applications.ecommerce.modules.order.domain.services import (
    InventoryItem,
    InventoryReservationService,
    Reservation,
    ReservationRequest,
    ReservationStatus,
)


def example_successful_order():
    """Example: Complete successful order flow."""
    print("\n" + "=" * 70)
    print("Example 1: Successful Order Flow")
    print("=" * 70)

    service = InventoryReservationService()
    current_time = datetime.now()

    # Step 1: Check inventory availability
    print("\n1. Checking inventory availability...")
    inventory = InventoryItem(product_id="LAPTOP-001", available_quantity=50)

    availability = service.check_availability(inventory, requested_quantity=5)
    print(f"   Product: {availability['product_id']}")
    print(f"   Available: {availability['available_quantity']} units")
    print(f"   Status: {availability['stock_status']}")
    print(f"   ✓ {availability['message']}")

    # Step 2: Reserve inventory for order
    if availability["is_available"]:
        print("\n2. Reserving inventory...")
        request = ReservationRequest(
            product_id="LAPTOP-001",
            quantity=5,
            order_id="ORD-2025-001",
            customer_id="CUST-12345",
            reservation_duration_minutes=15,
        )

        reservation_result = service.reserve_inventory(request, inventory, current_time)
        print(f"   Reservation ID: {reservation_result['reservation_id']}")
        print(f"   Quantity Reserved: {reservation_result['quantity']} units")
        print(f"   Expires: {reservation_result['expires_at']}")
        print(f"   New Available: {reservation_result['new_available_quantity']} units")
        print(f"   ✓ {reservation_result['message']}")

        # Step 3: Customer completes payment - fulfill order
        print("\n3. Customer completed payment - fulfilling order...")
        reservation = Reservation(
            reservation_id=reservation_result["reservation_id"],
            product_id="LAPTOP-001",
            quantity=5,
            order_id="ORD-2025-001",
            customer_id="CUST-12345",
            status=ReservationStatus.CONFIRMED,
            created_at=current_time,
            expires_at=datetime.fromisoformat(reservation_result["expires_at"]),
        )

        fulfill_result = service.fulfill_reservation(reservation, current_time)
        print(f"   Order ID: {fulfill_result['reservation_id']}")
        print(f"   Units Deducted: {fulfill_result['quantity_fulfilled']}")
        print(f"   Status: {fulfill_result['status']}")
        print(f"   ✓ {fulfill_result['message']}")


def example_cancelled_order():
    """Example: Order cancelled - release reservation."""
    print("\n" + "=" * 70)
    print("Example 2: Cancelled Order Flow")
    print("=" * 70)

    service = InventoryReservationService()
    current_time = datetime.now()

    # Reserve inventory
    print("\n1. Reserving inventory for order...")
    inventory = InventoryItem(product_id="PHONE-002", available_quantity=100)
    request = ReservationRequest(
        product_id="PHONE-002",
        quantity=10,
        order_id="ORD-2025-002",
        customer_id="CUST-67890",
    )

    reservation_result = service.reserve_inventory(request, inventory, current_time)
    print(f"   Reservation ID: {reservation_result['reservation_id']}")
    print(f"   Quantity Reserved: {reservation_result['quantity']} units")
    print("   ✓ Inventory reserved successfully")

    # Customer cancels order
    print("\n2. Customer cancelled order - releasing inventory...")
    reservation = Reservation(
        reservation_id=reservation_result["reservation_id"],
        product_id="PHONE-002",
        quantity=10,
        order_id="ORD-2025-002",
        customer_id="CUST-67890",
        status=ReservationStatus.CONFIRMED,
        created_at=current_time,
        expires_at=datetime.fromisoformat(reservation_result["expires_at"]),
    )

    release_result = service.release_reservation(
        reservation, reason="customer_cancelled", current_time=current_time
    )
    print(f"   Reservation ID: {release_result['reservation_id']}")
    print(f"   Quantity Released: {release_result['quantity_released']} units")
    print(f"   Reason: {release_result['reason']}")
    print(f"   ✓ {release_result['message']}")


def example_insufficient_stock():
    """Example: Handling insufficient stock."""
    print("\n" + "=" * 70)
    print("Example 3: Insufficient Stock")
    print("=" * 70)

    service = InventoryReservationService()
    current_time = datetime.now()

    print("\n1. Checking inventory availability...")
    inventory = InventoryItem(product_id="TABLET-003", available_quantity=3)

    availability = service.check_availability(inventory, requested_quantity=10)
    print(f"   Product: {availability['product_id']}")
    print(f"   Available: {availability['available_quantity']} units")
    print(f"   Requested: {availability['requested_quantity']} units")
    print(f"   Status: {availability['stock_status']}")
    print(f"   ⚠ {availability['message']}")

    # Attempt to reserve
    print("\n2. Attempting to reserve inventory...")
    request = ReservationRequest(
        product_id="TABLET-003",
        quantity=10,
        order_id="ORD-2025-003",
        customer_id="CUST-11111",
    )

    reservation_result = service.reserve_inventory(request, inventory, current_time)
    if not reservation_result["success"]:
        print(f"   ✗ Reservation failed: {reservation_result['reason']}")
        print(f"   {reservation_result['message']}")
        print("\n   → Suggest customer to:")
        print("      - Reduce quantity to 3 units")
        print("      - Wait for restocking")
        print("      - Check similar products")


def example_expired_reservations():
    """Example: Handling expired reservations."""
    print("\n" + "=" * 70)
    print("Example 4: Expired Reservations Cleanup")
    print("=" * 70)

    service = InventoryReservationService()
    current_time = datetime.now()

    print("\n1. Creating sample reservations...")
    from datetime import timedelta

    reservations = [
        Reservation(
            reservation_id="RES-001",
            product_id="MONITOR-004",
            quantity=5,
            order_id="ORD-001",
            customer_id="CUST-001",
            status=ReservationStatus.PENDING,
            created_at=current_time - timedelta(minutes=30),
            expires_at=current_time - timedelta(minutes=10),  # Expired 10 mins ago
        ),
        Reservation(
            reservation_id="RES-002",
            product_id="KEYBOARD-005",
            quantity=10,
            order_id="ORD-002",
            customer_id="CUST-002",
            status=ReservationStatus.CONFIRMED,
            created_at=current_time - timedelta(minutes=5),
            expires_at=current_time + timedelta(minutes=10),  # Still active
        ),
        Reservation(
            reservation_id="RES-003",
            product_id="MOUSE-006",
            quantity=20,
            order_id="ORD-003",
            customer_id="CUST-003",
            status=ReservationStatus.PENDING,
            created_at=current_time - timedelta(minutes=45),
            expires_at=current_time - timedelta(minutes=30),  # Expired 30 mins ago
        ),
    ]
    print(f"   Created {len(reservations)} test reservations")

    # Check for expired
    print("\n2. Checking for expired reservations...")
    expired = service.check_expired_reservations(reservations, current_time)
    print(f"   Found {len(expired)} expired reservations:")

    for exp in expired:
        print(f"\n   Reservation ID: {exp['reservation_id']}")
        print(f"   Product: {exp['product_id']}")
        print(f"   Quantity: {exp['quantity']} units")
        print(f"   Expired: {exp['expired_duration_minutes']} minutes ago")

    # Release expired reservations
    print("\n3. Releasing expired reservations...")
    for reservation in reservations:
        if reservation.reservation_id in [e["reservation_id"] for e in expired]:
            release_result = service.release_reservation(
                reservation, reason="timeout", current_time=current_time
            )
            if release_result["success"]:
                print(f"   ✓ Released {release_result['quantity_released']} units")


def example_reservation_metrics():
    """Example: Calculate reservation metrics."""
    print("\n" + "=" * 70)
    print("Example 5: Reservation Metrics & Analytics")
    print("=" * 70)

    service = InventoryReservationService()
    current_time = datetime.now()

    from datetime import timedelta

    reservations = [
        Reservation(
            reservation_id="RES-A",
            product_id="PROD-A",
            quantity=10,
            order_id="ORD-A",
            customer_id="CUST-A",
            status=ReservationStatus.CONFIRMED,
            created_at=current_time,
            expires_at=current_time + timedelta(minutes=15),
        ),
        Reservation(
            reservation_id="RES-B",
            product_id="PROD-B",
            quantity=5,
            order_id="ORD-B",
            customer_id="CUST-B",
            status=ReservationStatus.CONFIRMED,
            created_at=current_time,
            expires_at=current_time + timedelta(minutes=15),
        ),
        Reservation(
            reservation_id="RES-C",
            product_id="PROD-C",
            quantity=15,
            order_id="ORD-C",
            customer_id="CUST-C",
            status=ReservationStatus.FULFILLED,
            created_at=current_time - timedelta(hours=1),
            expires_at=current_time - timedelta(minutes=45),
        ),
        Reservation(
            reservation_id="RES-D",
            product_id="PROD-D",
            quantity=8,
            order_id="ORD-D",
            customer_id="CUST-D",
            status=ReservationStatus.RELEASED,
            created_at=current_time - timedelta(hours=2),
            expires_at=current_time - timedelta(hours=1),
            released_at=current_time - timedelta(hours=1),
        ),
    ]

    print("\n1. Calculating reservation metrics...")
    metrics = service.calculate_reservation_metrics(reservations)

    print(f"   Total Reservations: {metrics['total_reservations']}")
    print(f"   Active Reservations: {metrics['active_reservations']}")
    print(f"   Total Quantity Reserved: {metrics['total_quantity_reserved']} units")
    print("\n   By Status:")
    for status, count in metrics["by_status"].items():
        print(f"      {status}: {count}")


def example_stock_replenishment():
    """Example: Stock replenishment recommendations."""
    print("\n" + "=" * 70)
    print("Example 6: Stock Replenishment Recommendations")
    print("=" * 70)

    service = InventoryReservationService()

    # Case 1: Out of stock
    print("\n1. Product out of stock:")
    item1 = InventoryItem(product_id="HEADPHONES-007", available_quantity=0)
    recommendation1 = service.recommend_stock_replenishment(item1, sales_velocity=15.0)
    if recommendation1:
        print(f"   Product: {recommendation1['product_id']}")
        print(f"   Urgency: {recommendation1['urgency'].upper()}")
        print(f"   Recommended Quantity: {recommendation1['recommended_quantity']} units")
        print(f"   ⚠ {recommendation1['message']}")

    # Case 2: Low stock - urgent
    print("\n2. Low stock - urgent replenishment needed:")
    item2 = InventoryItem(product_id="CHARGER-008", available_quantity=15, low_stock_threshold=30)
    recommendation2 = service.recommend_stock_replenishment(item2, sales_velocity=5.0)
    if recommendation2:
        print(f"   Product: {recommendation2['product_id']}")
        print(f"   Urgency: {recommendation2['urgency'].upper()}")
        print(f"   Days Until Stockout: {recommendation2['days_until_stockout']} days")
        print(f"   Recommended Quantity: {recommendation2['recommended_quantity']} units")
        print(f"   ⚠ {recommendation2['message']}")

    # Case 3: Sufficient stock
    print("\n3. Sufficient stock - no action needed:")
    item3 = InventoryItem(product_id="CABLE-009", available_quantity=500)
    recommendation3 = service.recommend_stock_replenishment(item3, sales_velocity=10.0)
    if recommendation3 is None:
        print("   ✓ Inventory levels are healthy")
        print(f"   Current stock: {item3.available_quantity} units")
        print(f"   Status: {item3.stock_status.value}")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 12 + "INVENTORY RESERVATION SERVICE EXAMPLES" + " " * 17 + "║")
    print("╚" + "=" * 68 + "╝")

    example_successful_order()
    example_cancelled_order()
    example_insufficient_stock()
    example_expired_reservations()
    example_reservation_metrics()
    example_stock_replenishment()

    print("\n" + "=" * 70)
    print("All examples completed successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
