# 数据库访问示例

此目录包含展示如何在应用程序中有效使用数据库抽象层的示例。

## 架构说明

### 核心接口

数据库抽象层基于以下关键接口：

- `Database` - 数据库抽象基类，提供会话和连接管理
- `ConnectionManager` - 连接管理器接口，负责连接的获取和管理
- `SessionManager` - 会话管理器接口，负责创建和管理数据库会话
- `TransactionManager` - 事务管理器接口，负责事务的开始、提交和回滚

### 架构设计

我们采用了组合优于继承的设计原则，使用以下组件化结构：

1. `SQLAlchemyConnectionManager` - 实现了`ConnectionManager`接口，作为主要的连接管理器
2. `SQLAlchemyConnectionPool` - 作为连接管理器的组成部分，负责底层连接池管理
3. `SQLAlchemySessionManager` - 实现了`SessionManager`接口，提供会话管理功能
4. `SQLAlchemyTransactionManager` - 实现了`TransactionManager`接口，提供事务管理功能
5. `Database` - 提供了全局入口点，简化数据库操作访问

## 示例概述

### 基础示例 (example.py)

展示基本数据库操作的示例，包括：

- 使用全局函数API进行数据库操作
- 数据库会话和事务管理
- 使用仓储模式进行数据访问

```python
# 使用全局API
async with Database.session() as session:
    result = await session.execute(query)
    
# 使用事务
async with Database.transaction() as session:
    await session.execute(insert_query)
```

### FastAPI集成示例 (integration_example.py)

展示如何在FastAPI应用中集成和使用数据库抽象层：

- 应用生命周期管理 (lifespan)
- 使用依赖注入提供数据库会话
- RESTful API实现和错误处理

```python
# 依赖注入
async def get_db_session():
    async with Database.session() as session:
        yield session

@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_db_session)):
    # 使用会话查询数据
```

### 依赖注入示例 (dependency_injection_example.py)

展示如何使用依赖注入框架与数据库抽象层集成：

- 定义领域模型和数据库实体
- 仓储接口和实现
- 服务层和依赖注入配置

```python
# 仓储实现
class SQLAlchemyUserRepository:
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        async with Database.session() as session:
            user_entity = await session.get(UserEntity, str(user_id))
            return user_entity.to_domain() if user_entity else None
```

## 数据库配置

示例默认使用本地PostgreSQL数据库，连接配置示例：

```python
await Database.initialize(
    connection_string="postgresql+asyncpg://postgres:postgres@localhost:5432/example"
)
```

## 依赖

示例代码依赖：

- FastAPI - 用于API示例
- Pydantic - 用于数据验证和序列化
- SQLAlchemy 2.0 - ORM和SQL表达式
- asyncpg - PostgreSQL异步驱动程序

## 最佳实践

这些示例展示了以下最佳实践：

1. **简化数据访问** - 全局`Database`类提供简单统一的入口点
2. **关注点分离** - 通过使用仓储模式和服务层分离业务逻辑和数据访问
3. **资源管理** - 使用上下文管理器确保资源正确释放
4. **组合优于继承** - 使用组合而不是继承构建功能，提高代码的可测试性和可维护性

## 代码架构

```
Database (全局入口)
   |
   +--> SQLAlchemyConnectionManager (连接管理)
          |
          +--> SQLAlchemyConnectionPool (连接池)
          |
          +--> SQLAlchemySessionManager (会话管理)
          |
          +--> SQLAlchemyTransactionManager (事务管理)
```

这种架构设计使各组件职责明确，同时保持了较低的耦合度，方便测试和扩展。 