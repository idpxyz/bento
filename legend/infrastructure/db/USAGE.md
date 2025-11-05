# 数据库抽象层使用指南

本文档提供了数据库抽象层的详细使用示例、最佳实践和常见模式，帮助开发者更有效地使用数据库功能。

## 目录

- [基础概念](#基础概念)
- [数据库访问模式](#数据库访问模式)
- [FastAPI集成](#fastapi集成)
- [事务管理](#事务管理)
- [读写分离](#读写分离)
- [高级查询](#高级查询)
- [性能优化](#性能优化)
- [错误处理](#错误处理)
- [监控与调试](#监控与调试)
- [常见问题](#常见问题)
- [故障排查](#故障排查)

## 基础概念

数据库抽象层提供了三种级别的数据库访问，每种都适用于不同的场景：

1. **会话 (Session)** - 对象关系映射的基础单元，支持ORM操作但需手动管理事务
2. **事务 (Transaction)** - 自动管理事务的会话，支持原子操作
3. **连接 (Connection)** - 底层数据库连接，用于执行原始SQL和特殊操作

### 数据库实例和全局访问

```python
# 通过全局单例获取数据库实例
from idp.framework.infrastructure.db.database import get_database

db = get_database()

# 或者直接使用全局访问函数
from idp.framework.infrastructure.db.database import session, transaction, connection
```

### 配置示例

```python
from idp.framework.infrastructure.db.config import (
    DatabaseConfig, 
    DatabaseType, 
    ConnectionConfig, 
    CredentialsConfig,
    PoolConfig,
    ReadWriteConfig
)

config = DatabaseConfig(
    type=DatabaseType.POSTGRESQL,
    connection=ConnectionConfig(
        host="localhost",
        port=5432,
        database="myapp",
        application_name="my_application"
    ),
    credentials=CredentialsConfig(
        username="app_user",
        password="password"
    ),
    pool=PoolConfig(
        min_size=5,
        max_size=20,
        pre_ping=True,
        timeout=30.0
    ),
    read_write=ReadWriteConfig(
        enable_read_write_split=False  # 默认禁用读写分离
    )
)
```

## 数据库访问模式

### 使用会话

会话是最常用的数据库访问方式，适合需要手动控制事务的场景：

```python
from idp.framework.infrastructure.db.database import session
from sqlalchemy import select

async def get_user_by_email(email: str):
    async with session() as db_session:
        query = select(UserModel).where(UserModel.email == email)
        result = await db_session.execute(query)
        return result.scalar_one_or_none()

async def create_user(user_data: dict):
    async with session() as db_session:
        # 创建用户实例
        new_user = UserModel(**user_data)
        db_session.add(new_user)
        
        # 手动提交更改
        await db_session.commit()
        return new_user
```

### 使用事务

事务提供了原子操作保证，适合需要全部成功或全部失败的场景：

```python
from idp.framework.infrastructure.db.database import transaction

async def transfer_funds(from_account_id: str, to_account_id: str, amount: float):
    async with transaction() as db_session:
        # 获取账户
        from_account = await db_session.get(AccountModel, from_account_id)
        to_account = await db_session.get(AccountModel, to_account_id)
        
        if not from_account or not to_account:
            raise ValueError("Account not found")
            
        if from_account.balance < amount:
            raise ValueError("Insufficient funds")
            
        # 执行转账
        from_account.balance -= amount
        to_account.balance += amount
        
        # 记录交易
        transaction_record = TransactionModel(
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            amount=amount
        )
        db_session.add(transaction_record)
        
        # 事务会自动提交，如果有任何异常会自动回滚
```

### 使用连接

连接提供了对底层数据库的直接访问，适合执行原始SQL和批量操作：

```python
from idp.framework.infrastructure.db.database import connection
from sqlalchemy import text

async def execute_complex_query(params: dict):
    async with connection() as conn:
        # 执行复杂SQL查询
        sql = """
        WITH ranked_data AS (
            SELECT id, name, value, 
                   ROW_NUMBER() OVER (PARTITION BY category ORDER BY value DESC) as rank
            FROM items
            WHERE created_at > :from_date
        )
        SELECT * FROM ranked_data WHERE rank <= 10
        """
        result = await conn.execute(text(sql), {"from_date": params["from_date"]})
        return [dict(row) for row in result.fetchall()]
```

## FastAPI集成

### 数据库生命周期管理

FastAPI应用中的数据库生命周期可以通过lifespan事件或启动/关闭事件管理：

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from idp.framework.infrastructure.db.database import initialize_database, cleanup_database
from idp.framework.infrastructure.db.config import DatabaseConfig

# 方法1: 使用lifespan上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化数据库
    config = get_database_config()
    await initialize_database(config)
    yield
    # 清理数据库资源
    await cleanup_database()

app = FastAPI(lifespan=lifespan)

# 方法2: 使用事件处理器
app = FastAPI()

@app.on_event("startup")
async def startup():
    config = get_database_config()
    await initialize_database(config)
    
@app.on_event("shutdown")
async def shutdown():
    await cleanup_database()
```

### 依赖注入

使用依赖注入提供数据库会话给路由处理函数：

```python
from fastapi import Depends, FastAPI, HTTPException, status
from idp.framework.infrastructure.db.database import session, transaction

# 会话依赖
async def get_db_session():
    try:
        async with session() as db_session:
            yield db_session
    except Exception as e:
        # 捕获并转换数据库错误为HTTP错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error"
        )

# 事务依赖
async def get_db_transaction():
    try:
        async with transaction() as tx_session:
            yield tx_session
    except Exception as e:
        # 异常已经导致事务回滚
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transaction error"
        )

# 在路由中使用
@app.get("/users/{user_id}")
async def get_user(user_id: str, db_session = Depends(get_db_session)):
    user = await db_session.get(UserModel, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users")
async def create_user(
    user_data: UserCreate, 
    db_session = Depends(get_db_transaction)
):
    # 检查用户是否存在
    existing = await db_session.execute(
        select(UserModel).where(UserModel.email == user_data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already exists"
        )
    
    # 创建用户
    new_user = UserModel(
        id=str(uuid.uuid4()),
        email=user_data.email,
        username=user_data.username,
        is_active=True
    )
    db_session.add(new_user)
    
    # 事务会自动提交
    return new_user
```

## 事务管理

### 隔离级别

SQLAlchemy支持不同的事务隔离级别，可以通过`transaction()`函数指定：

```python
from idp.framework.infrastructure.db.database import transaction

# 使用读已提交隔离级别
async with transaction(isolation_level="READ COMMITTED") as session:
    # 事务操作...

# 使用可序列化隔离级别
async with transaction(isolation_level="SERIALIZABLE") as session:
    # 事务操作...
```

### 嵌套事务

由于事务已经集成了会话功能，推荐避免嵌套事务。如果需要分阶段操作，可以先使用会话执行只读操作，再使用事务执行写操作：

```python
async def complex_operation(item_id: str, new_data: dict):
    # 第一阶段：检查操作（只读）
    async with session() as db_session:
        # 检查项目是否存在
        item = await db_session.get(ItemModel, item_id)
        if not item:
            raise ValueError("Item not found")
            
        # 验证数据
        if not validate_data(item, new_data):
            raise ValueError("Invalid data")
    
    # 第二阶段：更新操作（写入）
    async with transaction() as tx_session:
        # 重新获取项目
        item = await tx_session.get(ItemModel, item_id)
        # 更新项目
        for key, value in new_data.items():
            setattr(item, key, value)
        # 自动提交
```

## 读写分离

当启用读写分离时，可以使用`read_replica()`函数从只读副本获取会话：

```python
from idp.framework.infrastructure.db.database import session, read_replica, transaction

async def get_user_stats(user_id: str):
    # 读操作使用副本
    async with read_replica() as db_session:
        # 执行复杂查询
        result = await db_session.execute(
            text("SELECT COUNT(*) FROM user_activities WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        return result.scalar()

async def update_user_profile(user_id: str, profile_data: dict):
    # 写操作使用主库
    async with transaction() as tx_session:
        user = await tx_session.get(UserModel, user_id)
        if not user:
            raise ValueError("User not found")
            
        # 更新用户资料
        for key, value in profile_data.items():
            setattr(user.profile, key, value)
```

## 高级查询

### 使用SQLAlchemy ORM

```python
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

async def search_products(
    category_id: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    tags: Optional[List[str]] = None,
    limit: int = 20,
    offset: int = 0
):
    async with session() as db_session:
        # 构建基本查询
        query = select(ProductModel)
        
        # 应用筛选条件
        filters = []
        if category_id:
            filters.append(ProductModel.category_id == category_id)
        if min_price is not None:
            filters.append(ProductModel.price >= min_price)
        if max_price is not None:
            filters.append(ProductModel.price <= max_price)
        if tags:
            filters.append(ProductModel.tags.contains(tags))
            
        if filters:
            query = query.where(and_(*filters))
            
        # 排序和分页
        query = query.order_by(ProductModel.created_at.desc())
        query = query.offset(offset).limit(limit)
        
        # 执行查询
        result = await db_session.execute(query)
        return result.scalars().all()
```

### 使用原始SQL

对于复杂查询，可以使用原始SQL：

```python
from sqlalchemy import text

async def get_sales_statistics(start_date: datetime, end_date: datetime):
    async with session() as db_session:
        query = text("""
            SELECT 
                product_id,
                product_name,
                SUM(quantity) as total_sold,
                SUM(price * quantity) as total_revenue,
                COUNT(DISTINCT customer_id) as unique_customers
            FROM sales
            WHERE sale_date BETWEEN :start_date AND :end_date
            GROUP BY product_id, product_name
            ORDER BY total_revenue DESC
            LIMIT 10
        """)
        
        result = await db_session.execute(
            query, 
            {"start_date": start_date, "end_date": end_date}
        )
        
        return [dict(row) for row in result.fetchall()]
```

## 性能优化

### 连接池配置

```python
config = DatabaseConfig(
    # 其他配置...
    pool=PoolConfig(
        min_size=10,        # 连接池最小连接数
        max_size=50,        # 连接池最大连接数（包括溢出）
        max_overflow=40,    # 最大溢出连接数
        timeout=30.0,       # 获取连接超时时间
        recycle=3600,       # 连接最大使用时间（秒）
        pre_ping=True       # 使用前检查连接是否有效
    )
)
```

### 批量操作

对于大量数据的插入或更新，使用批量操作会更高效：

```python
async def bulk_insert_items(items: List[dict]):
    async with transaction() as tx_session:
        # 创建实体对象
        item_objects = [ItemModel(**item) for item in items]
        
        # 批量添加
        tx_session.add_all(item_objects)
        # 事务自动提交
```

## 错误处理

### 自定义异常转换

在实际应用中，通常需要将数据库异常转换为域异常或API响应：

```python
from idp.framework.infrastructure.db.resilience.errors import DatabaseError

async def create_user(user_data: dict):
    try:
        async with transaction() as tx_session:
            # 检查用户是否存在
            existing = await tx_session.execute(
                select(UserModel).where(UserModel.email == user_data["email"])
            )
            if existing.scalar_one_or_none():
                raise DomainError("User already exists", code="USER_EXISTS")
                
            # 创建用户
            new_user = UserModel(**user_data)
            tx_session.add(new_user)
            
        return new_user
    except DatabaseError as e:
        # 数据库错误转换为域错误
        if "unique constraint" in str(e).lower():
            raise DomainError("User with this email already exists", code="USER_EXISTS")
        elif "connection" in str(e).lower():
            raise InfrastructureError("Database connection error", code="DB_CONNECTION_ERROR")
        else:
            raise InfrastructureError(f"Database error: {str(e)}", code="DB_ERROR")
```

## 监控与调试

### 获取数据库统计信息

```python
from idp.framework.infrastructure.db.database import get_database

async def get_db_health_metrics():
    db = get_database()
    
    # 获取数据库健康状态
    is_healthy = await db.health_check()
    
    # 获取详细统计信息
    stats = await db.get_stats()
    
    return {
        "healthy": is_healthy,
        "stats": stats
    }
```

## 常见问题

### 事务已经开始错误

如果出现 "A transaction is already begun on this Session" 错误，通常是尝试在已有事务的会话上开始新事务。解决方法是避免嵌套事务，或者使用不同的会话实例：

```python
# 错误的方式
async with transaction() as tx_session:
    # ...
    async with tx_session.begin():  # 错误！会话已经在事务中
        # ...

# 正确的方式
async with transaction() as tx_session:
    # 所有操作都在同一个事务中
    # ...

# 或者使用两个独立的操作
async with session() as db_session:
    # 只读操作
    # ...

async with transaction() as tx_session:
    # 写入操作
    # ...
```

### 连接关闭错误

如果遇到 "connection is closed" 错误，可能是会话或连接已被关闭后仍尝试使用。解决方法是确保在适当的范围内使用会话/连接：

```python
# 错误的方式
async with session() as db_session:
    user = await db_session.get(UserModel, user_id)

# 会话已关闭
await db_session.refresh(user)  # 错误！会话已关闭

# 正确的方式
async with session() as db_session:
    user = await db_session.get(UserModel, user_id)
    # 在会话关闭前使用
    user_data = {
        "id": user.id,
        "name": user.name,
        # 其他属性...
    }

# 使用从会话中提取的数据
process_user(user_data)
```

### 高级事务控制

对于需要特定保存点或手动事务控制的场景：

```python
async with session() as db_session:
    # 手动开始事务
    async with db_session.begin():
        # 执行一些操作
        user = await db_session.get(UserModel, user_id)
        user.name = "New Name"
        
        # 创建保存点
        savepoint = await db_session.begin_nested()
        try:
            # 执行可能失败的操作
            user.email = "new_email@example.com"
            # 验证邮箱
            if not validate_email(user.email):
                raise ValueError("Invalid email")
        except Exception:
            # 回滚到保存点
            await savepoint.rollback()
            # 但保留其他更改
        
        # 提交事务
        # 事务会在上下文退出时自动提交
```

## 故障排查

### 深入分析：PreparedStatement连接关闭问题

我们已经分析了SQLAlchemy和asyncpg的底层实现代码，找出了导致"cannot call PreparedStatement.fetch(): the underlying connection is closed"错误的根本原因，并提供了系统性解决方案：

#### 底层原因深度分析

1. **SQLAlchemy异步会话与asyncpg的连接生命周期不同步**：

   ```
   SQLAlchemySessionManager.create_session()
   └── 通过SQLAlchemyConnectionManager.acquire()获取连接
      └── 在上下文退出时自动释放连接到连接池
         └── 如果在连接释放后尝试访问结果集，会导致"connection is closed"错误
   ```

2. **关键代码路径分析**：

   在`connection.py`和`session.py`中，我们可以看到几个关键点：

   ```python
   # SQLAlchemyConnectionManager.acquire()中
   async with self._connection_pool.acquire() as connection:
       # ... 连接被获取和使用 ...
       yield connection
   # 在此点，连接被释放回池
   
   # SQLAlchemySessionManager.create_session()中
   async with self._connection_manager.acquire() as connection:
       session = self._session_factory(bind=connection)
       # ... 会话被创建和使用 ...
       yield session
       await session.commit()
   # 在此点，session和底层连接都被释放
   ```

3. **关键问题**: 

   当SQLAlchemy的`AsyncSession`创建一个PreparedStatement，该语句引用了底层的asyncpg连接。当会话关闭时，连接被返回到池中，但PreparedStatement仍然保持对旧连接的引用。如果随后尝试从这个PreparedStatement获取结果，asyncpg会抛出错误，因为连接已经被关闭或返回到池中。

#### 系统性解决方案

1. **应用级别解决方案**

   ```python
   # 增强的结果缓存包装器
   class ResultHandler:
       """安全处理SQLAlchemy查询结果"""
       
       @staticmethod
       async def with_session(session_func):
           """会话结果处理装饰器
           
           确保在会话范围内处理所有结果
           """
           async def wrapper(*args, **kwargs):
               async with session() as session:
                   # 确保session_func接收会话作为第一个参数
                   return await session_func(session, *args, **kwargs)
           return wrapper
           
       @staticmethod
       async def process_result(result, processor):
           """处理查询结果
           
           在结果对象存在时立即处理结果
           """
           # 立即处理结果
           return await processor(result)
           
       @staticmethod
       async def fetch_all(result):
           """安全获取所有结果行"""
           return [dict(row) for row in result.fetchall()]
           
       @staticmethod
       async def fetch_one(result):
           """安全获取单行结果"""
           row = result.fetchone()
           return dict(row) if row else None
           
       @staticmethod
       async def fetch_many(result, size=100):
           """安全批量获取结果"""
           rows = result.fetchmany(size)
           return [dict(row) for row in rows]
   
   # 示例用法 - 方法1：使用装饰器
   @ResultHandler.with_session
   async def get_users(session, status=None):
       query = select(UserModel)
       if status is not None:
           query = query.where(UserModel.status == status)
       
       result = await session.execute(query)
       # 立即处理结果
       users = await ResultHandler.fetch_all(result)
       return users
   
   # 示例用法 - 方法2：直接使用
   async def get_products(category_id):
       async with session() as db_session:
           query = select(ProductModel).where(ProductModel.category_id == category_id)
           result = await db_session.execute(query)
           # 立即处理结果
           return await ResultHandler.fetch_all(result)
   ```

2. **基础设施级别优化**

   通过在`SQLAlchemySessionManager`中增加自动结果处理功能：

   ```python
   # 优化后的会话管理器
   class EnhancedSessionManager(SQLAlchemySessionManager):
       """增强的会话管理器，自动处理结果集"""
       
       @asynccontextmanager
       async def execute_with_result(self, query, params=None, auto_fetch=True):
           """执行查询并安全返回结果
           
           Args:
               query: SQL查询或SQLAlchemy查询对象
               params: 查询参数
               auto_fetch: 是否自动获取所有结果
           """
           async with self.create_session() as session:
               result = await session.execute(query, params)
               
               if auto_fetch:
                   # 立即获取所有结果
                   data = [dict(row) for row in result.fetchall()]
                   yield data
               else:
                   # 返回结果集，使用者必须在会话关闭前处理
                   yield result
   
   # 使用示例
   async def get_users_by_role(role_id):
       async with enhanced_session_manager.execute_with_result(
           select(UserModel).where(UserModel.role_id == role_id)
       ) as users:
           # users已经是完全获取的结果列表
           return users
   ```

3. **连接设置优化**

   在数据库配置中，添加以下设置以提高连接的稳定性：

   ```python
   db_config = DatabaseConfig(
       # 其他配置...
       pool=PoolConfig(
           # 使用前验证连接
           pre_ping=True,
           # 连接返回池时重置状态
           reset_on_return=True,
           # 连接最大使用时间
           recycle=1800,
           # 更健壮的连接处理
           pool_timeout=30,
           echo_pool=True   # 开发环境调试用
       )
   )
   ```

4. **事务模式优化**

   为避免连接问题，推荐使用以下事务模式：

   ```python
   # 推荐模式：单一文件原则
   async def safe_transaction_pattern():
       """安全的事务模式，遵循'单一文件原则'"""
       async with transaction() as tx_session:
           # 第1步：执行所有查询
           result1 = await tx_session.execute(query1)
           data1 = result1.fetchall()  # 立即获取结果
           
           result2 = await tx_session.execute(query2)
           data2 = result2.fetchall()  # 立即获取结果
           
           # 第2步：处理数据，进行业务逻辑判断
           combined_data = process_data(data1, data2)
           
           # 第3步：执行所有写操作
           for item in combined_data:
               new_entity = EntityModel(**item)
               tx_session.add(new_entity)
           
           # 事务自动提交
       
       # 返回处理结果
       return format_result(combined_data)
   ```

#### 总结：彻底解决方案

1. **结果处理原则**：
   - 始终在连接/会话上下文内获取结果
   - 使用结果缓存包装器将结果转换为普通Python对象
   - 遵循"先查询后处理"的分离原则

2. **连接管理增强**：
   - 在配置中启用`reset_on_return`和`pre_ping`
   - 增加连接池大小以处理峰值负载
   - 实现智能重试机制处理临时连接问题

3. **会话使用模式**：
   - 使用统一的会话处理模式，如上面的ResultHandler类
   - 实现基于模式的结果处理，确保安全获取
   - 避免在会话外保存或使用SQLAlchemy的结果对象

通过实施这些措施，可以彻底解决"PreparedStatement.fetch(): the underlying connection is closed"错误，确保应用稳定运行。

### 避免PreparedStatement连接关闭错误

如果遇到以下错误，表示在尝试获取PreparedStatement结果时底层连接已关闭：

```
ConnectionError: Session error: Error getting connection: 
(sqlalchemy.dialects.postgresql.asyncpg.InterfaceError) <class 'asyncpg.exceptions._base.InterfaceError'>: 
cannot call PreparedStatement.fetch(): the underlying connection is closed
```

这个错误通常有几个关键原因和解决方案：

#### 1. 结果获取与连接生命周期不同步

**问题：**
```python
# 错误示例
async def get_data():
    async with connection() as conn:
        # 执行查询获取结果
        result = await conn.execute(text("SELECT * FROM users"))
    
    # 错误：在连接关闭后尝试获取结果
    rows = result.fetchall()  # 将引发InterfaceError
    return rows
```

**解决方案：**
```python
# 正确做法：在连接上下文内获取结果
async def get_data():
    async with connection() as conn:
        # 执行查询获取结果
        result = await conn.execute(text("SELECT * FROM users"))
        # 在连接关闭前获取所有结果
        rows = result.fetchall()  
    
    return rows
```

#### 2. 查询执行与事务管理不同步

**问题：**
```python
# 错误示例 - 事务在获取结果前提交
async def complex_operation():
    async with session() as db_session:
        await db_session.execute("BEGIN")
        result = await db_session.execute(text("SELECT * FROM items"))
        # 提交事务
        await db_session.commit()
        
        # 错误：事务已提交，连接可能已返回池或重置
        items = result.fetchall()  # 可能引发InterfaceError
        return items
```

**解决方案：**
```python
# 正确做法：在提交前获取结果
async def complex_operation():
    async with session() as db_session:
        async with db_session.begin():
            result = await db_session.execute(text("SELECT * FROM items"))
            # 在事务提交前获取结果
            items = result.fetchall()
            
    return items
```

#### 3. 长时间执行的操作导致连接超时

**问题：**
```python
# 错误示例：长时间操作可能导致连接超时
async def slow_operation():
    async with connection() as conn:
        result = await conn.execute(text("SELECT * FROM large_table"))
        
        # 长时间处理，可能导致连接超时或被池回收
        await process_data_slowly(some_data)  # 耗时操作
        
        # 此时尝试获取结果，连接可能已关闭
        rows = result.fetchall()  # 可能引发InterfaceError
        return rows
```

**解决方案：**
```python
# 正确做法：立即获取结果，然后处理数据
async def slow_operation():
    data_to_process = []
    
    async with connection() as conn:
        result = await conn.execute(text("SELECT * FROM large_table"))
        # 立即获取所有需要的数据
        data_to_process = result.fetchall()
    
    # 连接关闭后再处理数据
    processed_data = await process_data_slowly(data_to_process)
    return processed_data
```

#### 4. 异步查询结果的缓存

**问题：**
SQLAlchemy结果对象不能在会话或连接关闭后使用，尝试这样做会导致连接已关闭错误。

**解决方案：**
实现一个结果缓存包装器：

```python
class ResultCache:
    """缓存SQLAlchemy查询结果，避免连接关闭后的访问错误"""
    
    @staticmethod
    async def fetch_all(result):
        """立即获取并缓存所有行"""
        return [dict(row) for row in result.fetchall()]
    
    @staticmethod
    async def fetch_one(result):
        """立即获取并缓存单行"""
        row = result.fetchone()
        return dict(row) if row else None
    
    @staticmethod
    async def scalar(result):
        """立即获取并缓存标量值"""
        return result.scalar()
    
    @staticmethod
    async def scalar_one_or_none(result):
        """立即获取并缓存标量值（单个或None）"""
        return result.scalar_one_or_none()

# 使用示例
async def get_users():
    async with session() as db_session:
        result = await db_session.execute(
            select(UserModel).where(UserModel.is_active == True)
        )
        # 立即缓存结果
        users = await ResultCache.fetch_all(result)
    
    # 连接关闭后仍可使用缓存的结果
    return users
```

#### 5. 优化实践与模式

1. **查询-获取-处理模式**：
   ```python
   async def safe_query_pattern():
       # 第一阶段：执行查询并获取数据
       data = None
       async with session() as db_session:
           result = await db_session.execute(query)
           data = result.fetchall()  # 立即获取所有数据
       
       # 第二阶段：连接关闭后处理数据
       return process_data(data)
   ```

2. **批处理模式**（适用于大量数据）：
   ```python
   async def batch_processing_pattern():
       async with session() as db_session:
           result = await db_session.execute(
               text("SELECT * FROM large_table")
           )
           
           # 分批处理结果
           batch_size = 1000
           batch = result.fetchmany(batch_size)
           while batch:
               # 处理当前批次
               await process_batch(batch)
               # 获取下一批
               batch = result.fetchmany(batch_size)
   ```

3. **检查连接状态**（预防性方法）：
   ```python
   async def check_then_fetch():
       async with connection() as conn:
           # 在执行查询前检查连接是否有效
           is_valid = await conn.scalar(text("SELECT 1"))
           if not is_valid:
               raise ValueError("Database connection invalid")
               
           result = await conn.execute(text("SELECT * FROM users"))
           return result.fetchall()
   ```

4. **使用事务包装复杂操作**：
   ```python
   async def transaction_wrapped_operation():
       async with transaction() as tx_session:
           # 所有操作在单一事务中执行
           result1 = await tx_session.execute(query1)
           data1 = result1.fetchall()
           
           # 第二个查询
           result2 = await tx_session.execute(query2)
           data2 = result2.fetchall()
           
           # 处理和修改数据...
           
           # 事务自动提交
       
       # 返回结果
       return combine_results(data1, data2)
   ```

通过应用这些模式和实践，可以有效避免"连接已关闭"类型的错误，提高应用程序的稳定性和可靠性。

### 接口返回 "Database session error"

如果API接口突然返回以下错误响应，并且在一段时间内持续不可访问：

```json
{
  "detail": "Database session error"
}
```

这通常表示数据库连接出现了严重问题，可能是数据库服务不可用或连接资源耗尽。

#### 可能的原因

1. **数据库服务不可用**：
   - 数据库服务器宕机或重启
   - 网络连接问题阻止应用程序访问数据库
   - 防火墙规则变更导致连接被阻止

2. **连接资源耗尽**：
   - 数据库连接池已满且所有连接都在使用中
   - 数据库服务器达到最大连接数限制
   - 连接泄漏导致可用连接逐渐减少

3. **认证/权限问题**：
   - 数据库用户密码过期或被修改
   - 数据库用户权限被撤销
   - 使用的角色或模式不存在或无访问权限

4. **资源限制**：
   - 数据库服务器CPU或内存资源耗尽
   - 磁盘空间不足
   - 连接超时设置过短

#### 诊断步骤

1. **检查数据库服务状态**：
   ```bash
   # 对于PostgreSQL
   pg_isready -h <hostname> -p <port>
   
   # 对于MySQL/MariaDB
   mysqladmin -h <hostname> -P <port> -u <username> -p ping
   ```

2. **验证网络连接**：
   ```bash
   # 检查能否连接到数据库端口
   telnet <hostname> <port>
   
   # 或使用nc命令
   nc -zv <hostname> <port>
   ```

3. **检查应用日志**：
   查找更详细的错误信息，特别是包含以下关键词的日志：
   - "connection refused"
   - "authentication failed"
   - "too many connections"
   - "connection timeout"

4. **检查数据库连接状态**：
   ```sql
   -- PostgreSQL检查活动连接
   SELECT count(*) FROM pg_stat_activity;
   
   -- MySQL检查活动连接
   SHOW STATUS WHERE Variable_name = 'Threads_connected';
   ```

5. **检查连接池统计信息**：
   ```python
   # 获取数据库统计信息
   from idp.framework.infrastructure.db.database import get_database
   
   db = get_database()
   stats = await db.get_stats()
   print(f"连接池统计: {stats}")
   ```

#### 解决方案

1. **重启数据库服务**（如果是管理员）：
   ```bash
   # PostgreSQL
   sudo systemctl restart postgresql
   
   # MySQL
   sudo systemctl restart mysql
   ```

2. **增加连接池容量**：
   ```python
   config = DatabaseConfig(
       # 其他配置...
       pool=PoolConfig(
           min_size=10,        # 增加最小连接数
           max_size=50,        # 增加最大连接数
           max_overflow=40,    # 增加溢出连接数
           timeout=60.0,       # 增加获取连接的超时时间
       )
   )
   ```

3. **实现连接重试机制**：
   ```python
   async def get_db_with_retry(max_retries=3, retry_delay=1.0):
       """获取数据库会话，带重试机制"""
       retries = 0
       last_error = None
       
       while retries < max_retries:
           try:
               async with session() as db_session:
                   yield db_session
                   return
           except Exception as e:
               last_error = e
               retries += 1
               if retries < max_retries:
                   logger.warning(f"Database connection failed, retrying ({retries}/{max_retries})...")
                   await asyncio.sleep(retry_delay)
       
       # 如果所有重试都失败
       logger.error(f"Failed to connect to database after {max_retries} attempts: {last_error}")
       raise HTTPException(
           status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
           detail="Database service unavailable, please try again later"
       )
   ```

4. **实现数据库健康检查恢复机制**：
   ```python
   @app.middleware("http")
   async def db_health_middleware(request: Request, call_next):
       # 跳过健康检查端点，避免递归
       if request.url.path == "/health":
           return await call_next(request)
           
       # 检查数据库健康状态
       db = get_database()
       if not await db.health_check():
           # 尝试重新初始化数据库连接
           try:
               logger.warning("Database unhealthy, attempting reconnection...")
               await cleanup_database()
               await initialize_database(get_config())
               
               if not await db.health_check():
                   return JSONResponse(
                       status_code=503,
                       content={"detail": "Database service unavailable"}
                   )
           except Exception as e:
               logger.error(f"Failed to reconnect to database: {e}")
               return JSONResponse(
                   status_code=503,
                   content={"detail": "Database service unavailable"}
               )
               
       return await call_next(request)
   ```

#### 预防措施

1. **实现冗余和故障转移**：
   - 配置数据库主从复制
   - 在配置中启用读写分离，失败时自动切换到备用节点

2. **实现定期连接池刷新**：
   ```python
   async def refresh_connection_pool():
       """定期刷新连接池，丢弃潜在的有问题连接"""
       while True:
           await asyncio.sleep(3600)  # 每小时
           try:
               db = get_database()
               # 获取当前统计信息记录
               before_stats = await db.get_stats()
               
               # 执行连接池刷新（实现取决于具体数据库适配器）
               # 对于大多数连接池，可以通过销毁并重新创建池来实现
               await cleanup_database()
               await initialize_database(get_config())
               
               after_stats = await db.get_stats()
               logger.info(f"Connection pool refreshed: {before_stats} -> {after_stats}")
           except Exception as e:
               logger.error(f"Failed to refresh connection pool: {e}")
   
   # 在应用启动时启动后台任务
   @app.on_event("startup")
   async def start_background_tasks():
       asyncio.create_task(refresh_connection_pool())
   ```

3. **监控和报警**：
   - 实现数据库连接监控
   - 当可用连接数低于阈值时发送告警
   - 监控连接使用时间，识别长时间运行的查询

4. **优化查询和连接使用**：
   - 减少长时间运行的查询
   - 确保所有数据库操作都使用上下文管理器
   - 避免在循环中创建数据库连接

通过以上措施，可以更有效地预防、诊断和处理"Database session error"错误，提高应用的稳定性和可用性。

### 间歇性的健康检查失败

如果健康检查接口出现间歇性失败，交替显示健康和不健康状态，并出现如下错误：

```
"Health check failed: Can't reconnect until invalid transaction is rolled back. 
Please rollback() fully before proceeding"
```

这通常表示存在**事务泄漏**问题。

#### 原因分析

1. **连接池争用**：
   - 健康检查可能在多个连接之间交替进行
   - 一些连接处于有效状态，而其他连接处于未完成事务的状态
   - 当健康检查使用处于良好状态的连接时返回200 OK
   - 当使用带有未完成事务的连接时返回503错误

2. **事务泄漏**：
   - 某些代码路径没有正确提交或回滚事务
   - 连接返回池时仍处于事务中
   - 后续使用该连接的操作会遇到"invalid transaction"错误

3. **自动恢复**：
   - 连接池可能配置了`pool_recycle`参数，导致问题连接在一段时间后被重置
   - 连接池的预检机制(`pre_ping=True`)会在一段时间后丢弃有问题的连接

#### 解决方案

1. **使用上下文管理器**：
   ```python
   # 正确: 使用上下文管理器确保事务完成
   async with transaction() as tx_session:
       # 操作
       # 自动提交或回滚
   ```

2. **检查事务泄漏的位置**：
   - 检查使用原始会话的代码路径
   - 特别关注异常处理路径
   - 确保每个开始的事务都正确结束

3. **增加以下配置增强鲁棒性**：
   ```python
   config = DatabaseConfig(
       # 其他配置...
       pool=PoolConfig(
           pre_ping=True,  # 使用前检查连接
           recycle=1800,   # 30分钟后回收连接
           reset_on_return=True  # 返回池时重置连接状态
       )
   )
   ```

4. **实现事务监控**：
   ```python
   # 监控长时间运行的事务
   async def monitor_long_transactions():
       db = get_database()
       stats = await db.get_stats()
       active_transactions = stats.get("active_transactions", 0)
       if active_transactions > 0:
           logger.warning(f"Found {active_transactions} active transactions")
   ```

#### 预防措施

1. **使用高级抽象**：
   - 优先使用`transaction()`而不是手动管理事务
   - 避免直接调用`begin()`/`commit()`/`rollback()`

2. **实现请求级事务**：
   ```python
   @app.middleware("http")
   async def db_session_middleware(request: Request, call_next):
       async with transaction() as session:
           # 将会话附加到请求状态
           request.state.db_session = session
           response = await call_next(request)
           # 上下文退出时自动提交事务
           return response
   ```

3. **实现全局异常处理器**：
   ```python
   @app.exception_handler(Exception)
   async def global_exception_handler(request: Request, exc: Exception):
       # 确保在异常情况下回滚任何未完成的事务
       if hasattr(request.state, "db_session"):
           await request.state.db_session.rollback()
       # 处理异常...
   ```

通过这些措施，您可以解决事务泄漏导致的间歇性健康检查失败问题，并提高应用程序的稳定性。 