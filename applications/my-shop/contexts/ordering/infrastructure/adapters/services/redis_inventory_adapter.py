"""RedisInventoryAdapter - Redis 库存适配器

基于 Redis 的高性能库存管理实现。
符合六边形架构：实现 IInventoryService Port。

特点：
- 高性能（内存操作）
- 原子性（Lua 脚本）
- 支持分布式
- 支持预留过期时间
- 支持并发
"""

from __future__ import annotations

import json
import uuid

try:
    import redis.asyncio as redis
except ImportError:
    import redis  # type: ignore

from contexts.ordering.domain.ports.services.i_inventory_service import (
    IInventoryService,
    InventoryItem,
    ReservationRequest,
    ReservationResult,
)


class RedisInventoryAdapter(IInventoryService):
    """Redis 库存适配器

    实现：IInventoryService (domain/ports/services/i_inventory_service.py)

    特性：
    - 使用 Redis Hash 存储库存信息
    - 使用 Lua 脚本保证原子性
    - 使用 Redis 过期时间管理预留
    - 支持高并发场景

    Redis 数据结构：
    - inventory:{product_id} -> Hash {available, reserved, total}
    - reservation:{reservation_id} -> Hash {order_id, items, expire_at}

    配置示例：
    ```python
    adapter = RedisInventoryAdapter(
        redis_url="redis://localhost:6379/0",
        reservation_ttl=1800,  # 30分钟
    )
    ```
    """

    def __init__(
        self,
        redis_url: str,
        reservation_ttl: int = 1800,  # 预留过期时间（秒），默认30分钟
        inventory_prefix: str = "inventory:",
        reservation_prefix: str = "reservation:",
    ):
        """初始化 Redis 库存适配器

        Args:
            redis_url: Redis 连接URL
            reservation_ttl: 预留过期时间（秒）
            inventory_prefix: 库存键前缀
            reservation_prefix: 预留键前缀
        """
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.reservation_ttl = reservation_ttl
        self.inventory_prefix = inventory_prefix
        self.reservation_prefix = reservation_prefix

    def _inventory_key(self, product_id: str) -> str:
        """获取库存键"""
        return f"{self.inventory_prefix}{product_id}"

    def _reservation_key(self, reservation_id: str) -> str:
        """获取预留键"""
        return f"{self.reservation_prefix}{reservation_id}"

    async def check_availability(self, product_id: str, quantity: int) -> bool:
        """检查库存是否充足

        Args:
            product_id: 产品ID
            quantity: 需要数量

        Returns:
            bool: 库存是否充足
        """
        inventory = await self.get_inventory(product_id)
        is_available = inventory.available_quantity >= quantity

        print(
            f"📦 [RedisInventory] Check: {product_id} - "
            f"Need: {quantity}, Available: {inventory.available_quantity}, "
            f"Result: {'✅ OK' if is_available else '❌ Insufficient'}"
        )

        return is_available

    async def check_availability_batch(self, items: list[tuple[str, int]]) -> dict[str, bool]:
        """批量检查库存"""
        results = {}

        for product_id, quantity in items:
            results[product_id] = await self.check_availability(product_id, quantity)

        return results

    async def get_inventory(self, product_id: str) -> InventoryItem:
        """获取库存信息

        Args:
            product_id: 产品ID

        Returns:
            InventoryItem: 库存信息
        """
        key = self._inventory_key(product_id)

        # 从 Redis Hash 获取库存数据
        data = await self.redis.hgetall(key)

        if not data:
            # 如果不存在，返回零库存
            return InventoryItem(
                product_id=product_id,
                available_quantity=0,
                reserved_quantity=0,
                total_quantity=0,
            )

        return InventoryItem(
            product_id=product_id,
            available_quantity=int(data.get("available", 0)),
            reserved_quantity=int(data.get("reserved", 0)),
            total_quantity=int(data.get("total", 0)),
        )

    async def reserve_inventory(self, request: ReservationRequest) -> ReservationResult:
        """预留库存

        使用 Lua 脚本保证原子性。

        Args:
            request: 预留请求

        Returns:
            ReservationResult: 预留结果
        """
        # 生成预留ID
        reservation_id = f"RSV_{uuid.uuid4().hex[:12].upper()}"

        # Lua 脚本：原子性检查和预留库存
        lua_script = """
        local failed_items = {}
        local items = cjson.decode(ARGV[1])

        -- 检查所有商品库存
        for i, item in ipairs(items) do
            local product_id = item[1]
            local quantity = item[2]
            local key = KEYS[1] .. product_id

            local available = tonumber(redis.call('HGET', key, 'available') or 0)

            if available < quantity then
                table.insert(failed_items, product_id)
            end
        end

        -- 如果有商品库存不足，返回失败
        if #failed_items > 0 then
            return {0, cjson.encode(failed_items)}
        end

        -- 预留库存
        for i, item in ipairs(items) do
            local product_id = item[1]
            local quantity = item[2]
            local key = KEYS[1] .. product_id

            redis.call('HINCRBY', key, 'available', -quantity)
            redis.call('HINCRBY', key, 'reserved', quantity)
        end

        return {1, ""}
        """

        try:
            # 执行 Lua 脚本
            result = await self.redis.eval(
                lua_script,
                1,
                self.inventory_prefix,
                json.dumps(request.items),
            )

            success = result[0] == 1
            failed_items = json.loads(result[1]) if result[1] else []

            if not success:
                print(
                    f"⚠️ [RedisInventory] Reservation failed: {reservation_id} - "
                    f"Insufficient stock for: {', '.join(failed_items)}"
                )

                return ReservationResult(
                    reservation_id=reservation_id,
                    success=False,
                    failed_items=failed_items,
                    message=f"Insufficient stock: {', '.join(failed_items)}",
                )

            # 保存预留信息（带过期时间）
            reservation_key = self._reservation_key(reservation_id)
            reservation_data = {
                "order_id": request.order_id,
                "items": json.dumps(request.items),
            }

            await self.redis.hset(reservation_key, mapping=reservation_data)
            await self.redis.expire(reservation_key, self.reservation_ttl)

            print(
                f"✅ [RedisInventory] Reservation successful: {reservation_id} - "
                f"Order: {request.order_id} (TTL: {self.reservation_ttl}s)"
            )

            return ReservationResult(
                reservation_id=reservation_id,
                success=True,
                message="Inventory reserved successfully",
            )

        except Exception as e:
            print(f"❌ [RedisInventory] Reservation error: {str(e)}")
            return ReservationResult(
                reservation_id=reservation_id,
                success=False,
                message=f"Error: {str(e)}",
            )

    async def release_reservation(self, reservation_id: str) -> bool:
        """释放预留库存

        Args:
            reservation_id: 预留ID

        Returns:
            bool: 是否成功释放
        """
        reservation_key = self._reservation_key(reservation_id)

        # 获取预留信息
        data = await self.redis.hgetall(reservation_key)

        if not data:
            print(
                f"⚠️ [RedisInventory] Release failed: "
                f"Reservation {reservation_id} not found or expired"
            )
            return False

        # 解析预留的商品
        items = json.loads(data["items"])

        # Lua 脚本：原子性释放库存
        lua_script = """
        local items = cjson.decode(ARGV[1])

        for i, item in ipairs(items) do
            local product_id = item[1]
            local quantity = item[2]
            local key = KEYS[1] .. product_id

            redis.call('HINCRBY', key, 'available', quantity)
            redis.call('HINCRBY', key, 'reserved', -quantity)
        end

        return 1
        """

        try:
            await self.redis.eval(
                lua_script,
                1,
                self.inventory_prefix,
                json.dumps(items),
            )

            # 删除预留记录
            await self.redis.delete(reservation_key)

            print(f"♻️ [RedisInventory] Reservation released: {reservation_id}")

            return True

        except Exception as e:
            print(f"❌ [RedisInventory] Release error: {str(e)}")
            return False

    async def deduct_inventory(self, product_id: str, quantity: int) -> bool:
        """扣减库存

        使用 Lua 脚本保证原子性。
        优先从预留库存扣减，不足时从可用库存扣减。

        Args:
            product_id: 产品ID
            quantity: 扣减数量

        Returns:
            bool: 是否成功扣减
        """
        # Lua 脚本：原子性扣减库存
        lua_script = """
        local key = KEYS[1]
        local quantity = tonumber(ARGV[1])

        local available = tonumber(redis.call('HGET', key, 'available') or 0)
        local reserved = tonumber(redis.call('HGET', key, 'reserved') or 0)
        local total = tonumber(redis.call('HGET', key, 'total') or 0)

        -- 检查总库存是否充足
        if (available + reserved) < quantity then
            return {0, available + reserved}
        end

        -- 优先从预留库存扣减
        local reserved_deduct = math.min(quantity, reserved)
        local available_deduct = quantity - reserved_deduct

        -- 更新库存
        redis.call('HINCRBY', key, 'available', -available_deduct)
        redis.call('HINCRBY', key, 'reserved', -reserved_deduct)
        redis.call('HINCRBY', key, 'total', -quantity)

        return {1, total - quantity}
        """

        key = self._inventory_key(product_id)

        try:
            result = await self.redis.eval(lua_script, 1, key, quantity)

            success = result[0] == 1
            remaining = result[1]

            if not success:
                print(
                    f"❌ [RedisInventory] Deduct failed: {product_id} - "
                    f"Insufficient (need: {quantity}, available: {remaining})"
                )
                return False

            print(
                f"➖ [RedisInventory] Inventory deducted: {product_id} - "
                f"Quantity: {quantity}, Remaining: {remaining}"
            )

            return True

        except Exception as e:
            print(f"❌ [RedisInventory] Deduct error: {str(e)}")
            return False

    async def restore_inventory(self, product_id: str, quantity: int) -> bool:
        """恢复库存

        Args:
            product_id: 产品ID
            quantity: 恢复数量

        Returns:
            bool: 是否成功恢复
        """
        key = self._inventory_key(product_id)

        try:
            # 原子性增加库存
            pipeline = self.redis.pipeline()
            pipeline.hincrby(key, "available", quantity)
            pipeline.hincrby(key, "total", quantity)
            pipeline.hget(key, "total")
            results = await pipeline.execute()

            new_total = int(results[2])

            print(
                f"➕ [RedisInventory] Inventory restored: {product_id} - "
                f"Quantity: {quantity}, Total: {new_total}"
            )

            return True

        except Exception as e:
            print(f"❌ [RedisInventory] Restore error: {str(e)}")
            return False

    # ============ 管理方法 ============

    async def set_inventory(self, product_id: str, quantity: int):
        """设置库存（管理方法）

        Args:
            product_id: 产品ID
            quantity: 库存数量
        """
        key = self._inventory_key(product_id)

        await self.redis.hset(
            key,
            mapping={
                "available": quantity,
                "reserved": 0,
                "total": quantity,
            },
        )

        print(f"📝 [RedisInventory] Inventory set: {product_id} = {quantity}")

    async def sync_from_database(self, inventories: dict[str, int]):
        """从数据库同步库存到 Redis（管理方法）

        Args:
            inventories: {product_id: quantity, ...}
        """
        pipeline = self.redis.pipeline()

        for product_id, quantity in inventories.items():
            key = self._inventory_key(product_id)
            pipeline.hset(
                key,
                mapping={
                    "available": quantity,
                    "reserved": 0,
                    "total": quantity,
                },
            )

        await pipeline.execute()

        print(f"🔄 [RedisInventory] Synced {len(inventories)} items from database")

    async def clear_all(self):
        """清空所有库存数据（仅用于测试）"""
        # 删除所有库存键
        keys = await self.redis.keys(f"{self.inventory_prefix}*")
        if keys:
            await self.redis.delete(*keys)

        # 删除所有预留键
        reservation_keys = await self.redis.keys(f"{self.reservation_prefix}*")
        if reservation_keys:
            await self.redis.delete(*reservation_keys)

        print("🧹 [RedisInventory] All data cleared")

    async def close(self):
        """关闭 Redis 连接"""
        await self.redis.close()
