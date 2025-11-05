"""Dependency Injection Example

This example demonstrates how to use the database API with a dependency injection framework.
Using Python-DI as the dependency injection container.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel
from sqlalchemy import text

from idp.framework.infrastructure.db.config import (
    ConnectionConfig,
    CredentialsConfig,
    DatabaseConfig,
    DatabaseType,
    PoolConfig,
    ReadWriteConfig,
)
from idp.framework.infrastructure.db.database import (
    Database,
    cleanup_database,
    initialize_database,
)
from idp.framework.infrastructure.di.container import Container


# Domain model
class User(BaseModel):
    """User domain model"""
    id: int
    name: str
    email: str
    is_active: bool = True


# Define repository interface
class UserRepository(ABC):
    """User repository interface"""
    
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        pass
        
    @abstractmethod
    async def find_all(self) -> List[User]:
        """Get all users"""
        pass
        
    @abstractmethod
    async def create(self, user: Dict[str, Any]) -> User:
        """Create user"""
        pass
        
    @abstractmethod
    async def update(self, user_id: int, user_data: Dict[str, Any]) -> Optional[User]:
        """Update user"""
        pass
        
    @abstractmethod
    async def delete(self, user_id: int) -> bool:
        """Delete user"""
        pass


# Repository implementation
class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy user repository implementation"""
    
    def __init__(self, db: Database):
        self.db = db
        
    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        async with self.db.session() as session:
            result = await session.execute(
                text("SELECT id, name, email, is_active FROM users WHERE id = :id"),
                {"id": user_id}
            )
            row = result.first()
            if not row:
                return None
                
            return User(
                id=row.id,
                name=row.name,
                email=row.email,
                is_active=row.is_active
            )
            
    async def find_all(self) -> List[User]:
        """Get all users"""
        async with self.db.session() as session:
            result = await session.execute(
                text("SELECT id, name, email, is_active FROM users")
            )
            return [
                User(
                    id=row.id,
                    name=row.name,
                    email=row.email,
                    is_active=row.is_active
                )
                for row in result.fetchall()
            ]
            
    async def create(self, user_data: Dict[str, Any]) -> User:
        """Create user"""
        async with self.db.transaction() as session:
            result = await session.execute(
                text("""
                    INSERT INTO users (name, email, is_active)
                    VALUES (:name, :email, :is_active)
                    RETURNING id, name, email, is_active
                """),
                user_data
            )
            row = result.first()
            return User(
                id=row.id,
                name=row.name,
                email=row.email,
                is_active=row.is_active
            )
            
    async def update(self, user_id: int, user_data: Dict[str, Any]) -> Optional[User]:
        """Update user"""
        # Build update statement
        set_clause_parts = []
        params = {"id": user_id}
        
        for key, value in user_data.items():
            set_clause_parts.append(f"{key} = :{key}")
            params[key] = value
            
        if not set_clause_parts:
            # No fields to update
            return await self.get_by_id(user_id)
            
        set_clause = ", ".join(set_clause_parts)
        query = f"UPDATE users SET {set_clause} WHERE id = :id RETURNING id, name, email, is_active"
        
        async with self.db.transaction() as session:
            result = await session.execute(text(query), params)
            row = result.first()
            
            if not row:
                return None
                
            return User(
                id=row.id,
                name=row.name,
                email=row.email,
                is_active=row.is_active
            )
            
    async def delete(self, user_id: int) -> bool:
        """Delete user"""
        async with self.db.transaction() as session:
            result = await session.execute(
                text("DELETE FROM users WHERE id = :id"),
                {"id": user_id}
            )
            return result.rowcount > 0


# Service interface
class UserService(Protocol):
    """User service interface"""
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user"""
        ...
        
    async def list_users(self) -> List[User]:
        """List all users"""
        ...
        
    async def create_user(self, name: str, email: str, is_active: bool = True) -> User:
        """Create user"""
        ...
        
    async def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user"""
        ...
        
    async def delete_user(self, user_id: int) -> bool:
        """Delete user"""
        ...


# Service implementation
class UserServiceImpl:
    """User service implementation"""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
        
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user"""
        return await self.user_repository.get_by_id(user_id)
        
    async def list_users(self) -> List[User]:
        """List all users"""
        return await self.user_repository.find_all()
        
    async def create_user(self, name: str, email: str, is_active: bool = True) -> User:
        """Create user"""
        user_data = {
            "name": name,
            "email": email,
            "is_active": is_active
        }
        return await self.user_repository.create(user_data)
        
    async def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user"""
        valid_fields = {"name", "email", "is_active"}
        update_data = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
        return await self.user_repository.update(user_id, update_data)
        
    async def delete_user(self, user_id: int) -> bool:
        """Delete user"""
        return await self.user_repository.delete(user_id)


# Dependency injection configuration
async def setup_di_container() -> Container:
    """Set up dependency injection container"""
    
    # Configure database
    config = DatabaseConfig(
        type=DatabaseType.POSTGRESQL,
        connection=ConnectionConfig(
            host="localhost",
            port=5432,
            database="idp",
        ),
        credentials=CredentialsConfig(
            username="postgres", 
            password="postgres",
        ),
        pool=PoolConfig(
            min_size=5,
            max_size=20
        ),
        read_write=ReadWriteConfig(
            enable_read_write_split=False
        ),
        retry_attempts=3,
        retry_interval=1.0,
    )
    
    # Initialize database
    db = await initialize_database(config)
    
    # Create container
    container = Container()
    
    # Register database
    container.bind(Database, db)
    
    # Register repository
    container.bind(UserRepository, Dependent(SQLAlchemyUserRepository, scope="singleton"))
    
    # Register service
    container.bind(UserService, Dependent(UserServiceImpl, scope="singleton"))
    
    return container


# Application example
async def run_example(container: Container):
    """Run example"""
    print("\n===== Dependency Injection Usage Example =====")
    
    # Get user service
    user_service = container.get(UserService)
    
    # Create users
    user1 = await user_service.create_user(
        name="Alice", 
        email="alice@example.com"
    )
    print(f"Created user: {user1}")
    
    user2 = await user_service.create_user(
        name="Bob", 
        email="bob@example.com", 
        is_active=False
    )
    print(f"Created user: {user2}")
    
    # Get user
    retrieved_user = await user_service.get_user(user1.id)
    print(f"Retrieved user: {retrieved_user}")
    
    # List all users
    users = await user_service.list_users()
    print(f"All users: {users}")
    
    # Update user
    updated_user = await user_service.update_user(
        user_id=user2.id,
        name="Robert",
        is_active=True
    )
    print(f"Updated user: {updated_user}")
    
    # Delete user
    deleted = await user_service.delete_user(user1.id)
    print(f"Deleted user (ID={user1.id}): {'successful' if deleted else 'failed'}")
    
    # List all users again
    users = await user_service.list_users()
    print(f"Remaining users: {users}")


async def main():
    """Main function"""
    try:
        # Set up table structure
        db = await initialize_database(DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            connection=ConnectionConfig(
                host="192.168.8.137",
                port=5438,
                database="idp",
            ),
            credentials=CredentialsConfig(
                username="topsx", 
                password="thends",
            ),
            pool=PoolConfig(
                min_size=2,
                max_size=10
            )
        ))
        
        # Create table
        async with db.session() as session:
            await session.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE
                )
            """))
            
            # Clear table data to ensure example runs properly
            await session.execute(text("TRUNCATE TABLE users RESTART IDENTITY"))
            await session.commit()
            
        # Set up dependency injection container
        container = await setup_di_container()
        
        # Run example
        await run_example(container)
        
    except Exception as e:
        print(f"Error running example: {e}")
    finally:
        # Clean up resources
        await cleanup_database()


if __name__ == "__main__":
    asyncio.run(main()) 