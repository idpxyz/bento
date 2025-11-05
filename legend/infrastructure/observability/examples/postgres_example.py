#!/usr/bin/env python3
"""
PostgreSQL Metrics Recorder Example

This example demonstrates how to use the PostgreSQL metrics recorder with FastAPI.
It shows how to:
- Configure and initialize the PostgreSQL metrics recorder
- Record various types of metrics (counter, gauge, histogram, summary)
- Use middleware to automatically track HTTP requests
- View metrics in a dashboard endpoint

Prerequisites:
- PostgreSQL database with connection details configured in environment variables
- Setup the database schema using the postgres_schema.sql script

To run this example:
1. Set environment variables:
   - POSTGRES_DSN (e.g., "postgresql://user:password@localhost:5432/observability")
   - SERVICE_NAME (e.g., "example-service")
2. Install required packages: fastapi, uvicorn, asyncpg
3. Run with: uvicorn postgres_example:app --reload
"""

import asyncio
import logging
import os
import random
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from idp.framework.infrastructure.observability import (
    IMetricsRecorder,
    ITracer,
    MetricsConfig,
    ObservabilityConfig,
    PostgresCommonConfig,
    PostgresObservabilityConfig,
    Span,
    SpanKind,
    StandardMetrics,
    TracingConfig,
    create_observability,
)
from idp.framework.infrastructure.observability.core.metadata import MetricType
from idp.framework.infrastructure.observability.middleware import (
    MetricsMiddleware,
    RequestIdMiddleware,
    TracingMiddleware,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("postgres-example")

# 配置PostgreSQL连接
POSTGRES_CONNECTION = os.getenv(
    "POSTGRES_CONNECTION", 
    "postgresql://topsx:thends@192.168.8.137:5433/observability"
)
POSTGRES_SCHEMA = os.getenv("POSTGRES_SCHEMA", "observability")

# 创建可观测性配置
observability_config = ObservabilityConfig(
    env="dev",
    metrics=MetricsConfig(
        enabled=True,
        recorder_type="POSTGRES",
        service_name="idp-postgres-example",
        prefix="idp_example",
        aggregation_interval=10.0, 
    ),
    tracing=TracingConfig(
        enabled=True,
        service_name="idp-postgres-example",
        sample_rate=1.0,  # 开发环境采样率设为1.0以便调试
    ),
    postgres=PostgresObservabilityConfig(
        enabled=True,
        common=PostgresCommonConfig(
            connection=POSTGRES_CONNECTION,
            schema=POSTGRES_SCHEMA,
            retention_days=7,  # 开发环境保留数据时间较短
            batch_size=50,  # 开发环境批次大小较小
        ),
        metrics_table="example_metrics",
        metrics_metadata_table="example_metric_metadata",
        spans_table="example_spans",
        span_events_table="example_span_events",
        flush_interval=5.0,  # 更频繁的刷新以便于观察
    ),
)

# 全局可观测性组件
observability = None
metrics_recorder = None 
tracer = None

# 自定义指标定义
CUSTOM_COUNTER = {
    "name": "custom_operation_total",
    "help": "自定义操作计数器",
    "type": MetricType.COUNTER,
    "label_names": ["operation", "status"],
}

CUSTOM_HISTOGRAM = {
    "name": "custom_operation_duration",
    "help": "自定义操作耗时",
    "type": MetricType.HISTOGRAM,
    "unit": "seconds",
    "label_names": ["operation"],
    "buckets": [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
}

# 模拟数据库操作
async def simulate_db_operation(operation: str, trace_parent: Span = None) -> float:
    """模拟数据库操作，返回操作耗时"""
    # 使用上下文管理器创建子span
    async with tracer.start_span(
        name=f"db.{operation}",
        kind=SpanKind.CLIENT,
        attributes={
            "db.system": "postgresql", 
            "db.operation": operation,
            "db.name": "example_db"
        },
        parent=trace_parent,
    ) as span:
        # 模拟操作耗时
        duration = random.uniform(0.01, 0.2)
        await asyncio.sleep(duration)
        
        # 添加操作结果属性
        span.set_attribute("db.rows_affected", random.randint(1, 100))
        
        # 5%概率模拟错误
        if random.random() < 0.05:
            error = Exception(f"模拟的数据库错误: {operation}失败")
            span.record_exception(error)
            raise error
            
        return duration

# 批量记录指标函数
async def record_batch_metrics():
    """批量记录多个指标示例"""
    batch_metrics = []
    
    # 准备10条指标记录
    for i in range(10):
        operation = random.choice(["query", "insert", "update", "delete"])
        status = "success" if random.random() > 0.1 else "error"
        
        # 添加到批量记录列表
        batch_metrics.append({
            "name": CUSTOM_COUNTER["name"],
            "value": 1.0,
            "labels": {"operation": operation, "status": status}
        })
        
        # 添加直方图指标
        batch_metrics.append({
            "name": CUSTOM_HISTOGRAM["name"],
            "value": random.uniform(0.001, 0.5),
            "labels": {"operation": operation}
        })
    
    # 批量记录指标
    await metrics_recorder.batch_record(batch_metrics)
    logger.info(f"批量记录了 {len(batch_metrics)} 个指标")
    
    # 记录标准指标
    await metrics_recorder.set_gauge(
        StandardMetrics.METRICS_CACHE_SIZE.name,
        value=len(batch_metrics),
        labels={"source": "batch_example"}
    )

# FastAPI应用上下文管理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用生命周期，初始化和清理可观测性组件"""
    global observability, metrics_recorder, tracer
    
    # 初始化可观测性组件
    logger.info("初始化可观测性组件...")
    observability = create_observability(observability_config)
    await observability.initialize()
    
    # 获取指标记录器和追踪器
    metrics_recorder = observability.get_metrics_recorder()
    tracer = observability.get_tracer()
    
    # 安装中间件
    RequestIdMiddleware.setup(app)
    TracingMiddleware.setup(app, tracer=tracer)
    MetricsMiddleware.setup(app, get_recorder=lambda: metrics_recorder)
    
    # 注册自定义指标
    await metrics_recorder.register_metric(CUSTOM_COUNTER)
    await metrics_recorder.register_metric(CUSTOM_HISTOGRAM)
    
    # 启动后台任务
    background_task = asyncio.create_task(periodic_background_task())
    logger.info("可观测性组件初始化完成，后台任务已启动")
    
    yield
    
    # 清理资源
    logger.info("停止后台任务...")
    background_task.cancel()
    try:
        await background_task
    except asyncio.CancelledError:
        pass
    
    logger.info("清理可观测性组件...")
    await observability.cleanup()
    logger.info("应用关闭完成")

# 创建FastAPI应用
app = FastAPI(
    title="IDP可观测性框架 - PostgreSQL示例",
    description="演示使用PostgreSQL持久化的可观测性功能",
    version="1.0.0",
    lifespan=lifespan,
)

# 获取当前追踪Span的依赖项
def get_current_span(request: Request) -> Span:
    """获取当前请求的Span"""
    if tracer:
        return tracer.get_current_span()
    return None

# API路由 - 首页
@app.get("/")
async def read_root():
    return {
        "message": "IDP可观测性框架 - PostgreSQL持久化示例",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "API说明"},
            {"path": "/api/users", "method": "GET", "description": "模拟用户列表查询"},
            {"path": "/api/users/{user_id}", "method": "GET", "description": "模拟单个用户查询"},
            {"path": "/api/error", "method": "GET", "description": "模拟错误"},
            {"path": "/metrics/flush", "method": "POST", "description": "手动刷新指标"},
            {"path": "/health", "method": "GET", "description": "健康检查"},
        ]
    }

# API路由 - 用户列表
@app.get("/api/users")
async def get_users(
    limit: int = 10, 
    current_span: Span = Depends(get_current_span)
):
    """模拟获取用户列表"""
    # 记录自定义计数器指标
    await metrics_recorder.increment_counter(
        CUSTOM_COUNTER["name"],
        1.0,
        {"operation": "list_users", "status": "success"}
    )
    
    # 模拟数据库操作
    try:
        duration = await simulate_db_operation("query", current_span)
        
        # 记录操作耗时
        await metrics_recorder.observe_histogram(
            CUSTOM_HISTOGRAM["name"],
            duration,
            {"operation": "list_users"}
        )
        
        # 生成模拟用户数据
        users = [
            {"id": i, "name": f"User {i}", "email": f"user{i}@example.com"}
            for i in range(1, limit + 1)
        ]
        
        return {"users": users, "count": len(users)}
    except Exception as e:
        # 记录错误指标
        await metrics_recorder.increment_counter(
            CUSTOM_COUNTER["name"],
            1.0,
            {"operation": "list_users", "status": "error"}
        )
        raise HTTPException(status_code=500, detail=str(e))

# API路由 - 单个用户
@app.get("/api/users/{user_id}")
async def get_user(
    user_id: int, 
    request_id: str = Header(None, alias="X-Request-ID"),
    current_span: Span = Depends(get_current_span)
):
    """模拟获取单个用户"""
    # 添加额外的追踪信息
    if current_span:
        current_span.set_attribute("user.id", str(user_id))
        current_span.set_attribute("request.id", request_id or "unknown")
    
    try:
        # 模拟数据库操作
        duration = await simulate_db_operation("get", current_span)
        
        # 记录操作耗时
        await metrics_recorder.observe_histogram(
            CUSTOM_HISTOGRAM["name"],
            duration,
            {"operation": "get_user"}
        )
        
        # 生成模拟用户数据
        user = {"id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@example.com"}
        
        # 记录成功指标
        await metrics_recorder.increment_counter(
            CUSTOM_COUNTER["name"],
            1.0,
            {"operation": "get_user", "status": "success"}
        )
        
        return user
    except Exception as e:
        # 记录错误指标
        await metrics_recorder.increment_counter(
            CUSTOM_COUNTER["name"],
            1.0,
            {"operation": "get_user", "status": "error"}
        )
        if current_span:
            current_span.record_exception(e)
        raise HTTPException(status_code=500, detail=str(e))

# API路由 - 模拟错误
@app.get("/api/error")
async def get_error():
    """模拟产生错误的端点"""
    # 创建一个子追踪
    async with tracer.start_span(
        name="error.example",
        kind=SpanKind.INTERNAL,
        attributes={"error.type": "example"}
    ) as span:
        # 构造错误信息
        error_id = str(uuid.uuid4())
        error_message = f"示例错误 (ID: {error_id})"
        
        # 记录错误指标
        await metrics_recorder.increment_counter(
            CUSTOM_COUNTER["name"], 
            1.0,
            {"operation": "simulate_error", "status": "error"}
        )
        
        # 记录错误到追踪
        error = ValueError(error_message)
        span.record_exception(error)
        span.set_attribute("error.id", error_id)
        
        # 构造并抛出HTTP异常
        raise HTTPException(status_code=500, detail={
            "message": error_message,
            "error_id": error_id,
            "timestamp": time.time()
        })

# API路由 - 手动刷新指标
@app.post("/metrics/flush")
async def flush_metrics():
    """手动刷新指标到存储"""
    if metrics_recorder:
        start_time = time.time()
        await metrics_recorder.flush()
        duration = time.time() - start_time
        return {
            "success": True,
            "message": "指标已刷新到PostgreSQL",
            "duration_seconds": duration
        }
    return {"success": False, "message": "指标记录器未初始化"}

# API路由 - 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    result = {
        "status": "healthy",
        "components": {},
        "timestamp": time.time()
    }
    
    # 检查指标记录器
    if metrics_recorder:
        try:
            metrics_health = await metrics_recorder.health_check()
            result["components"]["metrics"] = {
                "status": "healthy" if metrics_health else "unhealthy",
                "details": metrics_health
            }
        except Exception as e:
            result["components"]["metrics"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            result["status"] = "degraded"
    else:
        result["components"]["metrics"] = {"status": "not_initialized"}
        result["status"] = "degraded"
    
    # 检查追踪器
    if tracer:
        try:
            # 确保当前追踪器正常工作
            async with tracer.start_span("health.check") as span:
                span.set_attribute("check.time", time.time())
            result["components"]["tracing"] = {"status": "healthy"}
        except Exception as e:
            result["components"]["tracing"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            result["status"] = "degraded"
    else:
        result["components"]["tracing"] = {"status": "not_initialized"}
        result["status"] = "degraded"
    
    # 设置HTTP状态码
    return result

# 后台任务: 定期记录批量指标
async def periodic_background_task():
    """后台任务：定期记录批量指标和执行健康检查"""
    while True:
        try:
            # 批量记录指标
            await record_batch_metrics()
            
            # 执行健康检查
            health_status = await metrics_recorder.health_check()
            logger.info(f"健康检查状态: {health_status}")
            
            # 等待下一个间隔
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"后台任务出错: {e}", exc_info=True)
            # 出错后等待一段时间再继续
            await asyncio.sleep(5)

# 主函数
if __name__ == "__main__":
    uvicorn.run(
        "postgres_example:app", 
        host="0.0.0.0", 
        port=8000,
        reload=False  # 禁用自动重载以避免多次初始化
    ) 