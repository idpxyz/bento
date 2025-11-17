"""Initialize Database Tables

This script creates all database tables defined in the SQLAlchemy models.

Usage:
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Import all models to register them with SQLAlchemy
from bento.persistence import Base

from config import settings

# Add project root and bento src to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


async def main():
    """Initialize database"""
    print("🔧 Initializing database...")
    print(f"📍 Database URL: {settings.database_url}")

    # Get database config
    from api.deps import engine

    # Use Bento's Base metadata (all models inherit from it)
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
