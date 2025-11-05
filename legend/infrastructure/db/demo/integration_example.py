"""
FastAPI与数据库抽象层集成示例

本示例展示如何在FastAPI应用中集成和使用数据库抽象层。
包括应用启动/关闭事件处理、依赖注入配置和RESTful API实现。
"""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import List

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, Column, String, select, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from idp.framework.bootstrap.component.logger_setup import logger_setup
from idp.framework.infrastructure.db.config import (
    ConnectionConfig,
    CredentialsConfig,
    DatabaseConfig,
    DatabaseType,
    PoolConfig,
    ReadWriteConfig,
)
from idp.framework.infrastructure.db.database import (
    cleanup_database,
    connection,
    get_database,
    initialize_database,
    session,
    transaction,
)
from idp.framework.infrastructure.logger import logger_manager

# 配置日志记录器
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[logging.StreamHandler()]
# )

# 获取应用日志记录器
logger = logger_manager.get_logger(__name__)
# logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    """基础模型类"""
    pass

# 数据模型定义
class UserModel(Base):
    """用户数据库模型"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)


# API请求/响应模型
class UserCreate(BaseModel):
    """用户创建请求模型"""
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    is_active: bool = Field(default=True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "is_active": True
            }
        }


class UserResponse(BaseModel):
    """用户响应模型"""
    id: str
    email: str
    username: str
    is_active: bool
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "username": "johndoe",
                "is_active": True
            }
        },
        "from_attributes": True
    }


# 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理，处理启动和关闭事件"""
    try:
        # 设置日志
        # await logger_setup()
        # 配置数据库连接
        config = DatabaseConfig(
            type=DatabaseType.POSTGRESQL,
            connection=ConnectionConfig(
                host="192.168.8.137",
                port=5438,
                database="idp",
                application_name="database_example"
            ),
            credentials=CredentialsConfig(
                username="topsx",
                password="thends",
            ),
            pool=PoolConfig(
                min_size=5,
                max_size=20,
                recycle=1800,
                pre_ping=True
            ),
            read_write=ReadWriteConfig(
                enable_read_write_split=False
            )
        )
        
        # 初始化数据库
        logger.info("Initializing database...")
        await initialize_database(config)
        logger.info("Database initialized successfully")
        
        # 获取数据库实例
        db = get_database()
        
        # 创建数据库表（仅在开发环境中使用）
        try:
            logger.info("Creating database tables...")
            
            # 直接使用事务创建表 - 避免尝试访问引擎
            async with transaction() as db_session:
                try:
                    # 将多条SQL语句分开执行
                    # 创建表
                    await db_session.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id UUID PRIMARY KEY,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        is_active BOOLEAN DEFAULT TRUE
                    )
                    """))
                    
                    # 创建索引 - 分别执行
                    await db_session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
                    """))
                    
                    await db_session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
                    """))
                    
                    await db_session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active)
                    """))
                    
                    logger.info("Database tables created successfully")
                except Exception as sql_error:
                    logger.error(f"Failed to create tables with SQL: {sql_error}", exc_info=True)
                    # 如果失败，继续启动应用，因为表可能已经存在
        except Exception as table_error:
            logger.error(f"Failed to create database tables: {table_error}", exc_info=True)
            # 继续启动应用，因为表可能已经存在
            
        # 应用正常运行
        logger.info("Application startup complete")
        yield
        
    except Exception as e:
        logger.error(f"Error during application startup: {e}", exc_info=True)
        # 重新抛出异常，让FastAPI处理
        raise
    finally:
        # 确保在应用关闭时清理数据库资源
        try:
            logger.info("Cleaning up database resources...")
            await cleanup_database()
            logger.info("Database cleanup complete")
        except Exception as cleanup_error:
            logger.error(f"Error during database cleanup: {cleanup_error}", exc_info=True)


# 创建FastAPI应用
app = FastAPI(
    title="FastAPI Database Integration Example",
    description="示例API展示FastAPI与数据库抽象层集成",
    version="1.0.0",
    lifespan=lifespan
)


# 依赖注入函数
async def get_db_session():
    """提供数据库会话依赖"""
    try:
        async with session() as db_session:
            yield db_session
    except Exception as e:
        logger.error(f"Session error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session error"
        )


async def get_db_transaction():
    """提供事务管理依赖"""
    try:
        async with transaction() as db_session:
            yield db_session
    except Exception as e:
        logger.error(f"Transaction error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Database transaction error"
        )


# 新增添加：连接健康检查依赖
async def get_db_connection():
    """提供数据库连接依赖"""
    try:
        async with connection() as conn:
            yield conn
    except Exception as e:
        logger.error(f"Connection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )


# API路由
@app.get("/health")
async def health_check():
    """数据库健康检查端点"""
    db = get_database()
    is_healthy = await db.health_check()
    
    if not is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not healthy"
        )
    
    # 获取数据库统计信息
    stats = await db.get_stats()
    
    return {
        "status": "healthy",
        "database_stats": stats
    }


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate,
    db_session: AsyncSession = Depends(get_db_session)
):
    """创建新用户"""
    # 先检查用户是否已存在
    try:
        result = await db_session.execute(
            select(UserModel).where(
                (UserModel.email == user.email) | 
                (UserModel.username == user.username)
            )
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email or username already exists"
            )
    except HTTPException:
        # 直接传递HTTP异常
        raise
    except Exception as e:
        logger.error(f"Error checking existing user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    
    # 创建用户
    try:
        # 创建新用户
        user_id = uuid.uuid4()
        new_user = UserModel(
            id=user_id,
            email=user.email,
            username=user.username,
            is_active=user.is_active
        )
        
        # 添加到会话
        db_session.add(new_user)
        
        # 立即提交会话，不使用嵌套事务
        await db_session.commit()
        
        # 记录日志
        logger.info(f"Created new user with ID: {user_id}")
        
        # 返回用户数据
        return UserResponse(
            id=str(user_id),
            email=user.email,
            username=user.username,
            is_active=user.is_active
        )
    except Exception as e:
        # 如果创建用户过程中出错，回滚会话
        await db_session.rollback()
        logger.error(f"Failed to create user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@app.get("/users", response_model=List[UserResponse])
async def list_users(
    active_only: bool = False,
    session: AsyncSession = Depends(get_db_session)
):
    """获取用户列表"""
    query = select(UserModel)
    
    if active_only:
        query = query.where(UserModel.is_active == True)
    
    result = await session.execute(query)
    users = result.scalars().all()
    
    return [
        UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            is_active=user.is_active
        )
        for user in users
    ]


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_db_session)
):
    """获取指定用户"""
    user = await session.get(UserModel, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        is_active=user.is_active
    )


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db_session: AsyncSession = Depends(get_db_session)  # 使用普通会话而非事务
):
    """删除指定用户"""
    try:
        # 先检查用户是否存在
        user = await db_session.get(UserModel, user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found"
            )
        
        # 执行软删除
        user.is_active = False
        
        # 手动提交更改
        await db_session.commit()
        logger.info(f"Soft-deleted user with ID: {user_id}")
        
        # 204 No Content 响应
        return None
    except HTTPException:
        # 直接传递HTTP异常
        raise
    except Exception as e:
        # 如果出错，回滚会话
        await db_session.rollback()
        logger.error(f"Failed to delete user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@app.get("/connection-test")
async def connection_test(conn = Depends(get_db_connection)):
    """测试原始连接"""
    try:
        # 确保使用text()函数创建可执行的SQL文本
        result = await conn.execute(text("SELECT 1 AS test"))
        # 正确处理结果，fetchone()不需要await
        row = result.fetchone()
        if row:
            return {"connection_test": row[0], "success": True}
        else:
            return {"connection_test": None, "success": False, "message": "No result returned"}
    except Exception as e:
        logger.error(f"Connection test failed: {e}", exc_info=True)
        return {"connection_test": None, "success": False, "error": str(e)}


# 仅在直接运行时启动服务器
if __name__ == "__main__":
    # 配置uvicorn日志
    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    uvicorn_log_config["loggers"]["uvicorn"]["level"] = "INFO"
    
    # 启动服务器
    uvicorn.run(
        "integration_example:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=uvicorn_log_config
    ) 