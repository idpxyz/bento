# 缓存序列化架构设计

## 问题背景

### 原始问题

应用层在使用缓存预热时遇到序列化错误：

```
TypeError: Object of type Product is not JSON serializable
```

**原因**：
- 缓存尝试直接序列化聚合根对象（Product, Category）
- 聚合根是复杂的领域对象，包含方法、事件等，不能直接 JSON 序列化

### 临时解决方案（不推荐）

每个应用手动转换：

```python
# ❌ 每个 Warmup Service 都要写这样的代码
async def load_data(self, key: str):
    product = await self._product_repo.get(id)

    # 手动转换为字典（重复代码）
    return {
        "id": str(product.id),
        "name": product.name,
        "price": float(product.price),
        ...
    }
```

**问题**：
- ❌ 重复代码（每个 Strategy 都要写）
- ❌ 容易出错（忘记转换某个字段）
- ❌ 不一致（不同开发者可能用不同方式）
- ❌ 维护困难（字段变化时要改多处）

## ✅ Framework 层面的解决方案

### 设计原则

**"Framework 提供机制，应用提供策略"**

- Framework 负责：自动检测和序列化聚合根
- 应用负责：定义哪些字段需要缓存（可选）

### 架构设计

```
┌─────────────────────────────────────────────┐
│ Application Layer                           │
│                                             │
│ Warmup Service                              │
│   └── load_data() -> AggregateRoot         │ ← 直接返回聚合根
│                      ↓                      │
└──────────────────────┼──────────────────────┘
                       │
                       ↓ 自动序列化
┌──────────────────────┼──────────────────────┐
│ Infrastructure Layer │                      │
│                      ↓                      │
│ Cache._serialize()                          │
│   └── _make_serializable()                 │
│         └── 检测 to_cache_dict()            │ ← Framework 自动处理
│                      ↓                      │
└──────────────────────┼──────────────────────┘
                       │
                       ↓ 调用
┌──────────────────────┼──────────────────────┐
│ Domain Layer         │                      │
│                      ↓                      │
│ AggregateRoot.to_cache_dict()               │
│   └── 默认实现：自动转换所有公开属性        │ ← 提供默认实现
│   └── 可覆盖：自定义序列化逻辑              │ ← 允许自定义
│                                             │
└─────────────────────────────────────────────┘
```

## 实现细节

### 1. AggregateRoot 添加 to_cache_dict() 方法

```python
# bento/domain/aggregate.py

class AggregateRoot(Entity):
    """聚合根基类."""

    def to_cache_dict(self) -> dict[str, Any]:
        """转换为可缓存的字典.

        默认实现：自动转换所有公开属性
        - 跳过私有属性（_开头）
        - 自动转换特殊类型（ID, Decimal, datetime, Enum）
        - 递归处理嵌套对象

        子类可以覆盖此方法以自定义序列化逻辑。
        """
        result: dict[str, Any] = {}

        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue  # 跳过私有属性

            result[key] = self._serialize_value(value)

        return result

    def _serialize_value(self, value: Any) -> Any:
        """序列化单个值."""
        # EntityId → str
        if isinstance(value, EntityId):
            return str(value)

        # Decimal → float
        if isinstance(value, Decimal):
            return float(value)

        # datetime → ISO string
        if isinstance(value, (datetime, date)):
            return value.isoformat()

        # Enum → value
        if isinstance(value, Enum):
            return value.value

        # List - 递归
        if isinstance(value, list):
            return [
                item.to_cache_dict() if hasattr(item, 'to_cache_dict')
                else self._serialize_value(item)
                for item in value
            ]

        # Dict - 递归
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}

        # 嵌套对象
        if hasattr(value, 'to_cache_dict'):
            return value.to_cache_dict()

        # 原始类型
        return value
```

### 2. Cache 自动检测并序列化

```python
# bento/adapters/cache/memory.py

class InMemoryCache:
    def _serialize(self, value: Any) -> bytes:
        """序列化值."""
        try:
            if self.config.serializer == SerializerType.JSON:
                # 自动序列化聚合根
                serializable_value = self._make_serializable(value)
                return json.dumps(serializable_value).encode("utf-8")
            else:  # PICKLE
                return pickle.dumps(value)
        except Exception as e:
            raise ValueError(f"Failed to serialize value: {e}") from e

    def _make_serializable(self, value: Any) -> Any:
        """转换为可序列化格式."""
        # 检测 to_cache_dict 方法
        if hasattr(value, 'to_cache_dict') and callable(getattr(value, 'to_cache_dict')):
            return value.to_cache_dict()

        # 列表
        if isinstance(value, list):
            return [self._make_serializable(item) for item in value]

        # 字典
        if isinstance(value, dict):
            return {k: self._make_serializable(v) for k, v in value.items()}

        # 原始类型
        return value
```

### 3. 应用层代码简化

```python
# 应用层：直接返回聚合根
class HotProductsWarmupStrategy:
    async def load_data(self, key: str):
        product = await self._product_repo.get(ID(product_id_str))

        # 直接返回，Framework 自动序列化！
        return product
```

## 使用方式

### 方式 1：使用默认序列化（推荐）

大多数情况下，默认实现就够用了：

```python
class Product(AggregateRoot):
    """商品聚合根."""

    def __init__(self, id: ID, name: str, price: Decimal):
        super().__init__(id)
        self.name = name
        self.price = price
        self.stock = 0
        self.category_id = None

    # 不需要实现 to_cache_dict()，使用默认实现
```

**缓存内容**（自动生成）：
```json
{
    "id": "prod-123",
    "name": "iPhone 15",
    "price": 999.99,
    "stock": 100,
    "category_id": "cat-456"
}
```

### 方式 2：自定义序列化（可选）

如果需要控制缓存内容：

```python
class Product(AggregateRoot):
    """商品聚合根."""

    def to_cache_dict(self) -> dict:
        """自定义缓存序列化.

        只缓存必要的字段，排除大字段。
        """
        return {
            "id": str(self.id),
            "name": self.name,
            "price": float(self.price),
            "stock": self.stock,
            # 不缓存 description（太大）
            # 不缓存 images（太大）
        }
```

### 方式 3：包含计算属性

```python
class Order(AggregateRoot):
    """订单聚合根."""

    def to_cache_dict(self) -> dict:
        """包含计算属性."""
        return {
            "id": str(self.id),
            "customer_id": str(self.customer_id),
            "items": [item.to_cache_dict() for item in self.items],
            "total": float(self.total),  # 计算属性
            "status": self.status.value,
        }
```

## 自动类型转换

Framework 自动处理以下类型转换：

| 原始类型 | 转换后 | 示例 |
|---------|--------|------|
| `EntityId` (ID, OrderId, etc.) | `str` | `ID("123")` → `"123"` |
| `Decimal` | `float` | `Decimal("99.99")` → `99.99` |
| `datetime` | `str` (ISO) | `datetime(...)` → `"2024-11-24T20:00:00"` |
| `date` | `str` (ISO) | `date(...)` → `"2024-11-24"` |
| `Enum` | 枚举值 | `Status.ACTIVE` → `"active"` |
| `list[AR]` | `list[dict]` | 递归转换 |
| `dict` | `dict` | 递归转换值 |
| 嵌套 AR/Entity | `dict` | 调用其 `to_cache_dict()` |

## 优势

### 1. 应用层代码简洁

```python
# ✅ 之前：需要手动转换（20+ 行）
async def load_data(self, key: str):
    product = await self._product_repo.get(id)
    return {
        "id": str(product.id),
        "name": product.name,
        ...  # 重复代码
    }

# ✅ 现在：直接返回（3 行）
async def load_data(self, key: str):
    product = await self._product_repo.get(id)
    return product  # Framework 自动处理
```

### 2. 统一的序列化方式

- 所有聚合根使用相同的序列化机制
- 避免不一致的手动转换
- 易于维护和调试

### 3. 类型安全

- 自动转换特殊类型（ID, Decimal, datetime, Enum）
- 避免序列化错误
- 类型转换逻辑集中管理

### 4. 灵活性

- 默认实现满足大多数场景
- 可以覆盖 `to_cache_dict()` 自定义
- 支持嵌套对象和列表

### 5. 性能优化

- 可以选择性缓存字段（排除大字段）
- 减少缓存大小
- 提高缓存命中率

## 最佳实践

### 1. 优先使用默认实现

```python
# ✅ 推荐：使用默认实现
class Category(AggregateRoot):
    # 不需要实现 to_cache_dict()
    pass
```

### 2. 排除不必要的字段

```python
# ✅ 推荐：只缓存必要字段
class Product(AggregateRoot):
    def to_cache_dict(self) -> dict:
        return {
            "id": str(self.id),
            "name": self.name,
            "price": float(self.price),
            # 不缓存 description（太大）
        }
```

### 3. 处理嵌套对象

```python
# ✅ 推荐：递归处理嵌套对象
class Order(AggregateRoot):
    def to_cache_dict(self) -> dict:
        return {
            "id": str(self.id),
            "items": [item.to_cache_dict() for item in self.items],
            # 自动调用 OrderItem.to_cache_dict()
        }
```

### 4. 包含计算属性

```python
# ✅ 推荐：缓存计算结果
class Order(AggregateRoot):
    def to_cache_dict(self) -> dict:
        return {
            "id": str(self.id),
            "total": float(self.calculate_total()),  # 缓存计算结果
        }
```

## 测试

### 单元测试

```python
def test_aggregate_to_cache_dict():
    """测试聚合根序列化."""
    product = Product(
        id=ID("prod-123"),
        name="iPhone 15",
        price=Decimal("999.99"),
    )

    cache_dict = product.to_cache_dict()

    assert cache_dict["id"] == "prod-123"
    assert cache_dict["name"] == "iPhone 15"
    assert cache_dict["price"] == 999.99  # Decimal → float
    assert isinstance(cache_dict["price"], float)
```

### 集成测试

```python
async def test_cache_serialization():
    """测试缓存序列化."""
    cache = InMemoryCache(CacheConfig())

    product = Product(
        id=ID("prod-123"),
        name="iPhone 15",
        price=Decimal("999.99"),
    )

    # 缓存聚合根
    await cache.set("product:123", product)

    # 读取缓存
    cached = await cache.get("product:123")

    # 验证序列化结果
    assert cached["id"] == "prod-123"
    assert cached["price"] == 999.99
```

## 架构影响

### 修改的文件

1. ✅ `bento/domain/aggregate.py` - 添加 `to_cache_dict()` 方法
2. ✅ `bento/adapters/cache/memory.py` - 添加 `_make_serializable()` 方法
3. ✅ 应用层 Warmup Service - 简化代码

### 向后兼容性

- ✅ 完全向后兼容
- ✅ 不影响现有代码
- ✅ 可选功能（不使用缓存的代码不受影响）

### 性能影响

- ✅ 序列化性能：O(n)，n 为字段数量
- ✅ 内存占用：只缓存必要字段
- ✅ 缓存命中率：提高（因为可以排除大字段）

## 总结

### 设计原则

1. **Framework 提供机制** - 自动检测和序列化
2. **应用提供策略** - 可选的自定义序列化
3. **默认实现优先** - 满足 80% 的场景
4. **灵活可扩展** - 支持自定义

### 优势

- ✅ 应用层代码简洁（直接返回聚合根）
- ✅ 统一的序列化方式（避免不一致）
- ✅ 类型安全（自动转换特殊类型）
- ✅ 灵活性（可自定义序列化逻辑）
- ✅ 性能优化（可选择性缓存字段）

### 影响范围

- ✅ Framework 层：2 个文件修改
- ✅ 应用层：代码简化
- ✅ 向后兼容：不影响现有代码

**这是一个优雅的 Framework 层面解决方案！** 🎉
