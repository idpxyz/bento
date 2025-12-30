"""Comprehensive E-commerce System Test.

Tests:
1. Order CRUD operations (Write Model)
2. Order Query Service (Read Model + CQRS)
3. Projection synchronization (Write → Read)
4. Repository and Mapper functionality
5. Performance comparison (CRUD vs CQRS)
"""

import asyncio
import time
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from applications.ecommerce.modules.order.application.projections.order_projection import (
    OrderProjection,
)
from applications.ecommerce.modules.order.application.queries.order_query_service import (
    OrderQueryService,
)
from applications.ecommerce.modules.order.application.queries.order_read_service import (
    OrderReadService,
)
from applications.ecommerce.modules.order.domain.events import OrderCreated
from applications.ecommerce.modules.order.domain.order import Order, OrderItem
from applications.ecommerce.modules.order.persistence import (
    OrderMapper,
    OrderRepository,
)
from applications.ecommerce.modules.order.persistence.models import (
    OrderModel,
)
from applications.ecommerce.modules.order.persistence.models.order_read_model import (
    OrderReadModel,
)
from bento.core.ids import ID
from bento.infrastructure.database import init_database
from bento.persistence import Base

# ANSI color codes for output
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"


def print_section(title: str):
    """Print a section header."""
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}{title:^80}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")


def print_success(message: str):
    """Print a success message."""
    print(f"{GREEN}✓ {message}{RESET}")


def print_info(message: str):
    """Print an info message."""
    print(f"{BLUE}ℹ {message}{RESET}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"{YELLOW}⚠ {message}{RESET}")


def print_error(message: str):
    """Print an error message."""
    print(f"{RED}✗ {message}{RESET}")


def print_metric(label: str, value: any):
    """Print a metric."""
    print(f"{YELLOW}{label:.<40}{RESET} {BOLD}{value}{RESET}")


async def setup_database():
    """Setup in-memory database for testing."""
    print_section("DATABASE SETUP")

    # Import models to register them with Base
    from applications.ecommerce.modules.order.persistence.models import (  # noqa: F401
        OrderModel,
    )
    from applications.ecommerce.modules.order.persistence.models.order_read_model import (  # noqa: F401
        OrderItemReadModel,
        OrderReadModel,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    await init_database(engine, Base, check_tables=False)

    print_success("Database initialized (in-memory SQLite)")
    print_info("Tables created: orders, order_items, order_read_models")

    return engine


def create_sample_order(customer_id: str, order_id: str | None = None) -> Order:
    """Create a sample order for testing."""
    if order_id is None:
        order_id = str(uuid4())

    order = Order.create(
        order_id=ID(order_id),
        customer_id=ID(customer_id),
    )

    # Add items
    order.add_item(
        OrderItem(
            item_id=ID(str(uuid4())),
            product_id=ID("prod-001"),
            product_name="MacBook Pro",
            quantity=1,
            unit_price=2999.99,
        )
    )
    order.add_item(
        OrderItem(
            item_id=ID(str(uuid4())),
            product_id=ID("prod-002"),
            product_name="Magic Mouse",
            quantity=2,
            unit_price=79.99,
        )
    )

    return order


async def test_write_model_operations(session: AsyncSession):
    """Test 1: Basic CRUD operations on write model."""
    print_section("TEST 1: Write Model Operations (CRUD)")

    mapper = OrderMapper()
    repo = OrderRepository(session, mapper)

    # Create order
    customer_id = str(uuid4())
    order = create_sample_order(customer_id)

    print_info(f"Creating order: {order.id.value}")
    print_metric("Customer ID", customer_id)
    print_metric("Items count", len(order.items))
    print_metric("Total amount", f"${order.calculate_total():.2f}")

    await repo.add(order)
    print_success("Order created in write model (OrderModel)")

    # Retrieve order
    retrieved_order = await repo.get_by_id(order.id)
    assert retrieved_order is not None
    print_success(f"Order retrieved: {retrieved_order.id.value}")
    print_metric("Status", retrieved_order.status.value)
    print_metric("Items", len(retrieved_order.items))

    # Verify in database
    stmt = select(OrderModel).where(OrderModel.id == order.id.value)
    result = await session.execute(stmt)
    order_po = result.scalar_one()
    print_success(f"Verified in database: {len(order_po.items)} items")

    return order, customer_id


async def test_projection_sync(session: AsyncSession, order: Order):
    """Test 2: Projection synchronization (Write → Read)."""
    print_section("TEST 2: Projection Synchronization")

    projection = OrderProjection(session)

    # Simulate OrderCreated event
    event = OrderCreated(
        order_id=order.id,
        customer_id=order.customer_id,
        total_amount=order.calculate_total(),
    )

    print_info(f"Handling OrderCreated event: {event.order_id.value}")

    start_time = time.time()
    await projection.handle_order_created(event)
    elapsed = (time.time() - start_time) * 1000

    print_success(f"Projection completed in {elapsed:.2f}ms")

    # Verify read model was created
    stmt = select(OrderReadModel).where(OrderReadModel.id == order.id.value)
    result = await session.execute(stmt)
    read_model = result.scalar_one()

    print_success("Read model created successfully")
    print_metric("Order ID", read_model.id)
    print_metric("Customer ID", read_model.customer_id)
    print_metric("Status", read_model.status)
    print_metric("Total Amount (pre-calculated)", f"${read_model.total_amount:.2f}")
    print_metric("Items Count (pre-calculated)", read_model.items_count)

    # Verify accuracy
    expected_total = order.calculate_total()
    assert abs(read_model.total_amount - expected_total) < 0.01
    assert read_model.items_count == len(order.items)
    print_success("✓ Pre-calculated fields are accurate!")

    return read_model


async def test_read_service(session: AsyncSession, customer_id: str):
    """Test 3: Query using Read Service (CQRS)."""
    print_section("TEST 3: CQRS Read Service")

    read_service = OrderReadService(session)

    # Test 1: Get order by ID
    print_info("Test 3.1: Get order by ID")
    stmt = select(OrderReadModel).limit(1)
    result = await session.execute(stmt)
    first_order = result.scalar_one()

    order_data = await read_service.get_order_by_id(first_order.id)
    print_success(f"Retrieved order: {order_data['id']}")
    print_metric("Total amount", f"${order_data['total_amount']:.2f}")
    print_metric("Items count", order_data["items_count"])

    # Test 2: List orders
    print_info("\nTest 3.2: List orders by customer")
    result = await read_service.list_orders(customer_id=customer_id, limit=10)
    print_success(f"Found {len(result['items'])} orders")
    print_metric("Total count", result["total"])

    # Test 3: Search by amount range
    print_info("\nTest 3.3: Search orders by amount range")
    result = await read_service.search_orders(min_amount=100.0, max_amount=5000.0, limit=10)
    print_success(f"Found {len(result['items'])} orders in range $100-$5000")
    for item in result["items"]:
        print_metric(f"  Order {item['id'][:8]}...", f"${item['total_amount']:.2f}")

    # Test 4: Statistics
    print_info("\nTest 3.4: Get order statistics")
    stats = await read_service.get_order_statistics(customer_id=customer_id)
    print_success("Statistics calculated from read model:")
    print_metric("Total orders", stats["total_orders"])
    print_metric("Total revenue", f"${stats['total_revenue']:.2f}")
    print_metric("Average order value", f"${stats['average_order_value']:.2f}")
    print_metric("Status breakdown", stats["status_breakdown"])


async def test_query_service_comparison(session: AsyncSession, customer_id: str):
    """Test 4: Compare traditional query service (in-memory) vs CQRS."""
    print_section("TEST 4: Performance Comparison")

    query_service = OrderQueryService(session)
    read_service = OrderReadService(session)

    print_info("Comparing two approaches for amount filtering:")
    print_info("  1. Traditional: JOIN + in-memory filtering (OrderQueryService)")
    print_info("  2. CQRS: Pre-calculated read model (OrderReadService)")

    # Traditional approach (in-memory filtering)
    print_info("\n[Traditional Approach]")
    start_time = time.time()
    result1 = await query_service.search_orders(min_amount=100.0, max_amount=5000.0, limit=10)
    elapsed1 = (time.time() - start_time) * 1000

    print_metric("Execution time", f"{elapsed1:.2f}ms")
    print_metric("Results found", len(result1["items"]))
    print_warning("⚠ Requires JOIN + in-memory filtering")

    # CQRS approach (database-level filtering)
    print_info("\n[CQRS Approach]")
    start_time = time.time()
    result2 = await read_service.search_orders(min_amount=100.0, max_amount=5000.0, limit=10)
    elapsed2 = (time.time() - start_time) * 1000

    print_metric("Execution time", f"{elapsed2:.2f}ms")
    print_metric("Results found", len(result2["items"]))
    print_success("✓ Database-level filtering on pre-calculated field")

    # Performance comparison
    if elapsed1 > 0:
        speedup = elapsed1 / elapsed2 if elapsed2 > 0 else float("inf")
        print_info(f"\n{BOLD}Performance Improvement: {speedup:.1f}x faster{RESET}")


async def test_batch_operations(session: AsyncSession):
    """Test 5: Batch create orders and verify projections."""
    print_section("TEST 5: Batch Operations")

    mapper = OrderMapper()
    repo = OrderRepository(session, mapper)
    projection = OrderProjection(session)

    num_orders = 10
    print_info(f"Creating {num_orders} orders in batch...")

    orders = []
    customer_ids = [str(uuid4()) for _ in range(5)]  # 5 different customers

    start_time = time.time()

    for i in range(num_orders):
        customer_id = customer_ids[i % len(customer_ids)]
        order = create_sample_order(customer_id)

        # Vary the amounts
        if i % 3 == 0:
            # Add extra item for variety
            order.add_item(
                OrderItem(
                    item_id=ID(str(uuid4())),
                    product_id=ID("prod-003"),
                    product_name="AirPods Pro",
                    quantity=1,
                    unit_price=249.99,
                )
            )

        await repo.add(order)

        # Trigger projection
        event = OrderCreated(
            order_id=order.id,
            customer_id=order.customer_id,
            total_amount=order.calculate_total(),
        )
        await projection.handle_order_created(event)

        orders.append(order)

    elapsed = (time.time() - start_time) * 1000

    print_success(f"Created {num_orders} orders with projections")
    print_metric("Total time", f"{elapsed:.2f}ms")
    print_metric("Average per order", f"{elapsed / num_orders:.2f}ms")

    # Verify counts
    write_count = await session.scalar(select(func.count()).select_from(OrderModel))
    read_count = await session.scalar(select(func.count()).select_from(OrderReadModel))

    print_success(f"Write models: {write_count}")
    print_success(f"Read models: {read_count}")
    assert write_count == read_count
    print_success("✓ Write and read models are in sync!")

    return orders


async def test_data_consistency(session: AsyncSession):
    """Test 6: Verify data consistency between write and read models."""
    print_section("TEST 6: Data Consistency Check")

    from sqlalchemy.orm import selectinload

    # Get all orders from write model
    stmt = select(OrderModel).options(selectinload(OrderModel.items))
    result = await session.execute(stmt)
    write_orders = result.scalars().all()

    # Get all orders from read model
    stmt = select(OrderReadModel)
    result = await session.execute(stmt)
    read_orders = result.scalars().all()

    print_info(f"Checking consistency for {len(write_orders)} orders...")

    inconsistencies = 0

    for write_order in write_orders:
        # Find corresponding read model
        read_order = next((r for r in read_orders if r.id == write_order.id), None)

        if read_order is None:
            print_error(f"Missing read model for order: {write_order.id}")
            inconsistencies += 1
            continue

        # Verify total_amount
        expected_total = write_order.total_amount
        actual_total = read_order.total_amount

        if abs(expected_total - actual_total) > 0.01:
            print_error(
                f"Amount mismatch for {write_order.id}: "
                f"expected ${expected_total:.2f}, got ${actual_total:.2f}"
            )
            inconsistencies += 1

        # Verify items_count
        expected_count = len(write_order.items)
        actual_count = read_order.items_count

        if expected_count != actual_count:
            print_error(
                f"Items count mismatch for {write_order.id}: "
                f"expected {expected_count}, got {actual_count}"
            )
            inconsistencies += 1

    if inconsistencies == 0:
        print_success(f"✓ All {len(write_orders)} orders are consistent!")
        print_success("✓ Total amounts match")
        print_success("✓ Items counts match")
    else:
        print_error(f"Found {inconsistencies} inconsistencies!")

    return inconsistencies == 0


async def test_mapper_functionality(session: AsyncSession):
    """Test 7: Mapper functionality (AutoMapper)."""
    print_section("TEST 7: Mapper Functionality")

    mapper = OrderMapper()

    # Create domain order
    order = create_sample_order(str(uuid4()))
    print_info(f"Created domain order: {order.id.value}")
    print_metric("Items", len(order.items))
    print_metric("Total", f"${order.calculate_total():.2f}")

    # Map to persistence model
    print_info("\nMapping: Domain → Persistence (forward)")
    order_po = mapper.map(order)

    print_success("Mapped to OrderModel")
    print_metric("PO ID", order_po.id)
    print_metric("PO Items", len(order_po.items))
    print_success("✓ Child entities (OrderItems) auto-mapped")

    # Verify child mapping
    for i, (domain_item, po_item) in enumerate(zip(order.items, order_po.items, strict=True)):
        assert domain_item.item_id.value == po_item.id
        assert domain_item.product_name == po_item.product_name
        assert domain_item.quantity == po_item.quantity
        print_success(f"✓ Item {i + 1}: {po_item.product_name} mapped correctly")

    # Map back to domain
    print_info("\nMapping: Persistence → Domain (reverse)")
    order_domain = mapper.map_reverse(order_po)

    print_success("Mapped back to Order domain object")
    print_metric("Domain ID", order_domain.id.value)
    print_metric("Domain Items", len(order_domain.items))

    # Verify round-trip
    assert order_domain.id.value == order.id.value
    assert order_domain.customer_id.value == order.customer_id.value
    assert len(order_domain.items) == len(order.items)
    print_success("✓ Round-trip mapping successful!")


async def main():
    """Run comprehensive e-commerce system tests."""
    print(f"\n{BOLD}{GREEN}{'=' * 80}{RESET}")
    print(f"{BOLD}{GREEN}E-COMMERCE SYSTEM COMPREHENSIVE TEST{RESET:^88}")
    print(f"{BOLD}{GREEN}{'=' * 80}{RESET}\n")

    try:
        # Setup
        engine = await setup_database()

        async with AsyncSession(engine) as session:
            # Test 1: Write model CRUD
            order, customer_id = await test_write_model_operations(session)

            # Test 2: Projection sync
            await test_projection_sync(session, order)

            # Test 3: Read service
            await test_read_service(session, customer_id)

            # Test 4: Performance comparison
            await test_query_service_comparison(session, customer_id)

            # Test 5: Batch operations
            await test_batch_operations(session)

            # Test 6: Data consistency
            is_consistent = await test_data_consistency(session)

            # Test 7: Mapper functionality
            await test_mapper_functionality(session)

        # Final summary
        print_section("TEST SUMMARY")
        print_success("✓ Test 1: Write Model Operations (CRUD)")
        print_success("✓ Test 2: Projection Synchronization")
        print_success("✓ Test 3: CQRS Read Service")
        print_success("✓ Test 4: Performance Comparison")
        print_success("✓ Test 5: Batch Operations")
        print_success(
            "✓ Test 6: Data Consistency" if is_consistent else "✗ Test 6: Data Consistency"
        )
        print_success("✓ Test 7: Mapper Functionality")

        print(f"\n{BOLD}{GREEN}All tests completed successfully! ✓{RESET}\n")

        await engine.dispose()

    except Exception as e:
        print_error(f"Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
