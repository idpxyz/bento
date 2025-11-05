"""Quick script to check database contents."""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from applications.ecommerce.persistence.models import OrderItemModel, OrderModel
from applications.ecommerce.runtime.composition import init_db

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


async def check_database():
    """Check orders and items in database."""
    engine = create_async_engine("sqlite+aiosqlite:///./ecommerce.db")
    async_session = async_sessionmaker(engine, class_=AsyncSession)

    # Ensure tables exist
    await init_db()

    async with async_session() as session:
        # Get all orders
        result = await session.execute(select(OrderModel))
        orders = result.scalars().all()

        print(f"Total orders: {len(orders)}")
        print()

        for order in orders:
            # Get items for this order
            items_result = await session.execute(
                select(OrderItemModel).where(OrderItemModel.order_id == order.id)
            )
            items = items_result.scalars().all()

            print(f"Order ID: {order.id}")
            print(f"  Customer: {order.customer_id}")
            print(f"  Status: {order.status}")
            print(f"  Items in DB: {len(items)}")
            for item in items:
                print(f"    - {item.product_name} x{item.quantity} @ ${item.unit_price}")
            print()


if __name__ == "__main__":
    asyncio.run(check_database())
