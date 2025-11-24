"""Initialize database tables for ecommerce application.

Run this script before starting the application:
    cd /workspace/bento
    uv run python applications/ecommerce/init_db.py
"""

import asyncio
import sys
from pathlib import Path

from applications.ecommerce.runtime.composition import close_db, init_db

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def main():
    """Initialize database tables."""
    print("🔄 Initializing database tables...")

    try:
        # Import to trigger model registration
        import bento.persistence.sqlalchemy.outbox_sql  # noqa: F401

        await init_db()
        print("✅ Database tables initialized successfully!")
        print("\nTables created:")
        print("  - orders (with audit, soft-delete, optimistic-lock fields)")
        print("  - order_items")
        print("  - outbox (framework - for event publishing)")

        # Verify tables
        from sqlalchemy import text

        from applications.ecommerce.runtime.composition import engine

        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            tables = [row[0] for row in result.fetchall()]
            print(f"\n📊 Verified tables: {', '.join(tables)}")

        print("\n🚀 You can now start the application with:")
        print("   cd /workspace/bento")
        print("   uv run uvicorn applications.ecommerce.main:app --reload")

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
