"""Database Access Example

This example demonstrates how to use the simplified database API for common operations.
"""

import asyncio
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from idp.framework.infrastructure.db import (
    Database,
    cleanup_database,
    connection,
    get_database,
    initialize_database,
    read_replica,
    session,
    transaction,
)
from idp.framework.infrastructure.db.config import (
    ConnectionConfig,
    CredentialsConfig,
    DatabaseConfig,
    DatabaseType,
    PoolConfig,
    ReadWriteConfig,
)


# Example model definition
class User(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool = True


# Example 1: Using the global function API (simplest approach)
async def example_global_api():
    """Example using global function API"""
    print("\n============ Example 1: Using global function API ============")

    # Create database session and execute simple query
    async with session() as db_session:
        # Use SQLAlchemy Core to execute simple SQL
        result = await db_session.execute(text("SELECT 1 as test"))
        row = result.first()
        print(f"Query result: {row.test}")

    # Execute operations in a transaction
    async with transaction() as db_session:
        print("Executing operations in a transaction...")
        # Execute some operations that require a transaction...

    # Use direct connection (lower-level access)
    async with connection() as conn:
        result = await conn.execute(text("SELECT 'Direct connection' as access_type"))
        # Correctly handle the result from the raw connection
        row = result.fetchone()
        print(f"Connection access: {row[0]}")

    # Use read replica (if enabled)
    try:
        async with read_replica() as db_session:
            result = await db_session.execute(text("SELECT now()"))
            row = result.first()
            print(f"Time from read replica: {row[0]}")
    except RuntimeError as e:
        print(f"Read replica not enabled: {e}")


# Example 2: Using the Database facade class
async def example_database_facade():
    """Example using Database facade class"""
    print("\n============ Example 2: Using Database facade class ============")

    db = get_database()

    # Execute SQL directly
    result = await db.execute("SELECT 42 as answer")
    row = result.first()
    print(f"The answer to life, universe and everything: {row.answer}")

    # Execute queries in batch
    results = await db.execute_many([
        "SELECT 'hello' as greeting",
        "SELECT 'world' as target"
    ])
    print(
        f"Batch query results: {results[0].first()[0]} {results[1].first()[0]}")

    # Check database health status
    is_healthy = await db.health_check()
    print(
        f"Database health status: {'healthy' if is_healthy else 'unhealthy'}")

    # Get database statistics
    stats = await db.get_stats()
    print(f"Database statistics: {stats}")


# Example 3: Implementing a simple user repository
class UserRepository:
    """User repository example

    Demonstrates how to use the database API in a repository pattern.
    """

    def __init__(self, db: Database):
        self.db = db

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID

        Args:
            user_id: User ID

        Returns:
            Optional[User]: The found user, or None if not found
        """
        async with self.db.session() as db_session:
            # Assume there's a users table
            stmt = text(
                "SELECT id, name, email, is_active FROM users WHERE id = :id")
            result = await db_session.execute(stmt, {"id": user_id})
            row = result.first()

            if not row:
                return None

            return User(
                id=row.id,
                name=row.name,
                email=row.email,
                is_active=row.is_active
            )

    async def create(self, user: User) -> User:
        """Create user

        Args:
            user: User to create

        Returns:
            User: Created user (with ID)
        """
        async with self.db.transaction() as db_session:
            # Insert user and return generated ID
            stmt = text("""
                INSERT INTO users (name, email, is_active) 
                VALUES (:name, :email, :is_active)
                RETURNING id
            """)
            result = await db_session.execute(
                stmt,
                {
                    "name": user.name,
                    "email": user.email,
                    "is_active": user.is_active
                }
            )
            user_id = result.scalar_one()

            # Return complete user object
            return User(id=user_id, **user.model_dump(exclude={"id"}))

    async def update(self, user: User) -> bool:
        """Update user

        Args:
            user: User to update

        Returns:
            bool: Whether update was successful
        """
        async with self.db.transaction() as db_session:
            stmt = text("""
                UPDATE users 
                SET name = :name, email = :email, is_active = :is_active
                WHERE id = :id
            """)
            result = await db_session.execute(
                stmt,
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "is_active": user.is_active
                }
            )
            return result.rowcount > 0

    async def delete(self, user_id: int) -> bool:
        """Delete user

        Args:
            user_id: User ID

        Returns:
            bool: Whether deletion was successful
        """
        async with self.db.transaction() as db_session:
            stmt = text("DELETE FROM users WHERE id = :id")
            result = await db_session.execute(stmt, {"id": user_id})
            return result.rowcount > 0

    async def find_all_active(self) -> List[User]:
        """Find all active users

        Returns:
            List[User]: List of active users
        """
        # Use read replica if read-write split is enabled
        try:
            async with self.db.read_replica() as db_session:
                return await self._find_active_users(db_session)
        except RuntimeError:
            # Fall back to main database
            async with self.db.session() as db_session:
                return await self._find_active_users(db_session)

    async def _find_active_users(self, db_session: AsyncSession) -> List[User]:
        """Internal method: Find active users from given session"""
        stmt = text(
            "SELECT id, name, email, is_active FROM users WHERE is_active = true")
        result = await db_session.execute(stmt)

        users = []
        for row in result:
            users.append(User(
                id=row.id,
                name=row.name,
                email=row.email,
                is_active=row.is_active
            ))
        return users


async def example_repository_pattern():
    """Example using repository pattern"""
    print("\n============ Example 3: Using repository pattern ============")

    # Create user repository
    user_repo = UserRepository(get_database())

    # Simulate repository operations (not actually executed)
    print("Getting user with ID=1 from repository")
    print("Creating new user: Alice")
    print("Updating user information: Bob")
    print("Deleting user with ID=3")
    print("Querying all active users")


# Main function
async def main():
    """Main function"""
    # Configure database
    config = DatabaseConfig(
        type=DatabaseType.POSTGRESQL,
        connection=ConnectionConfig(
            host="192.168.8.137",
            port=5438,
            database="idp",
            application_name="database_example"
        ),
        credentials=CredentialsConfig(
            username="topsx",
            password="thends",
        ),
        pool=PoolConfig(
            min_size=5,
            max_size=20,
            pre_ping=True
        ),
        read_write=ReadWriteConfig(
            enable_read_write_split=True
        )
    )

    try:
        # Initialize database
        print("Initializing database...")
        await initialize_database(config)

        # Run examples
        await example_global_api()
        await example_database_facade()
        await example_repository_pattern()

    except Exception as e:
        print(f"Error running examples: {e}")
    finally:
        # Clean up resources
        print("\nCleaning up database resources...")
        await cleanup_database()


if __name__ == "__main__":
    # Run main function
    asyncio.run(main())
