"""API 演示路由

包含基本的 API 示例，展示如何：
1. 创建路由
2. 使用请求上下文
3. 访问应用配置
4. 获取系统状态
"""

from datetime import UTC, datetime
from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import Row
from sqlalchemy.exc import SQLAlchemyError

from idp.framework.bootstrap.component.db_setup import get_db, get_db_stats
from idp.framework.bootstrap.component.lifespan import lifespan_manager
from idp.framework.bootstrap.component.setting.app import AppConfig
from idp.framework.infrastructure.db.database import Database
from idp.framework.infrastructure.logger import logger_manager

logger = logger_manager.get_logger(__name__)

router = APIRouter(
    prefix="/demo",
    tags=["演示"]
)

# 定义数据库依赖
DBDependency = Annotated[Database, Depends(get_db)]


def row_to_dict(row: Row) -> Dict[str, Any]:
    """将 SQLAlchemy Row 对象转换为字典

    Args:
        row: SQLAlchemy Row 对象

    Returns:
        Dict[str, Any]: 转换后的字典
    """
    return {key: getattr(row, key) for key in row._fields} if row._fields else {}


@router.get("/")
async def root(request: Request):
    """演示路由根路径

    展示如何：
    1. 获取请求上下文
    2. 访问应用配置
    """
    settings: AppConfig = request.app.state.settings
    return {
        "message": "API 演示",
        "app_info": {
            "name": settings.app_name,
            "environment": settings.env,
            "version": settings.version
        },
        "request_info": {
            "client": request.client,
            "method": request.method,
            "url": str(request.url)
        }
    }


@router.get("/health")
async def health(request: Request):
    """健康检查演示

    展示如何：
    1. 获取系统组件状态
    2. 格式化响应数据
    """
    health_status = await lifespan_manager.get_health_status()
    return {
        "status": "healthy" if all(c["status"] == "healthy" for c in health_status["components"].values()) else "degraded",
        "environment": request.app.state.settings.env,
        "components": health_status["components"],
        "timestamp": datetime.now(UTC).isoformat()
    }


@router.get("/database")
async def database_stats():
    """数据库状态演示

    展示如何：
    1. 获取数据库统计信息
    2. 异步函数的使用
    """
    try:
        stats = await get_db_stats()
        return {
            "message": "数据库统计演示",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "DATABASE_STATS_ERROR",
                "message": "Failed to get database statistics",
                "error": str(e)
            }
        )


@router.get("/database/test")
async def database_test(db: DBDependency):
    """数据库测试演示

    展示如何：
    1. 测试数据库连接
    2. 处理数据库错误
    3. 读写分离
    """
    try:
        # 1. 写入测试（使用主数据库）
        write_data = await _perform_write_test(db)

        # 2. 读取测试（使用只读副本）
        read_data, read_db_info = await _perform_read_test(db)

        # 3. 准备响应数据
        response_data = {
            "message": "数据库读写测试成功",
            "write_result": write_data,
            "read_result": read_data,
            "timestamp": datetime.now(UTC).isoformat(),
            "status": "success",
            "database_info": {
                "type": db.config.type.value,
                "read_write_split": db.config.read_write.enable_read_write_split,
                "read_replicas_count": len(db.config.read_write.read_replicas),
                "write_database": {
                    "host": db.config.connection.host,
                    "port": db.config.connection.port,
                    "database": db.config.connection.database
                }
            }
        }

        # 添加读库信息到响应中（如果有）
        if read_db_info:
            response_data["database_info"]["read_database"] = read_db_info

        return response_data

    except SQLAlchemyError as e:
        error_msg = str(e)
        logger.error("Database query error: %s", error_msg)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "DATABASE_QUERY_ERROR",
                "message": "Database query failed",
                "error": error_msg,
                "status": "error"
            }
        )
    except Exception as e:
        error_msg = str(e)
        logger.error("Unexpected database error: %s", error_msg)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "DATABASE_ERROR",
                "message": "Internal database error",
                "error": error_msg,
                "status": "error"
            }
        )


async def _perform_write_test(db: Database) -> Dict[str, Any]:
    """执行写入测试

    Args:
        db: 数据库实例

    Returns:
        Dict[str, Any]: 写入结果
    """
    logger.info(
        "Write operation using main database: host=%s, port=%s, database=%s",
        db.config.connection.host,
        db.config.connection.port,
        db.config.connection.database
    )

    async with db.get_session() as write_session:
        try:
            insert_statement = text("""
                INSERT INTO test_table (name, created_at) 
                VALUES (:name, CURRENT_TIMESTAMP) 
                RETURNING id, name, created_at
            """)
            write_result = await write_session.execute(insert_statement, {"name": "test"})
            inserted_row = write_result.fetchone()
            await write_session.commit()

            logger.info(
                "Write operation successful: inserted_id=%s",
                getattr(inserted_row, 'id', None)
            )

            return {
                "id": getattr(inserted_row, 'id', None),
                "name": getattr(inserted_row, 'name', None),
                "created_at": getattr(inserted_row, 'created_at', None)
            } if inserted_row else None

        except Exception as e:
            await write_session.rollback()
            logger.error("Write operation failed: %s", str(e))
            raise


async def _perform_read_test(db: Database) -> tuple[list[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """执行读取测试

    Args:
        db: 数据库实例

    Returns:
        tuple[list[Dict[str, Any]], Optional[Dict[str, Any]]]: 读取结果和数据库信息
    """
    read_statement = text("""
        SELECT id, name, created_at 
        FROM test_table 
        ORDER BY created_at DESC 
        LIMIT :limit
    """)

    is_read_write_enabled = db.config.read_write.enable_read_write_split
    read_replicas = db.config.read_write.read_replicas
    read_db_info = None
    read_rows = []

    try:
        # 使用异步上下文管理器获取只读会话
        async with db.get_read_session() as read_session:
            # 获取当前会话的连接信息
            connection = read_session.get_bind()
            if hasattr(connection, 'get_connection_info'):
                connection_info = connection.get_connection_info()

                if connection_info:
                    read_db_info = {
                        "host": connection_info.host,
                        "port": connection_info.port,
                        "database": connection_info.database,
                        "is_replica": connection_info.is_replica
                    }
                    logger.info(
                        "Read operation using %(type)s: host=%(host)s, port=%(port)s, database=%(database)s",
                        {
                            "type": "replica" if connection_info.is_replica else "main database",
                            **read_db_info
                        }
                    )
            else:
                logger.info(
                    "Using database for read operation (read_write_split=%s, replicas_count=%d)",
                    is_read_write_enabled,
                    len(read_replicas)
                )

            result = await read_session.execute(read_statement, {"limit": 15})
            read_rows = result.fetchall()
            logger.info(
                "Read operation successful: fetched %d rows", len(read_rows))

    except Exception as e:
        logger.error("Read operation failed: %s", str(e))
        raise

    return [
        {
            "id": getattr(row, 'id', None),
            "name": getattr(row, 'name', None),
            "created_at": getattr(row, 'created_at', None)
        }
        for row in read_rows
    ], read_db_info
