"""数据库模块

提供数据库的生命周期管理功能，包括初始化、健康检查和清理。
使用数据库门面类管理数据库实例。
"""

import asyncio
import os
from datetime import UTC, datetime
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import Depends, FastAPI, Request
from sqlalchemy.ext.asyncio import AsyncSession

from idp.framework.bootstrap.component.setting.database import setup_database_config
from idp.framework.exception.classified import InfrastructureException
from idp.framework.exception.code.database import DatabaseErrorCode
from idp.framework.infrastructure.db import (
    Database,
    cleanup_database,
    get_database,
    initialize_database,
)
from idp.framework.infrastructure.db.config import DatabaseConfig
from idp.framework.infrastructure.logger import logger_manager

logger = logger_manager.get_logger(__name__)


async def db_setup(
        app: FastAPI,
        env_name: Optional[str] = None,
        config_dir: Optional[str] = None
) -> None:
    """初始化数据库

    Args:
        app: FastAPI 应用实例
        env_name: 环境名称，用于获取特定环境的配置
        config_dir: 配置目录路径，用于加载指定目录下的配置
    """
    try:
        env = env_name or os.environ.get("ENV", "dev")
        logger.info(f"🚀 初始化数据库 (环境: {env})")

        # 1. 初始化数据库配置
        db_config: DatabaseConfig = await setup_database_config(env_name=env, config_dir=config_dir)

        # 2. 初始化数据库实例
        logger.debug(f"正在创建数据库实例: {db_config.connection.database}")

        # 确保清理任何现有的数据库实例
        await cleanup_database()

        # 初始化新的数据库实例
        db = await initialize_database(db_config)

        # 确保数据库实例已正确初始化
        if not db or not db.is_initialized:
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_INITIALIZATION_ERROR,
                details={"message": "Failed to initialize database instance"}
            )

        # 3. 预热连接池
        logger.debug("正在预热数据库连接池...")
        async with asyncio.timeout(db_config.pool.timeout):
            is_healthy = await db.health_check()
            if not is_healthy:
                raise InfrastructureException(
                    code=DatabaseErrorCode.DATABASE_CONNECTION_ERROR,
                    details={"message": "Database health check failed"}
                )
            logger.info("✅ 数据库连接池预热成功")

        # 4. 设置数据库实例到应用状态
        app.state.db = db
        logger.info("✅ 已设置数据库实例到应用状态")

        # 5. 验证全局实例
        try:
            global_db = get_database()
            if global_db is not db:
                raise InfrastructureException(
                    code=DatabaseErrorCode.DATABASE_INITIALIZATION_ERROR,
                    details={"message": "Global database instance mismatch"}
                )
        except Exception as e:
            raise InfrastructureException(
                code=DatabaseErrorCode.DATABASE_INITIALIZATION_ERROR,
                details={
                    "message": f"Failed to verify global database instance: {str(e)}"},
                cause=e
            )

    except InfrastructureException:
        # 这些是已经格式化好的错误，直接抛出
        await cleanup_database()
        raise
    except Exception as e:
        # 其他未预期的错误
        await cleanup_database()
        raise InfrastructureException(
            code=DatabaseErrorCode.DATABASE_INITIALIZATION_ERROR,
            details={"message": str(e)},
            cause=e
        )


async def get_db(request: Request) -> Database:
    """获取数据库实例

    Args:
        request: FastAPI 请求对象

    Returns:
        Database: 数据库实例

    Raises:
        HTTPException: 当数据库实例不可用时
    """
    db = getattr(request.app.state, "db", None)
    if db is None:
        logger.error("数据库实例未初始化")
        raise InfrastructureException(
            code=DatabaseErrorCode.DATABASE_NOT_INITIALIZED,
            details={"message": "数据库实例未初始化"}
        )
    return db


async def get_read_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """获取只读数据库会话

    用于读写分离场景，自动获取读库连接。
    如果未配置读写分离或读库不可用，则返回主库连接。

    Args:
        request: FastAPI 请求对象

    Returns:
        AsyncGenerator[AsyncSession, None]: 只读数据库会话生成器
    """
    db = await get_db(request)  # 使用 get_db 确保数据库实例存在
    async with db.read_replica() as session:
        yield session


async def get_db_stats() -> Dict[str, Any]:
    """获取数据库统计信息

    Returns:
        Dict[str, Any]: 数据库统计信息，包含以下字段：
            - status: 数据库状态 ("healthy", "unhealthy", "uninitialized")
            - initialized: 是否已初始化
            - type: 数据库类型
            - database: 数据库名称
            - stats: 数据库统计信息
            - error: 错误信息（如果有）
            - last_check: 最后检查时间
    """
    try:
        # 获取数据库实例
        db = get_database()
        if not db or not db.is_initialized:
            return {
                "status": "uninitialized",
                "initialized": False,
                "error": "Database not initialized or initialization incomplete. Please check if the application startup process completed successfully.",
                "last_check": datetime.now(UTC).isoformat()
            }

        # 获取数据库统计信息
        stats = await db.get_stats()
        is_healthy = await db.health_check()

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "initialized": True,
            "type": db.config.type.value,
            "database": db.config.connection.database,
            "stats": stats,
            "last_check": datetime.now(UTC).isoformat()
        }

    except Exception as e:
        logger.error(f"❌ 获取数据库统计信息失败: {e}")
        return {
            "status": "error",
            "initialized": False,
            "error": str(e),
            "last_check": datetime.now(UTC).isoformat()
        }
