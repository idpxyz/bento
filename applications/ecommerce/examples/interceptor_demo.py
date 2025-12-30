"""Demonstration of Interceptors in the ecommerce application.

This script demonstrates how Interceptors automatically handle:
1. Audit fields (created_at, updated_at, created_by, updated_by)
2. Soft delete (deleted_at, deleted_by)
3. Optimistic locking (version field)

Run with:
    cd /workspace/bento/applications/ecommerce
    uv run python examples/interceptor_demo.py
"""

import asyncio

from applications.ecommerce.persistence.models import OrderModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from applications.ecommerce.modules.order.domain.order import Order
from applications.ecommerce.runtime.composition import (
    close_db,
    create_order_repository_with_interceptors,
    get_session,
    init_db,
)
from bento.core.ids import ID


def print_separator(title: str = "") -> None:
    """Print a formatted separator."""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}\n")


async def demo_audit_fields():
    """Demonstrate automatic audit field population."""
    print_separator("DEMO 1: Automatic Audit Fields")

    # Initialize database
    await init_db()

    async for session in get_session():
        # Create repository with Interceptors (actor = "user-alice")
        repo = create_order_repository_with_interceptors(
            session=session, actor="user-alice"
        )

        # 1. CREATE: Create a new order
        print("1️⃣  Creating new order...")
        order = Order(
            order_id=ID.generate(),
            customer_id=ID.generate(),
        )
        order.add_item(
            product_id=ID.generate(),
            product_name="Laptop",
            quantity=1,
            unit_price=1299.99,
        )

        await repo.save(order)
        await session.commit()

        # Load from DB to see Interceptor effects
        result = await session.execute(
            select(OrderModel)
            .options(selectinload(OrderModel.items))
            .where(OrderModel.id == order.id.value)
        )
        order_model = result.scalar_one()

        print(f"✅ Order created: {order_model.id}")
        print(f"   created_at:  {order_model.created_at}")
        print(f"   created_by:  {order_model.created_by}")
        print(f"   updated_at:  {order_model.updated_at}")
        print(f"   updated_by:  {order_model.updated_by}")
        print(f"   version:     {order_model.version}")
        print(f"   deleted_at:  {order_model.deleted_at}")

        # 2. UPDATE: Pay the order (as different user)
        print("\n2️⃣  Updating order (paying)...")
        await asyncio.sleep(0.1)  # Small delay to see timestamp change

        # Change actor to simulate different user
        repo2 = create_order_repository_with_interceptors(
            session=session, actor="user-bob"
        )

        order2 = await repo2.find_by_id(ID(order.id.value))
        if order2:
            order2.pay()
            await repo2.save(order2)
            await session.commit()

        # Reload to see changes
        await session.refresh(order_model)

        print(f"✅ Order updated: {order_model.id}")
        print(f"   created_at:  {order_model.created_at} (unchanged)")
        print(f"   created_by:  {order_model.created_by} (unchanged)")
        print(f"   updated_at:  {order_model.updated_at} (CHANGED!)")
        print(f"   updated_by:  {order_model.updated_by} (CHANGED to user-bob!)")
        print(f"   version:     {order_model.version} (incremented!)")

        # 3. SOFT DELETE: Delete the order
        print("\n3️⃣  Soft deleting order...")
        await asyncio.sleep(0.1)

        repo3 = create_order_repository_with_interceptors(
            session=session, actor="user-admin"
        )

        order3 = await repo3.find_by_id(ID(order.id.value))
        if order3:
            await repo3.delete(order3)
            await session.commit()

        # Reload from DB to see soft delete
        result = await session.execute(
            select(OrderModel).where(OrderModel.id == order.id.value)
        )
        order_model_after_delete = result.scalar_one()

        print(f"✅ Order soft deleted: {order_model_after_delete.id}")
        print(f"   deleted_at:  {order_model_after_delete.deleted_at} (SET!)")
        print(f"   deleted_by:  {order_model_after_delete.deleted_by} (SET to user-admin!)")
        print(f"   is_deleted:  {order_model_after_delete.is_deleted} (computed property)")
        print(f"   version:     {order_model_after_delete.version}")

        print("\n✨ All Interceptors worked correctly!")


async def demo_version_management():
    """Demonstrate optimistic locking with version field."""
    print_separator("DEMO 2: Optimistic Locking (Version Management)")

    async for session in get_session():
        repo = create_order_repository_with_interceptors(
            session=session, actor="user-charlie"
        )

        # Create order
        print("1️⃣  Creating order...")
        order = Order(
            order_id=ID.generate(),
            customer_id=ID.generate(),
        )
        order.add_item(
            product_id=ID.generate(),
            product_name="Keyboard",
            quantity=2,
            unit_price=79.99,
        )

        await repo.save(order)
        await session.commit()

        # Check initial version
        result = await session.execute(
            select(OrderModel).where(OrderModel.id == order.id.value)
        )
        order_model = result.scalar_one()
        print(f"✅ Initial version: {order_model.version}")

        # Update 1
        print("\n2️⃣  First update...")
        order1 = await repo.find_by_id(ID(order.id.value))
        if order1:
            order1.add_item(
                product_id=ID.generate(),
                product_name="Mouse",
                quantity=1,
                unit_price=29.99,
            )
            await repo.save(order1)
            await session.commit()

        await session.refresh(order_model)
        print(f"✅ Version after update 1: {order_model.version} (incremented!)")

        # Update 2
        print("\n3️⃣  Second update...")
        order2 = await repo.find_by_id(ID(order.id.value))
        if order2:
            order2.pay()
            await repo.save(order2)
            await session.commit()

        await session.refresh(order_model)
        print(f"✅ Version after update 2: {order_model.version} (incremented again!)")

        print("\n✨ Version tracking prevents concurrent modification conflicts!")


async def demo_soft_delete_queries():
    """Demonstrate soft delete with query behavior."""
    print_separator("DEMO 3: Soft Delete Query Behavior")

    async for session in get_session():
        repo = create_order_repository_with_interceptors(
            session=session, actor="user-dave"
        )

        # Create 3 orders
        print("1️⃣  Creating 3 orders...")
        order_ids = []
        for i in range(3):
            order = Order(
                order_id=ID.generate(),
                customer_id=ID.generate(),
            )
            order.add_item(
                product_id=ID.generate(),
                product_name=f"Product {i+1}",
                quantity=1,
                unit_price=99.99 * (i + 1),
            )
            await repo.save(order)
            order_ids.append(order.id.value)

        await session.commit()
        print(f"✅ Created {len(order_ids)} orders")

        # Count all orders
        count_before = await repo.count()
        print(f"\n2️⃣  Total orders: {count_before}")

        # Soft delete first order
        print("\n3️⃣  Soft deleting first order...")
        order1 = await repo.find_by_id(ID(order_ids[0]))
        if order1:
            await repo.delete(order1)
            await session.commit()

        # Check soft delete in DB
        result = await session.execute(
            select(OrderModel).where(OrderModel.id == order_ids[0])
        )
        deleted_order = result.scalar_one()
        print("✅ Order soft deleted")
        print(f"   deleted_at: {deleted_order.deleted_at}")
        print(f"   deleted_by: {deleted_order.deleted_by}")
        print(f"   is_deleted: {deleted_order.is_deleted}")

        # Count should still include soft-deleted (if no spec filter)
        count_after = await repo.count()
        print(f"\n4️⃣  Total orders after soft delete: {count_after}")
        print("   (Note: Soft-deleted orders still in DB, just marked as deleted)")

        print("\n✨ Soft delete preserves data for audit/recovery!")


async def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "INTERCEPTOR DEMONSTRATION" + " " * 33 + "║")
    print("║" + " " * 78 + "║")
    print("║  This demonstrates Bento's Interceptor module in action" + " " * 20 + "║")
    print("║  in the ecommerce application." + " " * 46 + "║")
    print("╚" + "═" * 78 + "╝")

    try:
        # Run demonstrations
        await demo_audit_fields()
        await demo_version_management()
        await demo_soft_delete_queries()

        print_separator("🎉 ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
        print("\nKey Takeaways:")
        print("  ✅ Audit fields are automatically populated by AuditInterceptor")
        print("  ✅ Version field is automatically managed by OptimisticLockInterceptor")
        print("  ✅ Soft delete is automatically handled by SoftDeleteInterceptor")
        print("  ✅ All of this happens transparently in the repository layer")
        print("  ✅ Domain layer remains clean and focused on business logic")
        print("\n")

    finally:
        # Cleanup
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
