"""Initialize Database Tables

This script creates all database tables defined in the SQLAlchemy models.

Usage:
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

from config import settings

# Import all models to register them with SQLAlchemy
from contexts.catalog.infrastructure.models.product_po import ProductPO

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    """Initialize database"""
    print("🔧 Initializing database...")
    print(f"📍 Database URL: {settings.database_url}")

    # Get database config
    from api.deps import engine

    # Get Base from any model (they all share the same)
    Base = ProductPO.metadata

    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.create_all)

        print("✅ Database tables created successfully!")
        print("\n📋 Created tables:")
        for table in Base.sorted_tables:
            print(f"  - {table.name}")

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        raise
    finally:
        # Close engine
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
