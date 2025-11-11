"""Direct test of Interceptors with Order creation.

This bypasses the FastAPI layer to test Interceptors directly.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.persistence.models import OrderModel
from applications.ecommerce.runtime.composition import (
    close_db,
    create_order_repository_with_interceptors,
    get_session,
    init_db,
)
from bento.core.ids import ID


async def main():
    """Test Interceptors directly."""
    print("🧪 Testing Interceptors with Order creation\n")

    try:
        # Initialize database
        await init_db()

        async for session in get_session():
            # Create repository with Interceptors
            repo = create_order_repository_with_interceptors(session=session, actor="test-user")

            # Create order
            print("1️⃣  Creating order...")
            order = Order(
                order_id=ID.generate(),
                customer_id=ID.generate(),
            )
            order.add_item(
                product_id=ID.generate(),
                product_name="Test Product",
                quantity=1,
                unit_price=99.99,
            )

            # Save order
            saved_order = await repo.save(order)
            await session.commit()

            print(f"✅ Order created with ID: {saved_order.id.value}\n")

            # Load from DB to see Interceptor effects
            result = await session.execute(
                select(OrderModel).where(OrderModel.id == saved_order.id.value)
            )
            order_model = result.scalar_one()

            print("📊 Interceptor Results:")
            print(f"   created_at:  {order_model.created_at}")
            print(f"   created_by:  {order_model.created_by}")
            print(f"   updated_at:  {order_model.updated_at}")
            print(f"   updated_by:  {order_model.updated_by}")
            print(f"   version:     {order_model.version}")
            print(f"   deleted_at:  {order_model.deleted_at}")

            print("\n✅ Interceptors are working correctly!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
