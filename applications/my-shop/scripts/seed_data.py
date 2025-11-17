"""Seed Database with Sample Data

This script populates the database with sample data for demonstration.

Usage:
    python scripts/seed_data.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bento.core.ids import ID
from sqlalchemy import select

from api.deps import engine, session_factory
from contexts.catalog.domain.category import Category
from contexts.catalog.domain.product import Product
from contexts.catalog.infrastructure.mappers.category_mapper import CategoryMapper
from contexts.catalog.infrastructure.mappers.product_mapper import ProductMapper
from contexts.catalog.infrastructure.models.category_po import CategoryPO
from contexts.catalog.infrastructure.models.product_po import ProductPO
from contexts.identity.domain.user import User
from contexts.identity.infrastructure.mappers.user_mapper import UserMapper
from contexts.identity.infrastructure.models.user_po import UserPO


async def clear_data():
    """Clear existing data"""
    print("🗑️  Clearing existing data...")
    async with session_factory() as session:
        # Delete in correct order (respect foreign keys)
        await session.execute("DELETE FROM products")
        await session.execute("DELETE FROM categories")
        await session.execute("DELETE FROM users")
        await session.commit()
    print("✅ Data cleared")


async def seed_categories():
    """Seed categories"""
    print("\n📁 Seeding categories...")

    categories_data = [
        {"name": "电子产品", "description": "手机、电脑、数码产品"},
        {"name": "图书", "description": "各类图书、教材、小说"},
        {"name": "服装", "description": "男装、女装、童装"},
        {"name": "食品", "description": "零食、饮料、生鲜"},
        {"name": "家居", "description": "家具、装饰、日用品"},
    ]

    async with session_factory() as session:
        mapper = CategoryMapper()
        created_categories = []

        for data in categories_data:
            # Create domain object
            category = Category(
                id=str(ID.generate()),
                name=data["name"],
                description=data.get("description"),
            )

            # Convert to PO and save
            po = mapper.to_po(category)
            session.add(po)
            created_categories.append(category)

            print(f"  + {category.name}")

        await session.commit()
        print(f"✅ Created {len(created_categories)} categories")
        return created_categories


async def seed_products(categories):
    """Seed products"""
    print("\n📦 Seeding products...")

    # Get category IDs for reference
    electronics_id = categories[0].id
    books_id = categories[1].id
    clothing_id = categories[2].id
    food_id = categories[3].id

    products_data = [
        # Electronics
        {
            "name": "iPhone 15 Pro",
            "price": 7999.00,
            "stock": 50,
            "category_id": electronics_id,
            "description": "Apple 最新旗舰手机，A17 Pro 芯片，钛金属机身",
        },
        {
            "name": "MacBook Pro 14",
            "price": 14999.00,
            "stock": 30,
            "category_id": electronics_id,
            "description": "M3 Pro 芯片，14 英寸 Liquid Retina XDR 显示屏",
        },
        {
            "name": "AirPods Pro 2",
            "price": 1899.00,
            "stock": 100,
            "category_id": electronics_id,
            "description": "主动降噪，空间音频，USB-C 充电",
        },
        {
            "name": "iPad Air",
            "price": 4799.00,
            "stock": 60,
            "category_id": electronics_id,
            "description": "10.9 英寸，M1 芯片，支持 Apple Pencil",
        },
        # Books
        {
            "name": "领域驱动设计",
            "price": 89.00,
            "stock": 200,
            "category_id": books_id,
            "description": "Eric Evans 经典著作，软件核心复杂性应对之道",
        },
        {
            "name": "Clean Architecture",
            "price": 79.00,
            "stock": 150,
            "category_id": books_id,
            "description": "Robert Martin 的架构整洁之道",
        },
        {
            "name": "Designing Data-Intensive Applications",
            "price": 128.00,
            "stock": 120,
            "category_id": books_id,
            "description": "数据密集型应用系统设计",
        },
        {
            "name": "Python 编程从入门到实践",
            "price": 99.00,
            "stock": 300,
            "category_id": books_id,
            "description": "适合初学者的 Python 教程",
        },
        # Clothing
        {
            "name": "优衣库 T恤",
            "price": 79.00,
            "stock": 500,
            "category_id": clothing_id,
            "description": "纯棉基础款，多色可选",
        },
        {
            "name": "Levi's 牛仔裤",
            "price": 499.00,
            "stock": 200,
            "category_id": clothing_id,
            "description": "经典 501 款式，舒适耐穿",
        },
        {
            "name": "Nike 运动鞋",
            "price": 699.00,
            "stock": 150,
            "category_id": clothing_id,
            "description": "Air Max 系列，气垫缓震",
        },
        # Food
        {
            "name": "三只松鼠坚果",
            "price": 39.90,
            "stock": 1000,
            "category_id": food_id,
            "description": "每日坚果，混合装",
        },
        {
            "name": "元气森林气泡水",
            "price": 5.00,
            "stock": 2000,
            "category_id": food_id,
            "description": "0糖0脂0卡，白桃味",
        },
        {
            "name": "良品铺子零食",
            "price": 59.90,
            "stock": 800,
            "category_id": food_id,
            "description": "零食大礼包，多种口味",
        },
    ]

    async with session_factory() as session:
        mapper = ProductMapper()
        created_products = []

        for data in products_data:
            # Create domain object
            product = Product(
                id=str(ID.generate()),
                name=data["name"],
                price=data["price"],
                stock=data["stock"],
                category_id=data.get("category_id"),
                description=data.get("description"),
            )

            # Convert to PO and save
            po = mapper.to_po(product)
            session.add(po)
            created_products.append(product)

            print(f"  + {product.name} - ¥{product.price}")

        await session.commit()
        print(f"✅ Created {len(created_products)} products")
        return created_products


async def seed_users():
    """Seed users"""
    print("\n👥 Seeding users...")

    users_data = [
        {"name": "张三", "email": "zhangsan@example.com"},
        {"name": "李四", "email": "lisi@example.com"},
        {"name": "王五", "email": "wangwu@example.com"},
        {"name": "赵六", "email": "zhaoliu@example.com"},
        {"name": "测试用户", "email": "test@example.com"},
    ]

    async with session_factory() as session:
        mapper = UserMapper()
        created_users = []

        for data in users_data:
            # Create domain object
            user = User(
                id=str(ID.generate()),
                name=data["name"],
                email=data["email"],
            )

            # Convert to PO and save
            po = mapper.to_po(user)
            session.add(po)
            created_users.append(user)

            print(f"  + {user.name} ({user.email})")

        await session.commit()
        print(f"✅ Created {len(created_users)} users")
        return created_users


async def verify_data():
    """Verify seeded data"""
    print("\n🔍 Verifying data...")

    async with session_factory() as session:
        # Count categories
        result = await session.execute(select(CategoryPO))
        categories = result.scalars().all()
        print(f"  📁 Categories: {len(categories)}")

        # Count products
        result = await session.execute(select(ProductPO))
        products = result.scalars().all()
        print(f"  📦 Products: {len(products)}")

        # Count users
        result = await session.execute(select(UserPO))
        users = result.scalars().all()
        print(f"  👥 Users: {len(users)}")

        print("✅ Data verification complete")


async def main():
    """Main seed function"""
    print("=" * 60)
    print("🌱 Seeding my-shop Database")
    print("=" * 60)

    try:
        # Clear existing data
        await clear_data()

        # Seed data in order
        categories = await seed_categories()
        products = await seed_products(categories)
        users = await seed_users()

        # Verify
        await verify_data()

        print("\n" + "=" * 60)
        print("✅ Database seeding completed successfully!")
        print("=" * 60)
        print("\n💡 Next steps:")
        print("  1. Start the server: make dev")
        print("  2. Visit API docs: http://localhost:8000/docs")
        print("  3. Try the API: curl http://localhost:8000/api/v1/products")
        print()

    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Close engine
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
