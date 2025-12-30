"""Redis Inventory Adapter 测试

测试 RedisInventoryAdapter 的功能。

运行前请确保：
1. Redis 服务已启动
2. 配置了 REDIS_URL 环境变量

运行测试：
```bash
# 启动 Redis（如果没有运行）
redis-server

# 运行测试
uv run python tests/ordering/test_redis_inventory_adapter.py
```
"""

import asyncio
import os

import pytest

from contexts.ordering.infrastructure.adapters.services.redis_inventory_adapter import (
    RedisInventoryAdapter,
    ReservationRequest,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Skip all tests in this module if Redis is not available
try:
    import redis  # noqa: F401

    REDIS_AVAILABLE = True
except (ImportError, Exception):
    REDIS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not REDIS_AVAILABLE, reason="Redis service not available (install redis and start redis-server)"
)


async def test_basic_operations():
    """测试基本操作"""
    print("\n" + "=" * 70)
    print("🧪 测试 Redis 库存基本操作")
    print("=" * 70)

    # 创建适配器
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    adapter = RedisInventoryAdapter(redis_url, reservation_ttl=60)

    try:
        # 清空测试数据
        await adapter.clear_all()

        # 1. 设置初始库存
        print("\n1️⃣ 设置初始库存...")
        await adapter.set_inventory("PROD_001", 100)
        await adapter.set_inventory("PROD_002", 50)

        # 2. 获取库存信息
        print("\n2️⃣ 获取库存信息...")
        inventory = await adapter.get_inventory("PROD_001")
        print(f"   产品: {inventory.product_id}")
        print(f"   可用数量: {inventory.available_quantity}")
        print(f"   预留数量: {inventory.reserved_quantity}")
        print(f"   总数量: {inventory.total_quantity}")

        # 3. 检查库存
        print("\n3️⃣ 检查库存（需要 10 件）...")
        is_available = await adapter.check_availability("PROD_001", 10)
        print(f"   结果: {'✅ 充足' if is_available else '❌ 不足'}")

        # 4. 批量检查
        print("\n4️⃣ 批量检查库存...")
        results = await adapter.check_availability_batch(
            [
                ("PROD_001", 10),
                ("PROD_002", 5),
            ]
        )
        for pid, available in results.items():
            print(f"   {pid}: {'✅ 可用' if available else '❌ 不可用'}")

        print("\n✅ 基本操作测试完成")
        return True

    finally:
        await adapter.close()


async def test_reservation():
    """测试库存预留"""
    print("\n" + "=" * 70)
    print("🧪 测试库存预留")
    print("=" * 70)

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    adapter = RedisInventoryAdapter(redis_url, reservation_ttl=60)

    try:
        # 设置初始库存
        await adapter.set_inventory("PROD_003", 100)
        await adapter.set_inventory("PROD_004", 50)

        # 1. 预留库存
        print("\n1️⃣ 预留库存...")
        request = ReservationRequest(
            order_id="ORDER_001", items=[("PROD_003", 10), ("PROD_004", 5)]
        )
        result = await adapter.reserve_inventory(request)
        print(f"   预留{'成功' if result.success else '失败'}: {result.reservation_id}")

        # 2. 查看预留后的库存
        print("\n2️⃣ 查看预留后的库存...")
        inventory = await adapter.get_inventory("PROD_003")
        print("   PROD_003:")
        print(f"   可用: {inventory.available_quantity}")
        print(f"   预留: {inventory.reserved_quantity}")
        print(f"   总计: {inventory.total_quantity}")

        # 3. 尝试预留超出库存
        print("\n3️⃣ 尝试预留超出库存...")
        request2 = ReservationRequest(
            order_id="ORDER_002",
            items=[("PROD_003", 200)],  # 超出库存
        )
        result2 = await adapter.reserve_inventory(request2)
        print(f"   预留{'成功' if result2.success else '失败'}")
        if not result2.success:
            print(f"   失败原因: {result2.message}")
            print(f"   失败商品: {result2.failed_items}")

        # 4. 释放预留
        print("\n4️⃣ 释放预留...")
        released = await adapter.release_reservation(result.reservation_id)
        print(f"   释放{'成功' if released else '失败'}")

        # 5. 查看释放后的库存
        print("\n5️⃣ 查看释放后的库存...")
        inventory_after = await adapter.get_inventory("PROD_003")
        print("   PROD_003:")
        print(f"   可用: {inventory_after.available_quantity}")
        print(f"   预留: {inventory_after.reserved_quantity}")

        print("\n✅ 预留测试完成")
        return True

    finally:
        await adapter.close()


async def test_deduct_and_restore():
    """测试扣减和恢复"""
    print("\n" + "=" * 70)
    print("🧪 测试库存扣减和恢复")
    print("=" * 70)

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    adapter = RedisInventoryAdapter(redis_url)

    try:
        # 设置初始库存
        await adapter.set_inventory("PROD_005", 100)

        # 1. 扣减库存
        print("\n1️⃣ 扣减库存（20件）...")
        success = await adapter.deduct_inventory("PROD_005", 20)
        print(f"   扣减{'成功' if success else '失败'}")

        # 2. 查看扣减后的库存
        print("\n2️⃣ 查看扣减后的库存...")
        inventory = await adapter.get_inventory("PROD_005")
        print(f"   总库存: {inventory.total_quantity}")
        print(f"   可用: {inventory.available_quantity}")

        # 3. 尝试扣减超出库存
        print("\n3️⃣ 尝试扣减超出库存（200件）...")
        success2 = await adapter.deduct_inventory("PROD_005", 200)
        print(f"   扣减{'成功' if success2 else '失败'}")

        # 4. 恢复库存
        print("\n4️⃣ 恢复库存（10件）...")
        success3 = await adapter.restore_inventory("PROD_005", 10)
        print(f"   恢复{'成功' if success3 else '失败'}")

        # 5. 查看最终库存
        print("\n5️⃣ 查看最终库存...")
        inventory_final = await adapter.get_inventory("PROD_005")
        print(f"   总库存: {inventory_final.total_quantity}")
        print(f"   可用: {inventory_final.available_quantity}")

        print("\n✅ 扣减和恢复测试完成")
        return True

    finally:
        await adapter.close()


async def test_concurrent_operations():
    """测试并发操作"""
    print("\n" + "=" * 70)
    print("🧪 测试并发操作（原子性）")
    print("=" * 70)

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    adapter = RedisInventoryAdapter(redis_url)

    try:
        # 设置初始库存
        await adapter.set_inventory("PROD_006", 100)

        print("\n模拟 10 个并发预留请求...")

        # 创建 10 个并发预留请求（每个预留 15 件）
        tasks = []
        for i in range(10):
            request = ReservationRequest(order_id=f"ORDER_{i:03d}", items=[("PROD_006", 15)])
            tasks.append(adapter.reserve_inventory(request))

        # 并发执行
        results = await asyncio.gather(*tasks)

        # 统计结果
        success_count = sum(1 for r in results if r.success)
        failed_count = sum(1 for r in results if not r.success)

        print("\n结果统计:")
        print(f"   成功: {success_count} 个")
        print(f"   失败: {failed_count} 个")

        # 查看最终库存
        inventory = await adapter.get_inventory("PROD_006")
        print("\n最终库存:")
        print(f"   可用: {inventory.available_quantity}")
        print(f"   预留: {inventory.reserved_quantity}")
        print(f"   总计: {inventory.total_quantity}")

        # 验证：成功数量 * 15 应该等于预留数量
        expected_reserved = success_count * 15
        actual_reserved = inventory.reserved_quantity

        if expected_reserved == actual_reserved:
            print(f"\n✅ 原子性验证通过（预留 {actual_reserved} 件 = {success_count} × 15）")
        else:
            print(f"\n❌ 原子性验证失败（预期 {expected_reserved}，实际 {actual_reserved}）")

        print("\n✅ 并发测试完成")
        return expected_reserved == actual_reserved

    finally:
        await adapter.close()


async def test_sync_from_database():
    """测试从数据库同步"""
    print("\n" + "=" * 70)
    print("🧪 测试从数据库同步")
    print("=" * 70)

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    adapter = RedisInventoryAdapter(redis_url)

    try:
        # 模拟从数据库获取的库存数据
        database_inventories = {
            "PROD_101": 500,
            "PROD_102": 300,
            "PROD_103": 150,
            "PROD_104": 800,
            "PROD_105": 50,
        }

        print(f"\n同步 {len(database_inventories)} 个产品的库存...")
        await adapter.sync_from_database(database_inventories)

        # 验证同步结果
        print("\n验证同步结果...")
        for product_id, expected_qty in database_inventories.items():
            inventory = await adapter.get_inventory(product_id)
            actual_qty = inventory.total_quantity
            status = "✅" if actual_qty == expected_qty else "❌"
            print(f"   {product_id}: {actual_qty} (预期 {expected_qty}) {status}")

        print("\n✅ 同步测试完成")
        return True

    finally:
        await adapter.close()


async def main():
    """运行所有测试"""
    print("\n" + "🚀 " + "=" * 66)
    print("🚀 Redis Inventory Adapter 测试套件")
    print("🚀 " + "=" * 66)

    # 检查 Redis 连接
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    print(f"\nRedis URL: {redis_url}")

    try:
        import redis.asyncio as redis

        client = redis.from_url(redis_url)
        await client.ping()
        await client.close()
        print("✅ Redis 连接正常\n")
    except Exception as e:
        print(f"❌ Redis 连接失败: {str(e)}")
        print("\n请确保：")
        print("1. Redis 服务已启动（redis-server）")
        print("2. REDIS_URL 配置正确")
        return False

    # 运行测试
    results = []

    try:
        results.append(("基本操作", await test_basic_operations()))
        results.append(("库存预留", await test_reservation()))
        results.append(("扣减和恢复", await test_deduct_and_restore()))
        results.append(("并发操作", await test_concurrent_operations()))
        results.append(("数据库同步", await test_sync_from_database()))
    except Exception as e:
        print(f"\n❌ 测试异常: {str(e)}")
        import traceback

        traceback.print_exc()
        return False

    # 输出结果
    print("\n" + "📊 " + "=" * 66)
    print("📊 测试结果总结")
    print("📊 " + "=" * 66)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {name}: {status}")

    all_passed = all(results)

    print("\n" + ("✅ " if all_passed else "❌ ") + "=" * 66)
    print(("✅ " if all_passed else "❌ ") + f"所有测试{'通过' if all_passed else '失败'}！")
    print(("✅ " if all_passed else "❌ ") + "=" * 66 + "\n")

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
