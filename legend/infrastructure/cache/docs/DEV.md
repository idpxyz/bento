# 缓存模块开发指南

## 1. 概述

缓存模块提供了一个简单高效的缓存实现，支持内存和Redis后端，以及多种缓存淘汰策略。

### 1.1 主要特性

- 支持内存和Redis缓存后端
- 支持多种缓存淘汰策略（LRU、LFU、自适应）
- 异步接口设计
- 内置统计功能
- 类型提示完整

## 2. 快速开始

### 2.1 基本使用

```python
from xyz.infrastructure.cache import CacheManager, CacheConfig

# 创建缓存管理器
config = CacheConfig(
    backend="memory",
    max_size=1000,
    policy="lru"
)
cache = CacheManager(config)
await cache.initialize()

# 基本操作
await cache.set("key", "value", expire=3600)  # 设置值，过期时间为1小时
value = await cache.get("key")  # 获取值
await cache.delete("key")  # 删除值

# 便捷的get_or_set操作
value = await cache.get_or_set(
    "key",
    getter_func=lambda: compute_value(),
    expire=3600
)
```

### 2.2 Redis后端配置

```python
config = CacheConfig(
    backend="redis",
    redis_url="redis://localhost:6379/0",
    policy="lru"
)
```

## 3. 缓存策略

### 3.1 可用策略

- **LRU (Least Recently Used)**
  - 最近最少使用策略
  - 适合一般场景
  - 默认策略

- **LFU (Least Frequently Used)**
  - 最少使用频率策略
  - 适合有明显访问频率差异的场景

- **Adaptive**
  - 自适应策略
  - 根据访问模式自动在LRU和LFU之间切换
  - 适合访问模式不确定的场景

### 3.2 策略选择建议

- 默认使用LRU策略
- 如果数据访问有明显的频率差异，使用LFU
- 如果不确定访问模式，使用自适应策略

## 4. 配置选项

### 4.1 基础配置

```python
class CacheConfig(BaseModel):
    # 基础配置
    backend: CacheBackend = "memory"     # 缓存后端类型
    prefix: str = "cache:"               # 键前缀
    default_expire: int = 3600           # 默认过期时间(秒)
    
    # 容量配置
    max_size: int = 10000               # 最大条目数
    
    # Redis配置
    redis_url: Optional[str] = None      # Redis连接URL
    
    # 策略配置
    policy: CachePolicy = "lru"          # 缓存淘汰策略
    policy_window_size: int = 1000      # 策略窗口大小，用于自适应策略
    
    # 监控配置
    enable_stats: bool = True            # 是否启用统计
```

### 4.2 配置最佳实践

- 设置合适的`max_size`以控制内存使用
- 根据数据特点设置合理的`default_expire`
- 生产环境建议启用`enable_stats`以监控缓存效果

## 5. 统计信息

### 5.1 可用统计

```python
stats = cache.get_stats()
{
    "hits": int,              # 缓存命中次数
    "misses": int,            # 缓存未命中次数
    "total_operations": int,  # 总操作次数
    "hit_rate": float        # 缓存命中率
}
```

### 5.2 监控建议

- 定期检查hit_rate，建议保持在80%以上
- 观察total_operations判断缓存使用情况
- 如果miss率过高，考虑调整缓存策略或过期时间




## 6. 性能优化

### 6.1 内存缓存优化

- 合理设置max_size，避免过大占用内存
- 设置合适的过期时间，避免长期占用内存
- 使用get_or_set减少重复计算

### 6.2 Redis缓存优化

- 使用连接池管理Redis连接
- 合理设置键前缀，避免键冲突
- 注意序列化数据大小

## 7. 最佳实践

### 7.1 键的命名

- 使用有意义的前缀
- 保持键名简短
- 避免使用特殊字符

### 7.2 过期时间设置

- 根据数据更新频率设置
- 避免过长的过期时间
- 对不同类型的数据使用不同的过期时间

### 7.3 错误处理

- 使用try-except捕获缓存操作异常
- 缓存失败时及时记录日志
- 实现降级策略

## 8. 常见问题

### 8.1 内存使用

Q: 如何控制内存缓存的大小？
A: 通过设置`max_size`参数控制最大条目数。

### 8.2 Redis连接

Q: Redis连接失败如何处理？
A: 系统会自动重试，同时抛出异常供上层处理。

### 8.3 缓存穿透

Q: 如何避免缓存穿透？
A: 使用get_or_set方法，对空值也进行缓存。

## 9. 注意事项

1. 避免缓存过大的对象
2. 注意设置合理的过期时间
3. 在关键业务中做好降级处理
4. 定期监控缓存效果

