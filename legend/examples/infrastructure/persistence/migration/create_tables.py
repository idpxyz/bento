"""Create database tables for the example application."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from idp.framework.examples.infrastructure.persistence.po.route_plan import RoutePlanPO
from idp.framework.examples.infrastructure.persistence.po.stop import StopPO
from idp.framework.infrastructure.persistence.sqlalchemy.po.base import Base
from idp.framework.infrastructure.persistence.sqlalchemy.po.outbox import OutboxPO

# Database connection string
DB_DSN = "postgresql+asyncpg://postgres:thends@192.168.8.195/mydb"


async def create_tables():
    """Create all database tables."""
    engine = create_async_engine(DB_DSN)

    async with engine.begin() as conn:
        # Drop existing tables if exists
        await conn.execute(text("DROP TABLE IF EXISTS route_plan CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS stop CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS outbox CASCADE"))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

        # Verify table structure
        for table_name in ['route_plan', 'stop', 'outbox']:
            result = await conn.execute(text(f"""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position;
            """))
            columns = result.fetchall()
            print(f"\nTable '{table_name}' columns:")
            for col in columns:
                print(f"- {col[0]}: {col[1]}{f'({col[2]})' if col[2] else ''}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(create_tables())
