"""Basic exception usage example.

This example demonstrates how to use the Bento exception system
in different layers of the application.
"""

import logging
from typing import Any

from core.error_codes import CommonErrors
from examples.error_codes.order_errors import OrderErrors
from examples.error_codes.product_errors import ProductErrors
from core.errors import (
    ApplicationException,
    DomainException,
    InfrastructureException,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


# ==================== Domain Layer Example ====================


class Order:
    """Order aggregate example."""

    def __init__(self, order_id: str, status: str = "pending") -> None:
        self.id = order_id
        self.status = status
        self.items: list[dict[str, Any]] = []

    def add_item(self, product_id: str, quantity: int, price: float) -> None:
        """Add item to order.

        Raises:
            DomainException: If order is already paid
        """
        if self.status == "paid":
            # Domain exception: business rule violation
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_PAID,
                details={"order_id": self.id, "current_status": self.status},
            )

        if quantity <= 0:
            raise DomainException(
                error_code=ProductErrors.INVALID_QUANTITY,
                details={"quantity": quantity},
            )

        self.items.append(
            {"product_id": product_id, "quantity": quantity, "price": price}
        )
        logger.info(f"Added item to order {self.id}: {product_id} x{quantity}")

    def pay(self) -> None:
        """Pay for the order.

        Raises:
            DomainException: If order is empty or already paid
        """
        if not self.items:
            raise DomainException(
                error_code=OrderErrors.EMPTY_ORDER_ITEMS,
                details={"order_id": self.id},
            )

        if self.status == "paid":
            raise DomainException(
                error_code=OrderErrors.ORDER_ALREADY_PAID,
                details={"order_id": self.id},
            )

        self.status = "paid"
        logger.info(f"Order {self.id} paid successfully")


# ==================== Application Layer Example ====================


class OrderService:
    """Order application service example."""

    def __init__(self) -> None:
        self.orders: dict[str, Order] = {}

    def create_order(self, order_id: str) -> Order:
        """Create a new order.

        Raises:
            ApplicationException: If validation fails
        """
        # Validate input
        if not order_id or order_id.strip() == "":
            raise ApplicationException(
                error_code=CommonErrors.INVALID_PARAMS,
                details={"field": "order_id", "reason": "cannot be empty"},
            )

        # Check if order already exists
        if order_id in self.orders:
            raise ApplicationException(
                error_code=CommonErrors.RESOURCE_CONFLICT,
                details={"order_id": order_id, "reason": "order already exists"},
            )

        # Create order
        order = Order(order_id)
        self.orders[order_id] = order
        logger.info(f"Order created: {order_id}")
        return order

    def get_order(self, order_id: str) -> Order:
        """Get order by ID.

        Raises:
            ApplicationException: If order not found
        """
        if order_id not in self.orders:
            raise ApplicationException(
                error_code=OrderErrors.ORDER_NOT_FOUND,
                details={"order_id": order_id},
            )

        return self.orders[order_id]


# ==================== Infrastructure Layer Example ====================


class OrderRepository:
    """Order repository example (simulated)."""

    def __init__(self) -> None:
        self._storage: dict[str, dict] = {}

    async def save(self, order: Order) -> None:
        """Save order to database.

        Raises:
            InfrastructureException: If database operation fails
        """
        try:
            # Simulate database operation
            self._storage[order.id] = {
                "id": order.id,
                "status": order.status,
                "items": order.items,
            }
            logger.info(f"Order {order.id} saved to database")

        except Exception as e:
            # Wrap infrastructure error
            raise InfrastructureException(
                error_code=CommonErrors.DATABASE_ERROR,
                details={"operation": "save_order", "order_id": order.id},
                cause=e,  # Preserve original exception
            )

    async def find_by_id(self, order_id: str) -> dict:
        """Find order by ID.

        Raises:
            InfrastructureException: If database operation fails
        """
        try:
            if order_id not in self._storage:
                raise InfrastructureException(
                    error_code=OrderErrors.ORDER_NOT_FOUND,
                    details={"order_id": order_id},
                )

            return self._storage[order_id]

        except InfrastructureException:
            raise
        except Exception as e:
            raise InfrastructureException(
                error_code=CommonErrors.DATABASE_ERROR,
                details={"operation": "find_order", "order_id": order_id},
                cause=e,
            )


# ==================== Demo Functions ====================


def demo_domain_exception() -> None:
    """Demonstrate domain exception."""
    logger.info("\n" + "=" * 60)
    logger.info("Demo 1: Domain Exception")
    logger.info("=" * 60)

    order = Order("ORDER-001")
    order.add_item("PROD-001", 2, 99.99)

    # Pay the order
    order.pay()
    logger.info(f"✅ Order status: {order.status}")

    # Try to add item to paid order (should fail)
    try:
        order.add_item("PROD-002", 1, 49.99)
    except DomainException as e:
        logger.error(f"❌ Domain exception caught:")
        logger.error(f"   Code: {e.error_code.code}")
        logger.error(f"   Message: {e.error_code.message}")
        logger.error(f"   Category: {e.category.value}")
        logger.error(f"   Details: {e.details}")


def demo_application_exception() -> None:
    """Demonstrate application exception."""
    logger.info("\n" + "=" * 60)
    logger.info("Demo 2: Application Exception")
    logger.info("=" * 60)

    service = OrderService()

    # Create order successfully
    order = service.create_order("ORDER-002")
    logger.info(f"✅ Order created: {order.id}")

    # Try to create duplicate order (should fail)
    try:
        service.create_order("ORDER-002")
    except ApplicationException as e:
        logger.error(f"❌ Application exception caught:")
        logger.error(f"   Code: {e.error_code.code}")
        logger.error(f"   Message: {e.error_code.message}")
        logger.error(f"   Details: {e.details}")

    # Try to get non-existent order (should fail)
    try:
        service.get_order("ORDER-999")
    except ApplicationException as e:
        logger.error(f"❌ Application exception caught:")
        logger.error(f"   Code: {e.error_code.code}")
        logger.error(f"   Message: {e.error_code.message}")
        logger.error(f"   Details: {e.details}")


async def demo_infrastructure_exception() -> None:
    """Demonstrate infrastructure exception."""
    logger.info("\n" + "=" * 60)
    logger.info("Demo 3: Infrastructure Exception")
    logger.info("=" * 60)

    repo = OrderRepository()
    order = Order("ORDER-003")
    order.add_item("PROD-001", 1, 99.99)

    # Save order successfully
    await repo.save(order)
    logger.info("✅ Order saved to database")

    # Find order successfully
    found = await repo.find_by_id("ORDER-003")
    logger.info(f"✅ Order found: {found['id']}")

    # Try to find non-existent order (should fail)
    try:
        await repo.find_by_id("ORDER-999")
    except InfrastructureException as e:
        logger.error(f"❌ Infrastructure exception caught:")
        logger.error(f"   Code: {e.error_code.code}")
        logger.error(f"   Message: {e.error_code.message}")
        logger.error(f"   Details: {e.details}")


def demo_exception_chaining() -> None:
    """Demonstrate exception chaining with __cause__."""
    logger.info("\n" + "=" * 60)
    logger.info("Demo 4: Exception Chaining")
    logger.info("=" * 60)

    try:
        # Simulate a database error
        try:
            raise ValueError("Database connection timeout")
        except ValueError as db_error:
            # Wrap as infrastructure exception
            raise InfrastructureException(
                error_code=CommonErrors.DATABASE_ERROR,
                details={"operation": "connect"},
                cause=db_error,  # Preserve original exception
            )
    except InfrastructureException as e:
        logger.error(f"❌ Infrastructure exception caught:")
        logger.error(f"   Code: {e.error_code.code}")
        logger.error(f"   Message: {e.error_code.message}")
        logger.error(f"   Details: {e.details}")
        if e.__cause__:
            logger.error(f"   Caused by: {type(e.__cause__).__name__}: {e.__cause__}")


def demo_to_dict() -> None:
    """Demonstrate converting exception to dictionary (for API responses)."""
    logger.info("\n" + "=" * 60)
    logger.info("Demo 5: Exception to Dictionary")
    logger.info("=" * 60)

    exc = DomainException(
        error_code=OrderErrors.ORDER_NOT_FOUND,
        details={"order_id": "123", "user_id": "456"},
    )

    # Convert to dictionary (for JSON API response)
    error_dict = exc.to_dict()

    logger.info("Exception as dictionary:")
    logger.info(f"  {error_dict}")
    logger.info("\nThis would be sent as JSON response:")
    import json

    logger.info(json.dumps(error_dict, indent=2))


async def main() -> None:
    """Run all demos."""
    logger.info("=" * 60)
    logger.info("Bento Framework - Exception System Examples")
    logger.info("=" * 60)

    # Run demos
    demo_domain_exception()
    demo_application_exception()
    await demo_infrastructure_exception()
    demo_exception_chaining()
    demo_to_dict()

    logger.info("\n" + "=" * 60)
    logger.info("✅ All demos completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    """Run the examples."""
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Examples interrupted by user")

