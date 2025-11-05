# 数据库基础设施使用指南

**版本**: 1.0  
**最后更新**: 2025-11-05

---

## 📖 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [配置管理](#配置管理)
4. [会话管理](#会话管理)
5. [生命周期管理](#生命周期管理)
6. [引擎抽象](#引擎抽象)
7. [弹性处理](#弹性处理)
8. [连接耗尽](#连接耗尽)
9. [最佳实践](#最佳实践)
10. [故障排查](#故障排查)

---

## 快速开始

### 前置条件

选择以下数据库之一：

**SQLite（开发环境）**:
```bash
# 无需安装，Python 内置支持
pip install aiosqlite
```

**PostgreSQL（生产环境）**:
```bash
# 1. 安装 PostgreSQL
docker run -d \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:15

# 2. 安装驱动
pip install asyncpg
```

### 5 分钟示例

```python
from bento.infrastructure.database import (
    DatabaseConfig,
    create_async_engine_from_config,
    create_async_session_factory,
    init_database,
    cleanup_database,
)

# 1. 配置数据库（从环境变量）
config = DatabaseConfig()
# 或手动配置
config = DatabaseConfig(
    url="sqlite+aiosqlite:///app.db",
    pool_size=10,
    echo=False,
)

# 2. 创建引擎和会话工厂
engine = create_async_engine_from_config(config)
session_factory = create_async_session_factory(engine)

# 3. 初始化数据库表
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    pass

await init_database(engine, Base)

# 4. 使用会话
async with session_factory() as session:
    async with session.begin():
        # 执行数据库操作
        result = await session.execute(query)
        data = result.scalars().all()

# 5. 应用关闭时清理
await cleanup_database(engine)
```

---

## 核心概念

### 1. 数据库配置 (DatabaseConfig)

所有数据库参数的集中管理，支持环境变量配置。

**关键配置项**:
- `url`: 数据库连接字符串
- `pool_size`: 连接池基础大小
- `max_overflow`: 最大溢出连接数
- `pool_timeout`: 获取连接超时时间
- `pool_recycle`: 连接回收时间
- `pool_pre_ping`: 连接预检查
- `connect_timeout`: 连接超时
- `command_timeout`: 命令超时
- `echo`: SQL 日志输出

### 2. 引擎抽象 (Engine Abstraction)

为不同数据库类型提供优化配置：

- **PostgreSQLEngine**: 
  - JSONB 列类型支持
  - 连接池 LIFO 优化
  - 服务器参数配置
  
- **SQLiteEngine**:
  - NullPool（无连接池）
  - 线程安全配置
  - JSON 列类型

### 3. 弹性处理 (Resilience)

自动错误分类和智能重试机制：

- **错误分类**: TRANSIENT（可重试）vs PERMANENT（不可重试）
- **智能重试**: 指数退避 + 随机抖动
- **错误识别**: 20+ 瞬态错误模式，10+ 永久错误模式

### 4. 连接耗尽 (Connection Draining)

优雅关闭数据库连接：

- **GRACEFUL**: 等待连接完成
- **IMMEDIATE**: 立即关闭池
- **FORCE**: 强制关闭所有连接

---

## 配置管理

### 环境变量配置（推荐）

```bash
# .env 文件
DB_URL="postgresql+asyncpg://user:pass@localhost/mydb"
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
DB_CONNECT_TIMEOUT=10
DB_COMMAND_TIMEOUT=60
DB_ECHO=false
```

```python
from bento.infrastructure.database import DatabaseConfig, get_database_config

# 自动从环境变量加载
config = get_database_config()

# 或使用默认配置
config = DatabaseConfig()  # 使用 DB_* 环境变量
```

### 代码配置

```python
from bento.infrastructure.database import DatabaseConfig

# SQLite（开发环境）
config = DatabaseConfig(
    url="sqlite+aiosqlite:///app.db",
    echo=True,  # 开启 SQL 日志
)

# PostgreSQL（生产环境）
config = DatabaseConfig(
    url="postgresql+asyncpg://user:pass@localhost/mydb",
    pool_size=20,
    max_overflow=10,
    pool_timeout=30.0,
    pool_recycle=3600,
    pool_pre_ping=True,
    connect_timeout=10.0,
    command_timeout=60.0,
    echo=False,
)
```

### 配置属性

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `url` | str | `sqlite+aiosqlite:///app.db` | 数据库连接 URL |
| `pool_size` | int | 5 | 连接池基础大小 |
| `max_overflow` | int | 10 | 最大溢出连接数 |
| `pool_timeout` | float | 30.0 | 获取连接超时（秒）|
| `pool_recycle` | int | 3600 | 连接回收时间（秒）|
| `pool_pre_ping` | bool | True | 连接预检查 |
| `connect_timeout` | float | 10.0 | 连接超时（秒）|
| `command_timeout` | float | 60.0 | 命令超时（秒）|
| `echo` | bool | False | 输出 SQL 日志 |

### 数据库类型检测

```python
config = DatabaseConfig(url="postgresql+asyncpg://localhost/db")

print(config.database_type)  # "postgresql"
print(config.is_postgres)    # True
print(config.is_sqlite)      # False
print(config.is_mysql)       # False
```

---

## 会话管理

### 创建引擎和会话工厂

```python
from bento.infrastructure.database import (
    create_async_engine_from_config,
    create_async_session_factory,
)

# 创建引擎
engine = create_async_engine_from_config(config)

# 创建会话工厂
session_factory = create_async_session_factory(
    engine,
    expire_on_commit=False,  # 提交后不过期对象
    autoflush=True,          # 自动刷新
)
```

### 使用会话

```python
# 基础用法
async with session_factory() as session:
    async with session.begin():
        # 执行操作
        result = await session.execute(select(User))
        users = result.scalars().all()

# 手动事务管理
async with session_factory() as session:
    # 开始事务
    await session.begin()
    
    try:
        # 执行操作
        user = User(name="Alice")
        session.add(user)
        
        # 提交
        await session.commit()
    except Exception as e:
        # 回滚
        await session.rollback()
        raise
```

### 便捷函数

```python
from bento.infrastructure.database import create_engine_and_session_factory

# 一次性创建引擎和会话工厂
engine, session_factory = create_engine_and_session_factory(config)
```

---

## 生命周期管理

### 初始化数据库

```python
from bento.infrastructure.database import init_database
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# 创建所有表
await init_database(engine, Base)

# 带表检查
await init_database(engine, Base, check_tables=True)
```

### 健康检查

```python
from bento.infrastructure.database import health_check

# 检查数据库连接
is_healthy = await health_check(engine)

if not is_healthy:
    raise RuntimeError("Database is not healthy!")
```

### 获取数据库信息

```python
from bento.infrastructure.database import get_database_info

info = await get_database_info(engine)
print(info)
# {
#     'driver': 'asyncpg',
#     'database_type': 'postgresql',
#     'database_name': 'mydb',
#     'pool_size': 20,
#     'pool_checked_out': 3
# }
```

### 清理数据库

```python
from bento.infrastructure.database import cleanup_database

# 应用关闭时调用
await cleanup_database(engine)
```

### 删除所有表（仅用于测试）

```python
from bento.infrastructure.database import drop_all_tables

# ⚠️ 危险操作！仅用于测试环境
await drop_all_tables(engine, Base)
```

---

## 引擎抽象

### 自动引擎选择

框架会根据数据库 URL 自动选择合适的引擎配置：

```python
from bento.infrastructure.database import create_async_engine_from_config

# PostgreSQL
config = DatabaseConfig(url="postgresql+asyncpg://localhost/db")
engine = create_async_engine_from_config(config)
# 使用 PostgreSQLEngine 优化

# SQLite
config = DatabaseConfig(url="sqlite+aiosqlite:///app.db")
engine = create_async_engine_from_config(config)
# 使用 SQLiteEngine 优化
```

### 手动引擎选择

```python
from bento.infrastructure.database.engines import (
    get_engine_for_config,
    PostgreSQLEngine,
    SQLiteEngine,
)

# 获取引擎实例
db_engine = get_engine_for_config(config)

# 查看引擎信息
print(db_engine.__class__.__name__)  # PostgreSQLEngine
print(db_engine.supports_pool)        # True
print(db_engine.json_column_type)     # "JSONB"

# 获取配置参数
connect_args = db_engine.get_connect_args()
pool_kwargs = db_engine.get_pool_kwargs()
engine_kwargs = db_engine.get_engine_kwargs()
```

### PostgreSQL 优化特性

```python
from bento.infrastructure.database.engines import PostgreSQLEngine

engine = PostgreSQLEngine(config)

# 连接参数
connect_args = engine.get_connect_args()
# {
#     'timeout': 10.0,
#     'command_timeout': 60.0,
#     'server_settings': {
#         'application_name': 'bento_app',
#         'jit': 'off',
#     }
# }

# 池配置（LIFO）
pool_kwargs = engine.get_pool_kwargs()
# {
#     'pool_size': 20,
#     'max_overflow': 10,
#     'pool_timeout': 30.0,
#     'pool_recycle': 3600,
#     'pool_pre_ping': True,
# }

# JSONB 支持
print(engine.json_column_type)  # "JSONB"
```

### SQLite 优化特性

```python
from bento.infrastructure.database.engines import SQLiteEngine

engine = SQLiteEngine(config)

# 连接参数
connect_args = engine.get_connect_args()
# {
#     'check_same_thread': False,
#     'timeout': 10.0,
#     'cached_statements': 100,
# }

# 无连接池
print(engine.supports_pool)  # False

# JSON 支持
print(engine.json_column_type)  # "JSON"
```

---

## 弹性处理

### 错误分类

```python
from bento.infrastructure.database.resilience import (
    DatabaseErrorClassifier,
    ErrorCategory,
    is_database_error_retryable,
)

try:
    await session.execute(query)
except Exception as e:
    # 分类错误
    category = DatabaseErrorClassifier.classify(e)
    
    if category == ErrorCategory.TRANSIENT:
        print("瞬态错误，可以重试")
    elif category == ErrorCategory.PERMANENT:
        print("永久错误，不应重试")
    elif category == ErrorCategory.CONNECTION:
        print("连接错误，需要重新连接")
    
    # 或使用便捷函数
    if is_database_error_retryable(e):
        print("可以重试")
```

### 自动重试

**方式 1：函数包装器**

```python
from bento.infrastructure.database.resilience import retry_on_db_error

async def query_users():
    async with session_factory() as session:
        result = await session.execute(select(User))
        return result.scalars().all()

# 自动重试
users = await retry_on_db_error(query_users)
```

**方式 2：自定义配置**

```python
from bento.infrastructure.database.resilience import (
    retry_on_db_error,
    RetryConfig,
)

# 自定义重试配置
config = RetryConfig(
    max_attempts=5,          # 最多重试 5 次
    base_delay=0.2,          # 初始延迟 0.2 秒
    max_delay=30.0,          # 最大延迟 30 秒
    exponential_base=2.0,    # 指数基数 2
    jitter=True,             # 启用随机抖动
)

users = await retry_on_db_error(query_users, config=config)
```

**方式 3：上下文管理器**

```python
from bento.infrastructure.database.resilience import RetryableOperation

async with RetryableOperation(config) as retry:
    async with session_factory() as session:
        result = await session.execute(query)
        return result
```

### 重试回调

```python
def on_retry_callback(error: Exception, attempt: int):
    logger.warning(f"Retry {attempt}: {type(error).__name__}")

users = await retry_on_db_error(
    query_users,
    config=config,
    on_retry=on_retry_callback,
)
```

### 错误模式

**可重试错误（TRANSIENT）**:
- 连接重置、连接超时
- 服务器关闭连接
- 连接池满
- 死锁检测
- 锁超时
- 序列化失败

**不可重试错误（PERMANENT）**:
- 权限拒绝
- 认证失败
- 数据库不存在
- 语法错误
- 列/表不存在
- 约束违反

---

## 连接耗尽

### 基础用法

```python
from bento.infrastructure.database import drain_connections

# 优雅关闭（等待连接完成）
await drain_connections(engine, timeout=30.0)
```

### 耗尽模式

```python
from bento.infrastructure.database import DrainingMode, drain_connections

# 优雅模式（默认）
await drain_connections(engine, timeout=30.0, mode=DrainingMode.GRACEFUL)

# 立即模式
await drain_connections(engine, timeout=30.0, mode=DrainingMode.IMMEDIATE)

# 强制模式
await drain_connections(engine, timeout=30.0, mode=DrainingMode.FORCE)
```

### 详细控制

```python
from bento.infrastructure.database import ConnectionDrainer

drainer = ConnectionDrainer(
    engine,
    timeout=30.0,
    mode=DrainingMode.GRACEFUL,
    check_interval=0.5,  # 每 0.5 秒检查一次
)

stats = await drainer.drain()
print(stats)
# {
#     'success': True,
#     'mode': 'graceful',
#     'timeout': 30.0,
#     'connections_at_start': 5,
#     'connections_at_end': 0,
#     'time_taken': 2.34
# }
```

### Kubernetes/Docker 集成

```python
import signal
import asyncio
from bento.infrastructure.database import drain_with_signal_handler

# 注册信号处理器
async def shutdown():
    await drain_with_signal_handler(engine)

loop = asyncio.get_event_loop()
for sig in (signal.SIGTERM, signal.SIGINT):
    loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
```

### FastAPI 集成

```python
from fastapi import FastAPI
from bento.infrastructure.database import drain_connections, cleanup_database

app = FastAPI()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown initiated")
    
    # 1. 耗尽连接
    await drain_connections(engine, timeout=30.0)
    
    # 2. 清理引擎
    await cleanup_database(engine)
    
    logger.info("Application shutdown complete")
```

---

## 最佳实践

### 1. 配置管理

✅ **DO**:
```python
# 使用环境变量
config = DatabaseConfig()  # 从 DB_* 环境变量读取

# 生产环境关闭 SQL 日志
config = DatabaseConfig(echo=False)

# 启用连接预检查
config = DatabaseConfig(pool_pre_ping=True)
```

❌ **DON'T**:
```python
# 不要硬编码密码
config = DatabaseConfig(url="postgresql://user:password@localhost/db")

# 不要在生产环境开启 echo
config = DatabaseConfig(echo=True)
```

### 2. 连接池配置

根据应用规模调整连接池：

```python
# 小型应用（<100 并发）
config = DatabaseConfig(pool_size=5, max_overflow=10)

# 中型应用（100-1000 并发）
config = DatabaseConfig(pool_size=20, max_overflow=20)

# 大型应用（>1000 并发）
config = DatabaseConfig(pool_size=50, max_overflow=50)
```

### 3. 会话管理

✅ **DO**:
```python
# 使用上下文管理器
async with session_factory() as session:
    async with session.begin():
        # 操作
        pass

# 事务内的操作要原子化
async with session.begin():
    user = User(name="Alice")
    session.add(user)
    order = Order(user_id=user.id)
    session.add(order)
    # 一起提交
```

❌ **DON'T**:
```python
# 不要忘记关闭会话
session = session_factory()
# ... 使用 session
# 缺少 await session.close()

# 不要在事务外执行多个依赖操作
session.add(user)
await session.commit()
session.add(order)  # user.id 可能不存在
await session.commit()
```

### 4. 错误处理

✅ **DO**:
```python
# 使用弹性重试
from bento.infrastructure.database.resilience import retry_on_db_error

users = await retry_on_db_error(query_users)

# 记录错误
try:
    result = await session.execute(query)
except Exception as e:
    logger.error(f"Query failed: {e}", exc_info=True)
    raise
```

❌ **DON'T**:
```python
# 不要忽略错误
try:
    await session.execute(query)
except:
    pass  # 错误被吞掉

# 不要重试永久错误
while True:
    try:
        await session.execute(invalid_query)
        break
    except:
        continue  # 永远循环
```

### 5. 生命周期管理

✅ **DO**:
```python
# 应用启动
async def startup():
    await init_database(engine, Base)
    
    # 健康检查
    if not await health_check(engine):
        raise RuntimeError("Database unhealthy")

# 应用关闭
async def shutdown():
    await drain_connections(engine, timeout=30.0)
    await cleanup_database(engine)
```

❌ **DON'T**:
```python
# 不要跳过初始化
# await init_database(engine, Base)  # 注释掉了

# 不要忘记清理
# await cleanup_database(engine)  # 缺少清理
```

### 6. 在 Use Cases 中使用

```python
from bento.infrastructure.database.resilience import retry_on_db_error

class CreateOrderUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow
    
    async def execute(self, command: CreateOrderCommand):
        # 包装整个事务以支持重试
        async def _create_order():
            async with self.uow:
                order = Order.create(...)
                await self.uow.repository(Order).save(order)
                await self.uow.commit()
            return order.to_dict()
        
        return await retry_on_db_error(_create_order)
```

---

## 故障排查

### 连接池耗尽

**症状**:
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size X overflow Y reached
```

**解决方案**:
```python
# 1. 增加池大小
config = DatabaseConfig(pool_size=20, max_overflow=30)

# 2. 减少超时时间
config = DatabaseConfig(pool_timeout=10.0)

# 3. 启用连接回收
config = DatabaseConfig(pool_recycle=3600)

# 4. 检查是否有未关闭的会话
async with session_factory() as session:
    # 确保使用上下文管理器
    pass
```

### 连接超时

**症状**:
```
asyncpg.exceptions.ConnectionDoesNotExistError
```

**解决方案**:
```python
# 1. 增加超时时间
config = DatabaseConfig(
    connect_timeout=30.0,
    command_timeout=120.0,
)

# 2. 启用预检查
config = DatabaseConfig(pool_pre_ping=True)

# 3. 使用重试机制
from bento.infrastructure.database.resilience import retry_on_db_error
result = await retry_on_db_error(query_func)
```

### SQLite 锁定

**症状**:
```
sqlite3.OperationalError: database is locked
```

**解决方案**:
```python
# 1. 增加超时
config = DatabaseConfig(
    url="sqlite+aiosqlite:///app.db",
    connect_timeout=30.0,
)

# 2. 使用 WAL 模式
# 在 SQLite 连接字符串中添加
url = "sqlite+aiosqlite:///app.db?journal_mode=WAL"

# 3. 考虑切换到 PostgreSQL
config = DatabaseConfig(url="postgresql+asyncpg://...")
```

### 连接泄漏

**症状**:
```
应用运行一段时间后性能下降
```

**排查**:
```python
# 获取连接池信息
info = await get_database_info(engine)
print(f"Pool size: {info['pool_size']}")
print(f"Checked out: {info['pool_checked_out']}")

# 如果 checked_out 持续增长，说明有连接泄漏
```

**解决方案**:
```python
# 1. 确保使用上下文管理器
async with session_factory() as session:
    pass  # 自动关闭

# 2. 启用连接回收
config = DatabaseConfig(pool_recycle=1800)

# 3. 定期耗尽连接（重启时）
await drain_connections(engine)
```

### 慢查询

**症状**:
```
查询响应时间长
```

**排查**:
```python
# 1. 启用 SQL 日志
config = DatabaseConfig(echo=True)

# 2. 使用 EXPLAIN 分析
result = await session.execute(text("EXPLAIN ANALYZE " + query))
print(result.fetchall())
```

**解决方案**:
```python
# 1. 添加索引
# 在 ORM 模型中
class User(Base):
    __tablename__ = "users"
    email = Column(String, index=True)  # 添加索引

# 2. 使用查询优化
# 使用 joinedload 避免 N+1 问题
from sqlalchemy.orm import joinedload
query = select(User).options(joinedload(User.orders))
```

### 测试环境问题

**问题**: 测试时数据库状态不一致

**解决方案**:
```python
import pytest
from bento.infrastructure.database import (
    create_async_engine_from_config,
    init_database,
    drop_all_tables,
)

@pytest.fixture
async def db_engine():
    # 使用内存数据库
    config = DatabaseConfig(url="sqlite+aiosqlite:///:memory:")
    engine = create_async_engine_from_config(config)
    
    # 初始化
    await init_database(engine, Base)
    
    yield engine
    
    # 清理
    await drop_all_tables(engine, Base)
    await engine.dispose()
```

---

## 完整示例

### 示例 1: FastAPI 应用

```python
from fastapi import FastAPI, Depends
from bento.infrastructure.database import (
    DatabaseConfig,
    create_async_engine_from_config,
    create_async_session_factory,
    init_database,
    cleanup_database,
    drain_connections,
    health_check,
)

app = FastAPI()

# 全局变量
engine = None
session_factory = None

@app.on_event("startup")
async def startup_event():
    global engine, session_factory
    
    # 1. 配置
    config = DatabaseConfig()
    
    # 2. 创建引擎
    engine = create_async_engine_from_config(config)
    session_factory = create_async_session_factory(engine)
    
    # 3. 初始化数据库
    await init_database(engine, Base)
    
    # 4. 健康检查
    if not await health_check(engine):
        raise RuntimeError("Database is not healthy!")
    
    print("Database initialized successfully")

@app.on_event("shutdown")
async def shutdown_event():
    # 1. 耗尽连接
    await drain_connections(engine, timeout=30.0)
    
    # 2. 清理
    await cleanup_database(engine)
    
    print("Database cleanup complete")

@app.get("/health")
async def health():
    is_healthy = await health_check(engine)
    return {"database": "healthy" if is_healthy else "unhealthy"}

@app.get("/users")
async def get_users():
    async with session_factory() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        return [{"id": u.id, "name": u.name} for u in users]
```

### 示例 2: 带重试的 Use Case

```python
from bento.infrastructure.database.resilience import (
    retry_on_db_error,
    RetryConfig,
)

class CreateOrderUseCase:
    def __init__(self, uow: IUnitOfWork):
        self.uow = uow
        
        # 自定义重试配置
        self.retry_config = RetryConfig(
            max_attempts=3,
            base_delay=0.5,
            max_delay=10.0,
        )
    
    async def execute(self, command: CreateOrderCommand):
        async def _create_order():
            async with self.uow:
                # 1. 验证客户
                customer = await self._find_customer(command.customer_id)
                if not customer:
                    raise ValueError("Customer not found")
                
                # 2. 创建订单
                order = Order.create(
                    customer_id=customer.id,
                    items=command.items,
                )
                
                # 3. 保存
                await self.uow.repository(Order).save(order)
                
                # 4. 提交（自动收集和发布事件）
                await self.uow.commit()
                
                return order.to_dict()
        
        # 使用重试机制
        return await retry_on_db_error(
            _create_order,
            config=self.retry_config,
        )
    
    async def _find_customer(self, customer_id: str):
        # 单独的查询也可以重试
        async def _query():
            return await self.uow.repository(Customer).find_by_id(customer_id)
        
        return await retry_on_db_error(_query)
```

### 示例 3: 测试配置

```python
import pytest
from bento.infrastructure.database import (
    DatabaseConfig,
    create_async_engine_from_config,
    create_async_session_factory,
    init_database,
    drop_all_tables,
)

@pytest.fixture(scope="session")
def db_config():
    return DatabaseConfig(
        url="sqlite+aiosqlite:///:memory:",
        echo=True,  # 测试时显示 SQL
    )

@pytest.fixture
async def db_engine(db_config):
    engine = create_async_engine_from_config(db_config)
    await init_database(engine, Base, check_tables=False)
    
    yield engine
    
    await drop_all_tables(engine, Base)
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    session_factory = create_async_session_factory(db_engine)
    
    async with session_factory() as session:
        yield session
        await session.rollback()  # 每个测试后回滚

@pytest.mark.asyncio
async def test_create_user(db_session):
    # 使用 session
    user = User(name="Test User")
    db_session.add(user)
    await db_session.commit()
    
    assert user.id is not None
```

---

## 性能优化建议

### 1. 连接池配置

```python
# 根据并发量调整
max_concurrent = 100
config = DatabaseConfig(
    pool_size=max(5, max_concurrent // 5),
    max_overflow=max(10, max_concurrent // 2),
)
```

### 2. 启用预检查

```python
# 避免使用失效连接
config = DatabaseConfig(pool_pre_ping=True)
```

### 3. 定期回收连接

```python
# 每小时回收一次连接
config = DatabaseConfig(pool_recycle=3600)
```

### 4. 批量操作

```python
# 批量插入
async with session.begin():
    users = [User(name=f"User {i}") for i in range(1000)]
    session.add_all(users)
```

### 5. 使用索引

```python
class User(Base):
    __tablename__ = "users"
    email = Column(String, index=True, unique=True)
    created_at = Column(DateTime, index=True)
```

---

## 监控建议

### 1. 记录数据库信息

```python
from bento.infrastructure.database import get_database_info

info = await get_database_info(engine)
logger.info(f"Database: {info['database_type']}")
logger.info(f"Pool size: {info['pool_size']}")
logger.info(f"Checked out: {info['pool_checked_out']}")
```

### 2. 定期健康检查

```python
import asyncio
from bento.infrastructure.database import health_check

async def periodic_health_check():
    while True:
        is_healthy = await health_check(engine)
        if not is_healthy:
            logger.error("Database health check failed!")
        await asyncio.sleep(60)  # 每分钟检查一次

# 启动后台任务
asyncio.create_task(periodic_health_check())
```

### 3. 监控连接池

```python
def log_pool_status(engine):
    pool = engine.pool
    logger.info(f"Pool size: {pool.size()}")
    logger.info(f"Checked out: {pool.checkedout()}")
    logger.info(f"Overflow: {pool.overflow()}")
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2025-11-05 | 初始版本，包含 P0+P1 功能 |

---

## 相关文档

- [ARCHITECTURE.md](../../applications/ecommerce/docs/ARCHITECTURE.md) - 应用架构设计
- [MESSAGING_USAGE.md](./MESSAGING_USAGE.md) - 消息系统使用
- [CACHE_ENHANCED_USAGE.md](./CACHE_ENHANCED_USAGE.md) - 缓存系统使用

---

## 支持

如有问题或建议，请提交 Issue 或 Pull Request。

