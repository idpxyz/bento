# 数据库基础设施

本模块提供了一个高性能、可扩展、可配置的数据库基础设施，支持多种数据库类型（PostgreSQL、MySQL、SQLite）和高级特性。

## 架构

数据库基础设施采用模块化设计，包含以下核心组件：

- **配置(config)**: 使用 Pydantic 模型管理数据库配置
- **引擎(engines)**: 为不同数据库类型提供实现
- **核心(core)**: 提供抽象接口和核心功能
- **SQLAlchemy**: 基于 SQLAlchemy 的具体实现
- **弹性(resilience)**: 错误处理和重试机制
- **监控(monitoring)**: 数据库性能监控
- **安全(security)**: 数据库安全功能
- **门面(database)**: 提供简化的单例访问API

## 特性

- **异步优先**: 完全支持 `async/await` 异步操作
- **读写分离**: 支持主从架构，配置读写分离
- **连接池管理**: 高级连接池配置和监控
- **连接耗尽(Connection Draining)**: 优雅关闭连接
- **事务管理**: 支持嵌套事务和工作单元模式
- **弹性**: 自动重试和故障恢复
- **监控**: 连接池状态和性能指标
- **简化API**: 提供全局函数用于数据库访问，无需直接管理实例

## 简化API

模块提供了三种级别的数据库访问，满足不同场景的需求：

### 会话 (Session)

```python
from idp.framework.infrastructure.db.database import session

async with session() as db_session:
    result = await db_session.execute(...)
    user = await db_session.get(UserModel, user_id)
    db_session.add(user)
    await db_session.commit()  # 手动提交更改
```

### 事务 (Transaction)

```python
from idp.framework.infrastructure.db.database import transaction

async with transaction() as tx_session:
    # 自动开始事务
    user = await tx_session.get(UserModel, user_id)
    user.is_active = False
    # 退出上下文时自动提交事务，发生异常时自动回滚
```

### 连接 (Connection)

```python
from idp.framework.infrastructure.db.database import connection
from sqlalchemy import text

async with connection() as conn:
    # 执行原始SQL
    result = await conn.execute(text("SELECT 1 AS test"))
    row = result.fetchone()
```

## 连接耗尽 (Connection Draining)

连接耗尽是一种优雅关闭数据库连接的机制，避免在应用关闭时中断正在执行的事务。

### 配置

在 `DatabaseConfig` 中可以配置连接耗尽参数：

```python
db_config = DatabaseConfig(
    # 其他配置...
    enable_draining=True,  # 启用连接耗尽
    draining_timeout=30.0,  # 等待活动连接完成的超时时间(秒)
    draining_mode="graceful",  # 耗尽模式: "graceful", "immediate", "force"
)
```

### 耗尽模式

- **graceful**: 优雅模式 - 等待现有连接完成，直到超时
- **immediate**: 立即模式 - 不等待现有连接，立即关闭数据库连接池
- **force**: 强制模式 - 强制关闭所有连接，可能导致正在执行的查询失败

### 工作原理

1. 当数据库清理开始时，连接追踪器进入关闭状态，不再接受新连接
2. 新的连接请求会收到 `DATABASE_SHUTTING_DOWN` 错误
3. 根据配置的耗尽模式，系统会：
   - 等待现有连接完成
   - 强制关闭连接
   - 或立即关闭连接池
4. 释放数据库资源并记录日志

## 使用方法

### 应用启动和关闭

```python
from idp.framework.infrastructure.db.database import initialize_database, cleanup_database
from idp.framework.infrastructure.db.config import DatabaseConfig

# 创建配置
config = DatabaseConfig(
    type=DatabaseType.POSTGRESQL,
    connection=ConnectionConfig(...),
    credentials=CredentialsConfig(...),
    # 其他配置
)

# 应用启动时
async def startup():
    await initialize_database(config)
    
# 应用关闭时
async def shutdown():
    await cleanup_database()
```

### FastAPI集成

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from idp.framework.infrastructure.db.database import initialize_database, cleanup_database, session
from idp.framework.infrastructure.db.config import (
    DatabaseConfig, 
    DatabaseType, 
    ConnectionConfig, 
    CredentialsConfig,
    PoolConfig,
    ReadWriteConfig
)

# 使用lifespan上下文管理器（推荐）
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理，处理启动和关闭事件"""
    try:
        # 配置数据库连接
        config = DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            connection=ConnectionConfig(
                host="localhost",
                port=5432,
                database="myapp"
            ),
            credentials=CredentialsConfig(
                username="user",
                password="password",
            ),
            pool=PoolConfig(
                min_size=5,
                max_size=20,
                pre_ping=True
            )
        )
        
        # 初始化数据库
        await initialize_database(config)
        yield
    finally:
        # 确保在应用关闭时清理数据库资源
        await cleanup_database()

app = FastAPI(lifespan=lifespan)

# 依赖注入
async def get_db_session():
    try:
        async with session() as db_session:
            yield db_session
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session error"
        )
        
@app.get("/users/{user_id}")
async def get_user(user_id: str, db_session = Depends(get_db_session)):
    # 使用会话操作数据库
    user = await db_session.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

有关更多详细示例和最佳实践，请参阅 [USAGE.md](./USAGE.md)。

## 贡献

欢迎提交问题和改进建议。 

## 数据库抽象层中三个关键函数的意义和区别

### 1. `connection()` - 最低级别的数据库访问

```python
async with connection() as conn:
    result = await conn.execute(text("SELECT 1 AS test"))
```

**主要特点**：
- 提供对原始数据库连接的直接访问
- 不自动管理事务
- 适合执行原始SQL查询
- 需要手动处理结果集

**适用场景**：
- 需要执行特定数据库引擎的专有SQL语句
- 性能关键的场景，需要最小化抽象层
- 特殊的连接级操作（如设置连接参数）
- 批量操作和复杂查询

### 2. `session()` - 中间级别的对象关系映射

```python
async with session() as db_session:
    user = await db_session.get(UserModel, user_id)
    db_session.add(new_user)
    await db_session.commit()
```

**主要特点**：
- 提供对象关系映射(ORM)功能
- 跟踪对象变化
- 需要手动提交或回滚事务
- 支持对象查询语言(如SQLAlchemy的select)

**适用场景**：
- 处理数据库对象而非原始SQL
- 需要对事务有精细控制（手动提交/回滚）
- 分步骤执行操作，有条件地提交
- 进行读取操作后根据结果决定是否需要写入

### 3. `transaction()` - 高级别的事务管理

```python
async with transaction() as tx_session:
    user = await tx_session.get(UserModel, user_id)
    user.is_active = False
    # 自动提交，无需手动调用commit()
```

**主要特点**：
- 自动管理事务（开始事务，提交或回滚）
- 封装了会话的所有功能
- 在上下文退出时自动提交成功的事务
- 出现异常时自动回滚

**适用场景**：
- 需要原子性操作（全部成功或全部失败）
- 简化代码，不想手动管理事务
- 多步骤更新必须作为单个单元执行
- 典型的CRUD操作模式

### 使用选择建议

1. **选择`connection()`当**：
   - 需要最大性能和最小开销
   - 执行特定数据库引擎的专有功能
   - 需要直接控制连接行为

2. **选择`session()`当**：
   - 需要使用ORM功能，但要精细控制事务
   - 需要在查询和更新之间做复杂的业务逻辑判断
   - 希望手动控制何时提交更改

3. **选择`transaction()`当**：
   - 需要简化代码，专注于业务逻辑
   - 执行必须作为单个原子单元的操作
   - 希望自动处理事务的提交和回滚

通过了解这三个抽象层次的区别，您可以根据具体需求选择最合适的接口，在代码简洁性和控制灵活性之间取得平衡。

## 连接池共享与资源管理

数据库抽象层中的 `connection()`, `session()`, 和 `transaction()` 函数底层共享同一个连接池，这是资源优化的重要设计：

```
┌──────────────────────────────────────────────┐
│             全局数据库门面 (Database)         │
└──────────────────────────┬───────────────────┘
                           │
┌──────────────────────────▼───────────────────┐
│          SQLAlchemyDatabaseFactory           │
└───┬─────────────┬───────────────┬────────────┘
    │             │               │
┌───▼────┐   ┌────▼────┐    ┌─────▼─────┐
│连接管理器│   │会话管理器│    │事务管理器 │
└───┬────┘   └────┬────┘    └─────┬─────┘
    │             │               │
    │        使用  │         使用  │
    │             │               │
┌───▼─────────────▼───────────────▼─────┐
│              连接池                    │
└─────────────────────────────────────┬─┘
                                      │
                                 ┌────▼─────┐
                                 │  数据库   │
                                 └──────────┘
```

### 连接池共享机制

1. **单例模式**：
   - 全局只初始化一个 `Database` 实例（通过 `initialize_database()` 函数）
   - 这个实例持有一个 `SQLAlchemyDatabaseFactory` 实例，负责创建和管理所有数据库组件

2. **组件层次**：
   - 连接管理器 (`ConnectionManager`) 负责直接与连接池交互
   - 会话管理器 (`SessionManager`) 使用连接管理器获取连接
   - 事务管理器 (`TransactionManager`) 使用会话管理器创建事务

3. **资源复用**：
   - `connection()` 直接从连接池获取连接
   - `session()` 使用连接管理器间接从相同连接池获取连接
   - `transaction()` 使用会话管理器，进而使用连接管理器，最终从相同连接池获取连接

### 资源使用效率

这种设计带来几个关键优势：

1. **高效连接管理**：
   - 连接在使用后返回池中而不是关闭
   - 减少频繁创建和销毁连接的开销
   - 维持适当数量的连接，避免资源浪费

2. **连接限制**：
   - 使用共享连接池确保应用不会超出数据库的连接限制
   - 池中的连接数量受到 `min_size` 和 `max_overflow` 参数控制

3. **使用示例**：

   ```python
   # 这些操作共享同一个连接池
   async def perform_operations():
       # 从共享池获取连接
       async with connection() as conn:
           await conn.execute(text("..."))
          
       # 从相同池间接获取连接
       async with session() as db_session:
           await db_session.execute(...)
           
       # 从相同池间接获取连接
       async with transaction() as tx_session:
           await tx_session.get(UserModel, user_id)
   ```

无论使用哪种抽象层次的接口，底层都是同一个连接池在管理实际的数据库连接，确保资源高效利用。
