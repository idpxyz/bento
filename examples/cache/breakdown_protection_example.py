"""Cache Breakdown Protection and Monitoring Example.

This example demonstrates:
1. Cache statistics and monitoring
2. Cache breakdown protection (防击穿)
3. Performance comparison with/without protection
"""

import asyncio
import logging
import time
from typing import Any

from adapters.cache import create_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


# ==================== Simulated Database ====================


class Database:
    """Simulated slow database."""

    def __init__(self) -> None:
        self.query_count = 0

    async def query_user(self, user_id: str) -> dict[str, Any]:
        """Simulate slow database query.

        Args:
            user_id: User ID to fetch

        Returns:
            User data
        """
        self.query_count += 1
        logger.info(f"🔍 DATABASE QUERY #{self.query_count} for user:{user_id}")

        # Simulate slow query (2 seconds)
        await asyncio.sleep(2)

        return {
            "id": user_id,
            "name": f"User {user_id}",
            "email": f"user{user_id}@example.com",
        }


# ==================== Demo Functions ====================


async def demo_without_protection() -> None:
    """Demonstrate cache without breakdown protection.

    Cache breakdown occurs: multiple concurrent requests hit database.
    """
    logger.info("\n" + "=" * 80)
    logger.info("Demo 1: WITHOUT Breakdown Protection (缓存击穿)")
    logger.info("=" * 80)

    # Create cache WITHOUT breakdown protection
    cache = await create_cache(backend="memory", prefix="no_protect:")
    cache.config.enable_breakdown_protection = False

    db = Database()

    async def get_user(user_id: str) -> dict[str, Any]:
        """Get user with basic caching (NO protection)."""
        cached = await cache.get(f"user:{user_id}")
        if cached:
            logger.info(f"✅ Cache hit: user:{user_id}")
            return cached

        logger.info(f"❌ Cache miss: user:{user_id}")
        user = await db.query_user(user_id)
        await cache.set(f"user:{user_id}", user, ttl=60)
        return user

    logger.info("\n📋 Simulating 10 concurrent requests for same user...")
    start_time = time.time()

    # 10 concurrent requests for same user
    tasks = [get_user("123") for _ in range(10)]
    await asyncio.gather(*tasks)

    duration = time.time() - start_time

    logger.info(f"\n📊 Results:")
    logger.info(f"   Total time: {duration:.2f}s")
    logger.info(f"   Database queries: {db.query_count}")
    logger.info(f"   ❌ Cache breakdown occurred! All 10 requests hit database!")

    await cache.close()


async def demo_with_protection() -> None:
    """Demonstrate cache WITH breakdown protection.

    Only ONE request hits database, others wait for result.
    """
    logger.info("\n" + "=" * 80)
    logger.info("Demo 2: WITH Breakdown Protection (防击穿)")
    logger.info("=" * 80)

    # Create cache WITH breakdown protection (default)
    cache = await create_cache(backend="memory", prefix="protected:")

    db = Database()

    async def get_user_protected(user_id: str) -> dict[str, Any]:
        """Get user with breakdown protection."""
        return await cache.get_or_set(
            f"user:{user_id}", lambda: db.query_user(user_id), ttl=60
        )

    logger.info("\n📋 Simulating 10 concurrent requests for same user...")
    start_time = time.time()

    # 10 concurrent requests for same user
    tasks = [get_user_protected("456") for _ in range(10)]
    await asyncio.gather(*tasks)

    duration = time.time() - start_time

    logger.info(f"\n📊 Results:")
    logger.info(f"   Total time: {duration:.2f}s")
    logger.info(f"   Database queries: {db.query_count}")
    logger.info(f"   ✅ Protected! Only 1 database query despite 10 requests!")

    await cache.close()


async def demo_cache_stats() -> None:
    """Demonstrate cache statistics monitoring."""
    logger.info("\n" + "=" * 80)
    logger.info("Demo 3: Cache Statistics and Monitoring")
    logger.info("=" * 80)

    # Create cache with stats enabled (default)
    cache = await create_cache(backend="memory", prefix="stats:", ttl=60)

    logger.info("\n📋 Performing cache operations...")

    # Perform operations
    await cache.set("user:1", {"name": "Alice"})
    await cache.set("user:2", {"name": "Bob"})
    await cache.set("user:3", {"name": "Charlie"})

    # Cache hits
    for _ in range(10):
        await cache.get("user:1")
        await cache.get("user:2")

    # Cache misses
    for _ in range(5):
        await cache.get("user:999")  # Non-existent

    logger.info("\n📊 Cache Statistics:")
    stats = cache.get_stats()
    if stats:
        logger.info(f"   Hits: {stats['hits']}")
        logger.info(f"   Misses: {stats['misses']}")
        logger.info(f"   Hit Rate: {stats['hit_rate']:.2%}")
        logger.info(f"   Total Operations: {stats['total_operations']}")
        logger.info(f"   Average Get Time: {stats['avg_get_time']:.6f}s")
        logger.info(f"   Average Set Time: {stats['avg_set_time']:.6f}s")

    await cache.close()


async def demo_breakdown_simulation() -> None:
    """Realistic simulation: what happens when cache expires."""
    logger.info("\n" + "=" * 80)
    logger.info("Demo 4: Cache Expiration Breakdown Simulation")
    logger.info("=" * 80)

    cache = await create_cache(backend="memory", prefix="sim:")
    db = Database()

    # Pre-populate cache
    user_data = await db.query_user("789")
    await cache.set("user:789", user_data, ttl=2)  # 2 seconds TTL

    logger.info("✅ Cache populated, waiting for expiration...")
    await asyncio.sleep(3)  # Wait for cache to expire

    logger.info("\n⚠️  Cache expired! Simulating 20 concurrent requests...")
    
    db.query_count = 0  # Reset counter
    start_time = time.time()

    # 20 concurrent requests right after expiration
    tasks = [
        cache.get_or_set("user:789", lambda: db.query_user("789"), ttl=60)
        for _ in range(20)
    ]
    await asyncio.gather(*tasks)

    duration = time.time() - start_time

    logger.info(f"\n📊 Results:")
    logger.info(f"   Total time: {duration:.2f}s")
    logger.info(f"   Database queries: {db.query_count}")
    logger.info(f"   ✅ Protection worked! Only {db.query_count} query for 20 requests!")

    await cache.close()


async def main() -> None:
    """Run all demos."""

    logger.info("=" * 80)
    logger.info("Cache Breakdown Protection and Monitoring - Complete Example")
    logger.info("=" * 80)

    # Run demos
    await demo_without_protection()
    await demo_with_protection()
    await demo_cache_stats()
    await demo_breakdown_simulation()

    logger.info("\n" + "=" * 80)
    logger.info("✅ All demos completed!")
    logger.info("=" * 80)

    logger.info("\n💡 Key Takeaways:")
    logger.info("   1. Cache breakdown (击穿) can cause database overload")
    logger.info("   2. Use get_or_set() to prevent breakdown with mutex locks")
    logger.info("   3. Monitor cache performance with get_stats()")
    logger.info("   4. High hit rate = good cache effectiveness")


if __name__ == "__main__":
    """Run the example."""

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Example interrupted by user")

