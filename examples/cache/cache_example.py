"""Cache System - Complete Example.

This example demonstrates the complete cache functionality:
1. Memory Cache for fast local caching
2. Redis Cache for distributed caching
3. @cached decorator for automatic caching
4. Cache-aside pattern
5. Cache invalidation
"""

import asyncio
import logging
import random
import time
from typing import Any

from adapters.cache import CacheBackend, CacheConfig, create_cache
from adapters.cache.decorators import cache_aside, cached, invalidate_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


# ==================== Sample Data and Functions ====================


async def expensive_database_query(user_id: str) -> dict[str, Any]:
    """Simulate expensive database query.

    Args:
        user_id: User ID to fetch

    Returns:
        User data dictionary
    """
    logger.info(f"🔍 Executing expensive database query for user: {user_id}")

    # Simulate slow database query
    await asyncio.sleep(1)

    return {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
        "created_at": "2025-01-01",
    }


async def calculate_report(report_id: str) -> dict[str, Any]:
    """Simulate expensive report calculation.

    Args:
        report_id: Report ID

    Returns:
        Report data
    """
    logger.info(f"📊 Calculating complex report: {report_id}")

    # Simulate expensive calculation
    await asyncio.sleep(2)

    return {
        "report_id": report_id,
        "total_users": random.randint(1000, 10000),
        "revenue": random.uniform(10000, 100000),
        "calculated_at": time.time(),
    }


# ==================== Demo Functions ====================


async def demo_memory_cache() -> None:
    """Demonstrate memory cache usage."""

    logger.info("\n" + "=" * 80)
    logger.info("Demo 1: Memory Cache")
    logger.info("=" * 80)

    # Create memory cache
    config = CacheConfig(
        backend=CacheBackend.MEMORY,
        prefix="demo:",
        ttl=60,  # 1 minute
        max_size=1000,
    )

    cache = await create_cache(
        backend="memory",
        prefix="demo:",
        ttl=60,
    )

    logger.info("✅ Memory cache created")

    # Basic operations
    logger.info("\n📋 Basic Operations:")

    # Set value
    await cache.set("user:123", {"name": "John", "age": 30})
    logger.info("✅ Set value: user:123")

    # Get value
    user = await cache.get("user:123")
    logger.info(f"✅ Get value: {user}")

    # Check existence
    exists = await cache.exists("user:123")
    logger.info(f"✅ Exists: {exists}")

    # Delete value
    await cache.delete("user:123")
    logger.info("✅ Deleted: user:123")

    # Verify deletion
    user = await cache.get("user:123")
    logger.info(f"✅ After delete: {user}")  # Should be None

    # Batch operations
    logger.info("\n📋 Batch Operations:")

    await cache.set_many({
        "user:1": {"name": "Alice"},
        "user:2": {"name": "Bob"},
        "user:3": {"name": "Charlie"},
    }, ttl=300)
    logger.info("✅ Set multiple users")

    users = await cache.get_many(["user:1", "user:2", "user:3"])
    logger.info(f"✅ Get multiple users: {users}")

    # Pattern deletion
    deleted = await cache.delete_pattern("user:*")
    logger.info(f"✅ Deleted {deleted} keys matching 'user:*'")

    # Cleanup
    await cache.close()
    logger.info("✅ Cache closed")


async def demo_redis_cache() -> None:
    """Demonstrate Redis cache usage.

    Note: Requires Redis running at localhost:6379
    """

    logger.info("\n" + "=" * 80)
    logger.info("Demo 2: Redis Cache")
    logger.info("=" * 80)

    try:
        # Create Redis cache
        cache = await create_cache(
            backend="redis",
            prefix="demo:",
            ttl=60,
            redis_url="redis://localhost:6379/0",
        )

        logger.info("✅ Redis cache created")

        # Set value
        await cache.set("user:456", {"name": "Jane", "age": 25})
        logger.info("✅ Set value in Redis")

        # Get value
        user = await cache.get("user:456")
        logger.info(f"✅ Get value from Redis: {user}")

        # Cleanup
        await cache.delete("user:456")
        await cache.close()
        logger.info("✅ Redis cache closed")

    except Exception as e:
        logger.warning(f"⚠️  Redis not available: {e}")
        logger.info("Skipping Redis demo (Redis not running)")


async def demo_cached_decorator() -> None:
    """Demonstrate @cached decorator."""

    logger.info("\n" + "=" * 80)
    logger.info("Demo 3: @cached Decorator")
    logger.info("=" * 80)

    # Create cache
    cache = await create_cache(backend="memory", prefix="cached:", ttl=300)

    # Decorate function
    @cached(cache, ttl=60, key_prefix="user:")
    async def get_user(user_id: str) -> dict[str, Any]:
        return await expensive_database_query(user_id)

    logger.info("\n📋 First call (cache miss):")
    start = time.time()
    user1 = await get_user("123")
    duration1 = time.time() - start
    logger.info(f"✅ User: {user1}")
    logger.info(f"⏱️  Duration: {duration1:.2f}s")

    logger.info("\n📋 Second call (cache hit):")
    start = time.time()
    user2 = await get_user("123")
    duration2 = time.time() - start
    logger.info(f"✅ User: {user2}")
    logger.info(f"⏱️  Duration: {duration2:.4f}s (should be instant!)")

    logger.info(f"\n🚀 Speedup: {duration1 / duration2:.0f}x faster!")

    # Cleanup
    await cache.close()


async def demo_cache_aside() -> None:
    """Demonstrate cache-aside pattern."""

    logger.info("\n" + "=" * 80)
    logger.info("Demo 4: Cache-Aside Pattern")
    logger.info("=" * 80)

    # Create cache
    cache = await create_cache(backend="memory", prefix="report:", ttl=300)

    # Create cache-aside function
    get_report = cache_aside(
        cache,
        loader=calculate_report,
        ttl=120,
        key_prefix="report:",
    )

    logger.info("\n📋 First call (loads from source):")
    start = time.time()
    report1 = await get_report("monthly-2025")
    duration1 = time.time() - start
    logger.info(f"✅ Report: {report1}")
    logger.info(f"⏱️  Duration: {duration1:.2f}s")

    logger.info("\n📋 Second call (returns from cache):")
    start = time.time()
    report2 = await get_report("monthly-2025")
    duration2 = time.time() - start
    logger.info(f"✅ Report: {report2}")
    logger.info(f"⏱️  Duration: {duration2:.4f}s")

    # Cleanup
    await cache.close()


async def demo_cache_invalidation() -> None:
    """Demonstrate cache invalidation."""

    logger.info("\n" + "=" * 80)
    logger.info("Demo 5: Cache Invalidation")
    logger.info("=" * 80)

    # Create cache
    cache = await create_cache(backend="memory", prefix="inv:", ttl=300)

    # Populate cache
    await cache.set_many({
        "user:1": {"name": "Alice"},
        "user:2": {"name": "Bob"},
        "user:3": {"name": "Charlie"},
    })
    logger.info("✅ Populated cache with 3 users")

    # Define update function with invalidation
    @invalidate_cache(cache, pattern="user:*")
    async def update_all_users() -> None:
        logger.info("📝 Updating all users in database...")
        await asyncio.sleep(0.5)  # Simulate DB update

    # Check cache before invalidation
    user = await cache.get("user:1")
    logger.info(f"✅ Before invalidation: {user}")

    # Trigger update (with invalidation)
    await update_all_users()
    logger.info("✅ Cache invalidated after update")

    # Check cache after invalidation
    user = await cache.get("user:1")
    logger.info(f"✅ After invalidation: {user}")  # Should be None

    # Cleanup
    await cache.close()


async def main() -> None:
    """Run all cache demos."""

    logger.info("=" * 80)
    logger.info("Cache System - Complete Example")
    logger.info("=" * 80)

    # Run demos
    await demo_memory_cache()
    await demo_redis_cache()
    await demo_cached_decorator()
    await demo_cache_aside()
    await demo_cache_invalidation()

    logger.info("\n" + "=" * 80)
    logger.info("✅ All demos completed!")
    logger.info("=" * 80)


if __name__ == "__main__":
    """Run the example.

    Prerequisites:
    1. No prerequisites for memory cache demos
    2. Redis running at localhost:6379 (optional, for Redis demo)
       docker run -d -p 6379:6379 redis:latest
    """

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Example interrupted by user")

