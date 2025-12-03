"""Initialize Database Tables

This script creates all database tables defined in the SQLAlchemy models.

Usage:
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root and bento src to path FIRST (before any imports)
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


async def main():
    """Initialize database"""
    print("🔧 Initializing database...")

    # Import config
    from config import settings

    print(f"📍 Database URL: {settings.database_url}")

    # Import all models to register them with SQLAlchemy metadata
    # These imports MUST happen BEFORE Base.metadata is used
    print("📦 Importing models...")
    from contexts.catalog.infrastructure.models.category_po import CategoryPO

    print(f"  CategoryPO: {CategoryPO}")
    from contexts.catalog.infrastructure.models.product_po import ProductPO

    print(f"  ProductPO: {ProductPO}")
    from contexts.identity.infrastructure.models.user_po import UserPO

    print(f"  UserPO: {UserPO}")

    # ✅ Import Ordering models
    from contexts.ordering.infrastructure.models.order_po import OrderPO

    print(f"  OrderPO: {OrderPO}")
    from contexts.ordering.infrastructure.models.orderitem_po import OrderItemPO

    print(f"  OrderItemPO: {OrderItemPO}")

    # ✅ Import OutboxRecord to create outbox table
    from bento.persistence.outbox.record import OutboxRecord

    print(f"  OutboxRecord: {OutboxRecord}")

    # Import Base AFTER models
    from bento.persistence import Base

    print(f"Base imported: {Base}")
    print(f"Base.metadata.tables at import: {list(Base.metadata.tables.keys())}")

    print(f"📊 Registered tables: {len(Base.metadata.tables)}")
    print(f"   Tables: {list(Base.metadata.tables.keys())}")

    # Get database config
    from shared.infrastructure.dependencies import engine

    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("✅ Database tables created successfully!")
        print("\n📋 Created tables:")
        for table in Base.metadata.sorted_tables:
            print(f"  - {table.name}")

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise
    finally:
        # Close engine
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
