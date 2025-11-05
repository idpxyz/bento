"""Example FastAPI application demonstrating DDD and CQRS patterns."""

# Configure logging first, before any other imports
import asyncio
import logging

from idp.framework.examples.api import route_plan, stop
import uvicorn
from fastapi import FastAPI
from idp.framework.infrastructure.projection.projector import OutboxProjector
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from idp.framework.infrastructure.messaging.adapter.console_bus import ConsoleEventBus

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True  # Force configuration even if the root logger already has handlers
)

import idp.framework.infrastructure.persistence.sqlalchemy.interceptor.impl.outbox as oi  # noqa F401

logger = logging.getLogger(__name__)

# ----------------------------- 初始化 -----------------------------
logger.info("Checking outbox interceptor registration: %s",
            event.contains(Session, "after_flush", oi.persist_events))

app = FastAPI(
    title="IDP Framework Examples",
    description="IDP Framework 示例应用",
    version="0.1.0",
)
# app.webhooks = {
#     "tenant-default": {
#         "tenant-default-webhook": {
#             "url": "https://example.com/tenant-default-webhook",
#             "method": "POST",
#             "headers": {
#                 "Content-Type": "application/json"
#             }
#         }
#     }
# }

# 数据库配置
DB_DSN = "postgresql+asyncpg://postgres:thends@192.168.8.195:5432/mydb"

# 创建数据库引擎，优化连接池配置
engine = create_async_engine(
    DB_DSN,
    pool_size=20,  # 连接池大小
    max_overflow=10,  # 最大溢出连接数
    pool_timeout=30,  # 连接超时时间
    pool_recycle=1800,  # 连接回收时间（30分钟）
    pool_pre_ping=True,  # 连接前ping一下确保连接有效
    echo=False,  # 关闭SQL日志
)

# 创建会话工厂
session_factory = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,  # 关闭自动刷新
)

logger.info("Application initialized with database: %s", DB_DSN)

# ④ 在 app.state 上存储共享资源


@app.on_event("startup")
async def on_startup():
    # 挂载 SessionFactory 和 EventBus（ConsoleBus 只是示例）
    app.state.session_factory = session_factory
    app.state.event_bus = ConsoleEventBus()

    # 启动 Projector：每个租户一个实例（这里以 "default" 为例）
    projector = OutboxProjector(
        sf=app.state.session_factory,
        bus=app.state.event_bus,
        tenant_id="default",
        batch_size=100,
    )
    # 异步任务，不阻塞主线程
    asyncio.create_task(projector.run_forever())
    logger.info("OutboxProjector started for tenant=default")


app.include_router(stop.router)
app.include_router(route_plan.router)

# ----------------------------- 启动 -----------------------------
if __name__ == "__main__":
    logger.info("Starting server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
