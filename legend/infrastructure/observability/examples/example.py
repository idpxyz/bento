"""
可观测性模块使用示例
"""
import asyncio
import logging
import os
import random
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from idp.framework.infrastructure.observability.core import (
    ObservabilityConfig,
    SentryConfig,
    SpanKind,
    StandardMetrics,
    TracingConfig,
)
from idp.framework.infrastructure.observability.metrics import (
    MemoryMetricsRecorder,
    PrometheusRecorder,
)
from idp.framework.infrastructure.observability.metrics.factory import (
    MetricsRecorderFactory,
)
from idp.framework.infrastructure.observability.middleware import (
    MetricsMiddleware,
    RequestIdMiddleware,
    TracingMiddleware,
)
from idp.framework.infrastructure.observability.tracing import (
    MemoryTracer,
    SentryTracer,
    configure_sentry,
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 初始化可观测性配置 - 使用同步方式创建默认配置
obs_config = ObservabilityConfig(
    service_name="example-service",
    tracing=TracingConfig(
        enabled=True,
        sample_rate=1.0,
        sentry=SentryConfig(
            enabled=True,
            dsn=os.getenv("SENTRY_DSN")
        )
    )
)

# 手动强制设置Sentry DSN，确保Sentry可以正常工作
if not obs_config.tracing.sentry.dsn:
    logger.warning("No Sentry DSN found in config, setting it manually")
    obs_config.tracing.sentry.dsn = "https://a717fb1c8639f35bc78f4b60340ccc88@o4507072299991040.ingest.us.sentry.io/4507072302678016"
    obs_config.tracing.sentry.enabled = True

# 提高事务采样率以捕获更多性能数据（开发/测试环境）
if obs_config.env in ["dev", "test", "development"]:
    logger.info(f"Increasing Sentry traces sample rate for {obs_config.env} environment")
    obs_config.tracing.sentry.traces_sample_rate = 1.0  # 在非生产环境捕获所有事务

# 初始化指标记录器 - 使用单例模式
metrics_recorder = PrometheusRecorder.get_instance(
    service_name=obs_config.service_name,
    env=obs_config.env,
    prefix=obs_config.metrics.name_prefix,
    port=obs_config.metrics.prometheus_port
)

# 初始化内存指标记录器，用于比较和测试
memory_metrics_recorder = MemoryMetricsRecorder(
    prefix=obs_config.metrics.name_prefix,
    default_labels={"service": obs_config.service_name, "env": obs_config.env}
)

# 初始化追踪器
tracer: Union[MemoryTracer, SentryTracer]

# 检查是否配置了Sentry DSN
logger.info(f"Checking Sentry configuration: enabled={obs_config.tracing.sentry.enabled}, DSN={'configured' if obs_config.tracing.sentry.dsn else 'not configured'}")

if obs_config.tracing.sentry.enabled and obs_config.tracing.sentry.dsn:
    # 使用Sentry追踪器
    logger.info(f"Initializing Sentry with DSN and environment: {obs_config.env}")
    tracer = configure_sentry(obs_config.tracing, obs_config.env)
    logger.info("Using Sentry for distributed tracing and error monitoring")
else:
    # 使用内存追踪器
    logger.info(f"Sentry not used: enabled={obs_config.tracing.sentry.enabled}, DSN present={bool(obs_config.tracing.sentry.dsn)}")
    tracer = MemoryTracer(
        service_name=obs_config.service_name,
        sample_rate=obs_config.tracing.sample_rate
    )
    logger.info("Using in-memory tracer (Sentry integration disabled or DSN not provided)")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时异步加载配置
    try:
        logger.info("Loading configuration asynchronously during application startup")
        env_name = os.getenv("APP_ENV", "dev")
        config = await ObservabilityConfig.load_config(
            env_name=env_name, 
            service_name="example-service"
        )
        
        # 更新全局配置
        global obs_config
        obs_config = config
        logger.info(f"Configuration loaded from config system for environment: {env_name}")
    except Exception as e:
        logger.warning(f"Failed to load config from config system: {e}, using default configuration")
    
    # 启动时执行
    logger.info("=== Observability Configuration ===")
    logger.info(f"Service: {obs_config.service_name}")
    logger.info(f"Environment: {obs_config.env}")
    logger.info(f"Metrics enabled: {obs_config.metrics.enabled}")
    logger.info(f"Tracing enabled: {obs_config.tracing.enabled}")
    logger.info(f"Sentry enabled: {obs_config.tracing.sentry.enabled}")
    logger.info(f"Sentry DSN configured: {'Yes' if obs_config.tracing.sentry.dsn else 'No'}")
    logger.info(f"Sentry trace sampler: {obs_config.tracing.sentry.traces_sample_rate}")
    logger.info(f"Tracer type: {type(tracer).__name__}")
    logger.info("================================")
    
    logger.info("Starting metrics recorder periodic flush")
    await metrics_recorder.start_periodic_flush(interval=obs_config.flush_interval)
    await memory_metrics_recorder.start_periodic_flush(interval=obs_config.flush_interval)
    logger.info("Application started")
    
    yield  # 应用运行期间
    
    # 关闭时执行
    logger.info("Flushing metrics before shutdown")
    await metrics_recorder.flush()
    await memory_metrics_recorder.flush()
    logger.info("Application shutdown")

# 创建FastAPI应用
app = FastAPI(title="Observability Example", lifespan=lifespan)

# 安装中间件（注意顺序很重要）
RequestIdMiddleware.setup(app)
TracingMiddleware.setup(app, tracer=tracer)
MetricsMiddleware.setup(app, recorder=metrics_recorder)

# 注入追踪器的依赖
def get_tracer():
    """获取追踪器的依赖函数"""
    return tracer

# 注入指标记录器的依赖
def get_metrics_recorder():
    """获取指标记录器的依赖函数"""
    return metrics_recorder

# 注入内存指标记录器的依赖
def get_memory_metrics_recorder():
    """获取内存指标记录器的依赖函数"""
    return memory_metrics_recorder

# 定义API路由
@app.get("/")
async def root():
    """根路径处理器"""
    return {"message": "Hello from Observability Example"}

@app.get("/metrics/custom")
async def custom_metrics(
    recorder: PrometheusRecorder = Depends(get_metrics_recorder)
):
    """自定义指标查看"""
    # 模拟记录一些自定义指标
    await recorder.increment_counter(
        "example_counter",
        1.0,
        {"action": "custom_metrics_view"}
    )
    return {"metrics": "Check /metrics for Prometheus format"}

@app.get("/traces")
async def view_traces():
    """查看追踪数据"""
    if isinstance(tracer, MemoryTracer):
        stats = tracer.get_statistics()
        spans = [span.to_dict() for span in tracer.get_spans()]
        return {
            "statistics": stats,
            "spans": spans[:10]  # 只返回前10个以避免数据过大
        }
    else:
        return {
            "message": "Sentry tracer does not support in-memory traces viewing",
            "info": "Check your Sentry dashboard for traces and errors"
        }

@app.get("/db/{table_id}")
async def simulate_db_operation(
    table_id: int,
    recorder: PrometheusRecorder = Depends(get_metrics_recorder)
):
    """模拟数据库操作"""
    # 创建子span
    async with tracer.start_span(
        name=f"db_query_{table_id}",
        kind=SpanKind.CLIENT,
        attributes={"db.table": f"table_{table_id}"}
    ) as span:
        # 模拟数据库操作
        operation_time = random.uniform(0.01, 0.2)
        await asyncio.sleep(operation_time)
        
        # 记录指标
        await recorder.observe_histogram(
            StandardMetrics.DB_OPERATION_DURATION.name,
            operation_time,
            {"operation": "query", "table": f"table_{table_id}"}
        )
        
        # 50%概率模拟慢查询
        if random.random() < 0.5:
            slow_operation_time = random.uniform(0.3, 0.8)
            await asyncio.sleep(slow_operation_time)
            span.set_attribute("db.slow_query", True)
        
        # 10%概率模拟错误
        if random.random() < 0.1:
            error_msg = f"Simulated DB error for table {table_id}"
            span.record_exception(Exception(error_msg))
            
            await recorder.increment_counter(
                StandardMetrics.DB_ERRORS.name,
                1.0,
                {"operation": "query", "error_type": "db_error"}
            )
            
            raise HTTPException(status_code=500, detail=error_msg)
    
    return {
        "table_id": table_id,
        "operation": "query",
        "time_taken": operation_time,
        "timestamp": time.time()
    }

@app.get("/error")
async def simulate_error():
    """模拟错误"""
    if random.random() < 0.8:
        # 80%概率触发错误
        error_type = random.choice(["ValueError", "KeyError", "RuntimeError", "TypeError"])
        error_msg = f"Simulated {error_type} error"
        
        if error_type == "ValueError":
            raise ValueError(error_msg)
        elif error_type == "KeyError":
            raise KeyError(error_msg)
        elif error_type == "RuntimeError":
            raise RuntimeError(error_msg)
        else:
            raise TypeError(error_msg)
    
    return {"message": "You got lucky, no error this time!"}

# 添加专门的Sentry测试路由
@app.get("/sentry-test")
async def test_sentry(request: Request):
    """测试Sentry集成"""
    # 打印详细的Sentry配置信息
    logger.info(f"Sentry test requested from {request.client.host}")
    logger.info(f"Current Sentry config - enabled: {obs_config.tracing.sentry.enabled}, DSN: {'configured' if obs_config.tracing.sentry.dsn else 'not configured'}")
    logger.info(f"Tracer type: {type(tracer).__name__}")
    
    if not obs_config.tracing.sentry.enabled or not obs_config.tracing.sentry.dsn:
        logger.error("Sentry is not configured properly")
        return {
            "message": "Sentry not configured",
            "info": "Set SENTRY_DSN environment variable to enable Sentry integration",
            "debug": {
                "sentry_enabled": obs_config.tracing.sentry.enabled,
                "sentry_dsn_configured": bool(obs_config.tracing.sentry.dsn),
                "tracer_type": str(type(tracer).__name__)
            }
        }
    
    # 记录一条消息
    try:
        from sentry_sdk import capture_message
        logger.info("Sending test message to Sentry")
        capture_message("This is a test message from the API", level="info")
        logger.info("Sentry message sent successfully")
    except Exception as e:
        logger.error(f"Error sending message to Sentry: {e}")
        return {
            "message": "Error occurred while sending to Sentry",
            "error": str(e),
            "success": False
        }
    
    # 创建一个带上下文的span
    async with tracer.start_span(
        name="sentry_test",
        attributes={
            "test_id": str(uuid.uuid4()),
            "request_path": request.url.path,
            "client_ip": request.client.host if hasattr(request, "client") else "unknown"
        }
    ) as span:
        # 添加更多上下文
        span.set_attribute("user.id", "test-user-123")
        span.set_attribute("environment", obs_config.env)
        
        await asyncio.sleep(0.2)  # 模拟操作
        
        # 50%概率触发错误
        if random.random() < 0.5:
            try:
                # 模拟异常
                raise ValueError("This is a test error for Sentry")
            except Exception as e:
                span.record_exception(e)
                return {
                    "message": "Sent test error to Sentry",
                    "error": str(e),
                    "success": True
                }
    
    return {
        "message": "Sent test message to Sentry",
        "success": True
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.exception(f"Global exception: {exc}")
    
    # 尝试从请求状态中获取跟踪信息
    trace_id = getattr(request.state, "trace_id", "unknown")
    request_id = getattr(request.state, "request_id", "unknown")
    
    # 如果使用Sentry，确保异常被捕获
    if obs_config.tracing.sentry.enabled and obs_config.tracing.sentry.dsn:
        from sentry_sdk import capture_exception, set_context
        set_context("request_info", {
            "trace_id": trace_id,
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method
        })
        capture_exception(exc)
    
    return JSONResponse(
        status_code=500,
        content={
            "message": str(exc),
            "type": exc.__class__.__name__,
            "trace_id": trace_id,
            "request_id": request_id
        }
    )

# 添加一个基准测试路由
@app.get("/benchmark/{iterations}")
async def benchmark(
    iterations: int,
    recorder: PrometheusRecorder = Depends(get_metrics_recorder),
    tracer_instance: MemoryTracer = Depends(get_tracer)
):
    """执行基准测试
    
    Args:
        iterations: 迭代次数
        recorder: 指标记录器
        tracer_instance: 追踪器实例
    """
    if iterations > 1000:
        raise HTTPException(status_code=400, detail="Maximum iterations is 1000")
    
    start_time = time.time()
    results = []
    
    # 分批处理，每批10个
    batch_size = 10
    metrics_batch = []
    
    for i in range(iterations):
        # 记录每个迭代的指标
        metric_data = {
            "name": "benchmark_iteration",
            "type": "counter",
            "value": 1.0,
            "labels": {"iteration": str(i)}
        }
        metrics_batch.append(metric_data)
        
        # 每10个迭代批量处理一次
        if len(metrics_batch) >= batch_size or i == iterations - 1:
            await recorder.batch_record(metrics_batch)
            metrics_batch = []
        
        # 随机添加延迟
        await asyncio.sleep(random.uniform(0.001, 0.005))
        
        # 每5个迭代记录一个span
        if i % 5 == 0:
            async with tracer_instance.start_span(
                name=f"benchmark_iter_{i}",
                attributes={"iteration": i}
            ):
                await asyncio.sleep(0.001)
        
        results.append({"iteration": i, "timestamp": time.time()})
    
    # 记录总持续时间
    duration = time.time() - start_time
    await recorder.observe_histogram(
        "benchmark_duration_seconds",
        duration,
        {"iterations": str(iterations)}
    )
    
    return {
        "iterations": iterations,
        "duration_seconds": duration,
        "avg_iteration_ms": (duration * 1000) / iterations
    }

# 健康检查路由
@app.get("/health")
async def health_check(
    recorder: PrometheusRecorder = Depends(get_metrics_recorder)
):
    """健康检查"""
    is_metrics_healthy = await recorder.health_check()
    
    health_data = {
        "status": "healthy" if is_metrics_healthy else "unhealthy",
        "metrics": is_metrics_healthy,
        "timestamp": time.time()
    }
    
    if not is_metrics_healthy:
        return JSONResponse(
            status_code=503,
            content=health_data
        )
    
    return health_data

# 添加专门的Sentry功能展示路由组
@app.get("/sentry-examples", tags=["sentry"])
async def sentry_examples_index():
    """Sentry功能展示入口"""
    if not isinstance(tracer, SentryTracer):
        return {
            "message": "Sentry not configured - features not available",
            "info": "Configure Sentry DSN to enable these examples"
        }
    
    available_examples = [
        {"path": "/sentry-examples/user-context", "name": "User Context", "description": "设置用户上下文"},
        {"path": "/sentry-examples/breadcrumbs", "name": "Breadcrumbs", "description": "添加面包屑跟踪用户操作"},
        {"path": "/sentry-examples/custom-tags", "name": "Custom Tags", "description": "添加自定义标签"},
        {"path": "/sentry-examples/transaction", "name": "Performance Monitoring", "description": "性能监控"},
        {"path": "/sentry-examples/exceptions", "name": "Exception Handling", "description": "异常处理方式"},
        {"path": "/sentry-examples/attachments", "name": "Attachments", "description": "添加附件数据"},
        {"path": "/sentry-examples/contexts", "name": "Custom Contexts", "description": "添加自定义上下文"},
        {"path": "/sentry-examples/message", "name": "Custom Messages", "description": "发送自定义消息"}
    ]
    
    return {
        "message": "Sentry功能展示",
        "sentry_status": "enabled",
        "examples": available_examples
    }

@app.get("/sentry-examples/user-context", tags=["sentry"])
async def sentry_user_context(request: Request):
    """演示如何设置用户上下文"""
    if not isinstance(tracer, SentryTracer):
        return {"message": "Sentry not configured"}
    
    from sentry_sdk import set_user

    # 设置用户上下文
    user_id = f"user_{uuid.uuid4().hex[:8]}"
    set_user({
        "id": user_id,
        "email": f"{user_id}@example.com",
        "username": f"user_{user_id}",
        "ip_address": request.client.host,
        "subscription": "premium",
        "is_authenticated": True
    })
    
    # 生成一个事件来测试
    from sentry_sdk import capture_message
    capture_message("User context test", level="info")
    
    return {
        "message": "Sentry用户上下文已设置",
        "user_id": user_id,
        "info": "检查Sentry仪表板查看用户信息"
    }

@app.get("/sentry-examples/breadcrumbs", tags=["sentry"])
async def sentry_breadcrumbs():
    """演示如何添加面包屑"""
    if not isinstance(tracer, SentryTracer):
        return {"message": "Sentry not configured"}
    
    from sentry_sdk import add_breadcrumb, capture_message

    # 添加不同类型的面包屑
    add_breadcrumb(
        category="auth",
        message="用户登录",
        level="info",
        data={"login_method": "password"}
    )
    
    # 模拟用户导航
    add_breadcrumb(
        category="navigation",
        message="访问产品页面",
        level="info"
    )
    
    # 模拟API调用
    add_breadcrumb(
        category="api",
        message="获取产品详情",
        level="info",
        data={"product_id": "12345", "response_status": 200}
    )
    
    # 模拟用户操作
    add_breadcrumb(
        category="ui.click",
        message="点击'添加到购物车'按钮",
        level="info"
    )
    
    # 模拟一个警告
    add_breadcrumb(
        category="cart",
        message="产品库存不足",
        level="warning",
        data={"product_id": "12345", "available": 2, "requested": 5}
    )
    
    # 生成一个事件来测试
    capture_message("Breadcrumb test", level="info")
    
    return {
        "message": "Sentry面包屑已添加",
        "breadcrumbs": ["登录", "浏览产品", "API调用", "点击按钮", "库存警告"],
        "info": "检查Sentry仪表板查看面包屑"
    }

@app.get("/sentry-examples/custom-tags", tags=["sentry"])
async def sentry_custom_tags():
    """演示如何设置自定义标签"""
    if not isinstance(tracer, SentryTracer):
        return {"message": "Sentry not configured"}
    
    from sentry_sdk import capture_message, set_tag

    # 设置自定义标签
    set_tag("transaction_id", uuid.uuid4().hex)
    set_tag("feature_flag.dark_mode", "enabled")
    set_tag("ab_test", "variant_b")
    set_tag("deployment", "canary")
    set_tag("priority", "high")
    
    # 生成一个事件来测试
    capture_message("Custom tags test", level="info")
    
    return {
        "message": "Sentry自定义标签已设置",
        "tags": [
            "transaction_id", 
            "feature_flag.dark_mode", 
            "ab_test",
            "deployment",
            "priority"
        ],
        "info": "检查Sentry仪表板查看标签"
    }

@app.get("/sentry-examples/transaction", tags=["sentry"])
async def sentry_transaction():
    """演示如何创建性能监控交易"""
    if not isinstance(tracer, SentryTracer):
        return {"message": "Sentry not configured"}
    
    # 使用我们的追踪器API创建transaction
    async with tracer.start_span(
        name="complex_transaction",
        kind=SpanKind.SERVER,
        attributes={
            "transaction_type": "custom_example",
            "priority": "high"
        }
    ) as transaction:
        # 添加第一个子span
        async with tracer.start_span(
            name="data_fetching",
            kind=SpanKind.CLIENT,
            attributes={"data_source": "database"}
        ) as db_span:
            # 模拟数据库查询
            await asyncio.sleep(0.1)
            
            # 再添加一个嵌套span
            async with tracer.start_span(
                name="data_processing",
                kind=SpanKind.INTERNAL
            ):
                await asyncio.sleep(0.05)
        
        # 添加第二个子span - 模拟API调用
        async with tracer.start_span(
            name="api_request",
            kind=SpanKind.CLIENT,
            attributes={"api": "payment_service"}
        ) as api_span:
            # 模拟API延迟
            await asyncio.sleep(0.15)
            
            # 给span添加结果信息
            api_span.set_attribute("response.status", 200)
            api_span.set_attribute("response.size", 1240)
        
        # 给主transaction添加最终信息
        transaction.set_attribute("processed_items", 42)
        transaction.set_attribute("transaction.result", "success")
    
    return {
        "message": "Sentry性能监控交易已创建",
        "components": ["data_fetching", "data_processing", "api_request"],
        "info": "在Sentry Performance页面查看交易和span信息"
    }

@app.get("/sentry-examples/exceptions", tags=["sentry"])
async def sentry_exceptions(capture: bool = True):
    """演示不同的异常处理方式"""
    if not isinstance(tracer, SentryTracer):
        return {"message": "Sentry not configured"}
    
    from sentry_sdk import capture_exception, push_scope

    # 创建一些不同类型的异常
    exceptions = []
    
    try:
        # 模拟ValueError
        raise ValueError("这是一个示例值错误")
    except Exception as e:
        exceptions.append({"type": type(e).__name__, "message": str(e)})
        if capture:
            # 方法1: 直接捕获异常
            capture_exception(e)
    
    try:
        # 模拟自定义异常
        class CustomError(Exception):
            pass
        
        raise CustomError("这是一个自定义错误")
    except Exception as e:
        exceptions.append({"type": type(e).__name__, "message": str(e)})
        if capture:
            # 方法2: 使用scope添加额外信息
            with push_scope() as scope:
                scope.set_tag("error_origin", "custom_module")
                scope.set_extra("additional_info", "这个错误发生在处理自定义逻辑时")
                capture_exception(e)
    
    # 方法3: 在span上下文中记录异常
    async with tracer.start_span(name="exception_handling") as span:
        try:
            # 模拟KeyError
            data = {}
            result = data["non_existent_key"]
        except Exception as e:
            exceptions.append({"type": type(e).__name__, "message": str(e)})
            if capture:
                span.record_exception(e)
    
    return {
        "message": "Sentry异常处理示例",
        "exceptions": exceptions,
        "captured": capture,
        "info": "在Sentry Issues页面查看捕获的异常"
    }

@app.get("/sentry-examples/attachments", tags=["sentry"])
async def sentry_attachments():
    """演示如何添加附件和额外数据"""
    if not isinstance(tracer, SentryTracer):
        return {"message": "Sentry not configured"}
    
    from sentry_sdk import add_breadcrumb, capture_message, set_extra

    # 添加各种额外数据
    set_extra("server_name", "api-server-01")
    set_extra("deployment_id", "deploy-2023-04-21-001")
    
    # 添加复杂的结构化数据
    set_extra("request_data", {
        "headers": {
            "user-agent": "Example/1.0",
            "content-type": "application/json"
        },
        "body": {
            "id": 12345,
            "items": ["item1", "item2", "item3"]
        },
        "query_params": {
            "filter": "active",
            "sort": "date_desc"
        }
    })
    
    # 添加面包屑作为调试信息
    add_breadcrumb(
        category="debug",
        message="请求处理开始",
        level="debug",
        data={"timestamp": time.time()}
    )
    
    # 生成测试事件
    capture_message("Attachment test", level="info")
    
    return {
        "message": "Sentry附加数据已添加",
        "extras": ["server_name", "deployment_id", "request_data"],
        "info": "在Sentry事件详情中查看附加数据"
    }

@app.get("/sentry-examples/contexts", tags=["sentry"])
async def sentry_contexts():
    """演示如何添加自定义上下文"""
    if not isinstance(tracer, SentryTracer):
        return {"message": "Sentry not configured"}
    
    from sentry_sdk import capture_message, set_context

    # 添加设备上下文
    set_context("device", {
        "name": "API Server",
        "model": "Virtual Machine",
        "arch": "x86_64",
        "battery_level": 100,
        "charging": True,
        "online": True,
        "memory_size": 16_384_000_000,
        "free_memory": 7_584_000_000
    })
    
    # 添加操作系统上下文
    set_context("os", {
        "name": "Linux",
        "version": "Ubuntu 22.04 LTS",
        "build": "5.15.0-25-generic",
        "kernel_version": "5.15.0-25-generic"
    })
    
    # 添加应用上下文
    set_context("app", {
        "name": "Observability Example",
        "version": "1.0.0",
        "build": "2023042101",
        "start_time": time.time() - 3600,
        "app_memory": 256_000_000,
        "in_foreground": True
    })
    
    # 添加自定义业务上下文
    set_context("subscription", {
        "plan": "enterprise",
        "status": "active",
        "features": ["monitoring", "alerting", "dashboard", "api_access"],
        "limits": {
            "users": 100,
            "projects": 50,
            "api_calls_per_month": 1_000_000
        }
    })
    
    # 生成测试事件
    capture_message("Context test", level="info")
    
    return {
        "message": "Sentry上下文已添加",
        "contexts": ["device", "os", "app", "subscription"],
        "info": "在Sentry事件详情中查看上下文信息"
    }

@app.get("/sentry-examples/message", tags=["sentry"])
async def sentry_message(level: str = "info"):
    """演示如何发送自定义消息"""
    if not isinstance(tracer, SentryTracer):
        return {"message": "Sentry not configured"}
    
    from sentry_sdk import capture_message

    # 检查日志级别
    valid_levels = ["debug", "info", "warning", "error", "fatal"]
    if level not in valid_levels:
        return {"error": f"Invalid level. Must be one of: {', '.join(valid_levels)}"}
    
    # 为消息添加一些上下文
    from sentry_sdk import set_context, set_tag
    set_tag("message_type", "custom")
    set_tag("source", "api")
    
    set_context("message_context", {
        "timestamp": time.time(),
        "origin": "/sentry-examples/message",
        "level": level
    })
    
    # 添加一些面包屑
    from sentry_sdk import add_breadcrumb
    add_breadcrumb(
        category="message",
        message="准备发送消息",
        level="info"
    )
    
    # 发送消息
    message = f"这是一个{level}级别的测试消息 - {uuid.uuid4().hex[:8]}"
    capture_message(message, level=level)
    
    return {
        "message": "Sentry消息已发送",
        "level": level,
        "content": message,
        "info": "在Sentry Issues页面查看消息"
    }

# 添加一个更全面的示例，结合指标和跟踪
@app.get("/sentry-examples/full-monitoring", tags=["sentry"])
async def full_monitoring_example(
    service_type: str = "database",
    request: Request = None,
    recorder: PrometheusRecorder = Depends(get_metrics_recorder)
):
    """
    展示完整的监控示例，包括指标记录和分布式追踪
    
    此示例模拟一个完整的服务调用流程，包括：
    - 用户上下文设置
    - 服务间调用追踪
    - 性能指标记录
    - 错误处理和上报
    - 关键事件记录
    """
    # 支持的服务类型
    supported_services = ["database", "cache", "api", "queue"]
    if service_type not in supported_services:
        return {
            "error": f"不支持的服务类型，支持的类型: {', '.join(supported_services)}"
        }
    
    # 如果Sentry可用，设置用户上下文
    if isinstance(tracer, SentryTracer):
        from sentry_sdk import set_tag, set_user

        # 设置用户上下文
        user_id = f"test_user_{random.randint(1000, 9999)}"
        set_user({
            "id": user_id,
            "username": f"user_{user_id}",
            "ip_address": request.client.host if request else "127.0.0.1"
        })
        
        # 设置请求标签
        set_tag("service_type", service_type)
        set_tag("test_scenario", "full_monitoring")
    
    # 请求ID - 用于关联所有组件
    request_id = f"req_{uuid.uuid4().hex[:8]}"
    
    # 创建父级Span - 表示完整请求
    async with tracer.start_span(
        name=f"service_request.{service_type}",
        kind=SpanKind.SERVER,
        attributes={
            "request_id": request_id,
            "service.type": service_type
        }
    ) as parent_span:
        start_time = time.time()
        success = True
        error_details = None
        
        try:
            # 记录请求开始指标
            await recorder.increment_counter(
                StandardMetrics.SERVICE_REQUESTS_TOTAL.name,
                1.0,
                {"service": service_type, "operation": "request"}
            )
            
            # 根据服务类型模拟不同的处理流程
            if service_type == "database":
                # 数据库操作模拟
                async with tracer.start_span(
                    name="db.query",
                    kind=SpanKind.CLIENT,
                    attributes={"db.type": "postgresql", "db.operation": "select"}
                ) as db_span:
                    # 模拟数据库延迟
                    db_latency = random.uniform(0.05, 0.2)
                    await asyncio.sleep(db_latency)
                    
                    # 记录指标
                    await recorder.observe_histogram(
                        "db_operation_duration_seconds",
                        db_latency,
                        {"operation": "query", "db_type": "postgresql"}
                    )
                    
                    # 10%概率触发慢查询
                    if random.random() < 0.1:
                        slow_latency = random.uniform(0.8, 1.5)
                        await asyncio.sleep(slow_latency)
                        db_span.set_attribute("db.slow_query", True)
                        
                        await recorder.increment_counter(
                            "db_slow_queries_total",
                            1.0,
                            {"db_type": "postgresql"}
                        )
                    
                    # 5%概率触发错误
                    if random.random() < 0.05:
                        raise Exception("数据库连接错误: 连接池已满")
                
                # 添加处理结果
                parent_span.set_attribute("db.rows_returned", random.randint(1, 100))
                    
            elif service_type == "cache":
                # 缓存操作模拟
                async with tracer.start_span(
                    name="cache.get",
                    kind=SpanKind.CLIENT,
                    attributes={"cache.type": "redis", "cache.operation": "get"}
                ) as cache_span:
                    # 模拟缓存延迟
                    cache_latency = random.uniform(0.01, 0.05)
                    await asyncio.sleep(cache_latency)
                    
                    # 记录指标
                    await recorder.observe_histogram(
                        "cache_operation_duration_seconds",
                        cache_latency,
                        {"operation": "get", "cache_type": "redis"}
                    )
                    
                    # 模拟缓存命中/未命中
                    cache_hit = random.random() > 0.3
                    if cache_hit:
                        await recorder.increment_counter(
                            "cache_hits_total",
                            1.0,
                            {"cache_type": "redis"}
                        )
                        cache_span.set_attribute("cache.hit", True)
                    else:
                        await recorder.increment_counter(
                            "cache_misses_total",
                            1.0,
                            {"cache_type": "redis"}
                        )
                        cache_span.set_attribute("cache.hit", False)
                        
                        # 缓存未命中时，模拟从数据库获取
                        async with tracer.start_span(
                            name="db.query_after_cache_miss",
                            kind=SpanKind.CLIENT
                        ):
                            await asyncio.sleep(0.1)
                            
                            # 记录额外延迟
                            await recorder.observe_histogram(
                                "cache_miss_fallback_duration_seconds",
                                0.1,
                                {"fallback_type": "database"}
                            )
                
            elif service_type == "api":
                # 外部API请求模拟
                async with tracer.start_span(
                    name="http.request",
                    kind=SpanKind.CLIENT,
                    attributes={
                        "http.method": "GET",
                        "http.url": "https://api.example.com/data"
                    }
                ) as http_span:
                    # 模拟API请求延迟
                    http_latency = random.uniform(0.1, 0.4)
                    await asyncio.sleep(http_latency)
                    
                    # 记录指标
                    await recorder.observe_histogram(
                        "http_request_duration_seconds",
                        http_latency,
                        {"method": "GET", "external": "true"}
                    )
                    
                    # 设置响应结果
                    status_code = random.choices(
                        [200, 400, 500],
                        weights=[0.9, 0.05, 0.05],
                        k=1
                    )[0]
                    
                    http_span.set_attribute("http.status_code", status_code)
                    
                    # 对错误状态码进行处理
                    if status_code >= 400:
                        await recorder.increment_counter(
                            "http_errors_total",
                            1.0,
                            {"method": "GET", "status": str(status_code)}
                        )
                        
                        if status_code >= 500:
                            raise Exception(f"API服务器错误: {status_code}")
                        else:
                            parent_span.set_attribute("error", "Client error")
                
            elif service_type == "queue":
                # 消息队列操作模拟
                async with tracer.start_span(
                    name="queue.publish",
                    kind=SpanKind.PRODUCER,
                    attributes={
                        "messaging.system": "kafka",
                        "messaging.destination": "events-topic"
                    }
                ):
                    # 模拟消息发布延迟
                    msg_latency = random.uniform(0.02, 0.1)
                    await asyncio.sleep(msg_latency)
                    
                    # 记录指标
                    await recorder.observe_histogram(
                        "message_publish_duration_seconds",
                        msg_latency,
                        {"queue_type": "kafka", "topic": "events"}
                    )
                    
                    # 记录发送的消息数
                    await recorder.increment_counter(
                        "messages_published_total",
                        random.randint(1, 5),
                        {"topic": "events"}
                    )
                    
                    # 模拟消息处理
                    async with tracer.start_span(
                        name="queue.process",
                        kind=SpanKind.CONSUMER,
                        attributes={"messaging.operation": "process"}
                    ) as process_span:
                        process_time = random.uniform(0.05, 0.2)
                        await asyncio.sleep(process_time)
                        
                        # 记录处理延迟
                        await recorder.observe_histogram(
                            "message_processing_duration_seconds",
                            process_time,
                            {"queue_type": "kafka", "topic": "events"}
                        )
                        
                        # 8%概率处理失败
                        if random.random() < 0.08:
                            failed_count = random.randint(1, 3)
                            process_span.set_attribute("messaging.failures", failed_count)
                            
                            await recorder.increment_counter(
                                "message_processing_failures_total",
                                failed_count,
                                {"topic": "events", "reason": "processing_error"}
                            )
                            
                            raise Exception("消息处理错误: 无法解析消息格式")
                        
                        # 设置处理结果
                        process_span.set_attribute(
                            "messaging.processed_count", 
                            random.randint(1, 10)
                        )
            
        except Exception as e:
            # 记录异常
            success = False
            error_details = str(e)
            
            # 记录错误指标
            await recorder.increment_counter(
                StandardMetrics.SERVICE_ERRORS_TOTAL.name,
                1.0,
                {"service": service_type, "error_type": type(e).__name__}
            )
            
            # 记录错误到span
            parent_span.record_exception(e)
            parent_span.set_attribute("error", True)
            parent_span.set_attribute("error.type", type(e).__name__)
            parent_span.set_attribute("error.message", str(e))
        
        finally:
            # 计算总持续时间
            duration = time.time() - start_time
            
            # 记录总持续时间指标
            try:
                await recorder.observe_histogram(
                    StandardMetrics.SERVICE_OPERATION_DURATION.name,
                    duration,
                    {"service": service_type, "success": str(success).lower()}
                )
            except Exception as metric_error:
                logger.error(f"Failed to record service_operation_duration: {metric_error}")
            
            # 设置请求结果
            parent_span.set_attribute("request.duration", duration)
            parent_span.set_attribute("request.success", success)
    
    # 返回结果
    response = {
        "message": "完整监控示例已执行",
        "service_type": service_type,
        "request_id": request_id,
        "duration_seconds": time.time() - start_time,
        "success": success
    }
    
    if error_details:
        response["error"] = error_details
    
    return response

@app.get("/sentry-examples/sampling-test", tags=["sentry"])
async def test_sentry_sampling():
    """测试Sentry的智能采样功能
    
    这个端点将创建几个不同类型的事务，测试采样逻辑。
    - 关键交易：应始终被采样（采样率 100%）
    - 数据库操作：高采样率（50%）
    - 错误路径：高采样率（80%）
    - 健康检查：低采样率（1%）
    """
    if not isinstance(tracer, SentryTracer):
        return {"message": "Sentry not configured"}
    
    results = []
    
    # 测试 1: 关键 API 事务（应该有 100% 采样率）
    async with tracer.start_span(
        name="critical_operation", 
        kind=SpanKind.SERVER,
        attributes={"operation": "critical-test"}
    ) as span:
        span.set_attribute("test_type", "critical_sampling")
        span.set_attribute("expected_sample_rate", "100%")
        await asyncio.sleep(0.1)
        results.append({
            "test": "critical_operation",
            "span_id": span.span_id,
            "trace_id": span.trace_id
        })
    
    # 测试 2: 数据库操作（应该有 50% 采样率）
    async with tracer.start_span(
        name="db_query", 
        kind=SpanKind.CLIENT,
        attributes={"db.type": "postgres", "operation": "query"}
    ) as span:
        span.set_attribute("test_type", "database_sampling")
        span.set_attribute("expected_sample_rate", "50%")
        await asyncio.sleep(0.1)
        results.append({
            "test": "database_operation",
            "span_id": span.span_id,
            "trace_id": span.trace_id
        })
    
    # 测试 3: 错误路径（应该有 80% 采样率）
    async with tracer.start_span(
        name="error_handler", 
        kind=SpanKind.INTERNAL,
        attributes={"error_type": "test"}
    ) as span:
        span.set_attribute("test_type", "error_path_sampling")
        span.set_attribute("expected_sample_rate", "80%")
        await asyncio.sleep(0.1)
        results.append({
            "test": "error_handler",
            "span_id": span.span_id,
            "trace_id": span.trace_id
        })
    
    # 测试 4: 健康检查（应该有 1% 采样率）
    async with tracer.start_span(
        name="health_check", 
        kind=SpanKind.INTERNAL
    ) as span:
        span.set_attribute("test_type", "health_sampling")
        span.set_attribute("expected_sample_rate", "1%")
        await asyncio.sleep(0.1)
        results.append({
            "test": "health_check",
            "span_id": span.span_id,
            "trace_id": span.trace_id
        })
    
    # 返回测试结果
    return {
        "message": "智能采样测试完成",
        "note": "事务会根据采样配置被发送到Sentry",
        "transactions": results,
        "check_sentry": "查看Sentry Performance页面检查哪些事务被采样"
    }

@app.get("/metrics/memory")
async def memory_metrics(
    recorder: MemoryMetricsRecorder = Depends(get_memory_metrics_recorder)
):
    """内存指标查看"""
    # 模拟记录一些自定义指标
    await recorder.increment_counter(
        "memory_example_counter",
        1.0,
        {"action": "memory_metrics_view"}
    )
    
    # 获取内存中存储的指标摘要
    summary = recorder.get_metrics_summary()
    
    # 获取一些具体指标值的示例
    counter_values = {
        "memory_example_counter": recorder.get_counter_value("memory_example_counter", {"action": "memory_metrics_view"})
    }
    
    return {
        "summary": summary,
        "counter_values": counter_values,
        "message": "Memory metrics are stored in memory and can be queried directly via API"
    }

@app.get("/metrics/comparison")
async def metrics_comparison(
    prometheus_recorder: PrometheusRecorder = Depends(get_metrics_recorder),
    memory_recorder: MemoryMetricsRecorder = Depends(get_memory_metrics_recorder)
):
    """比较Prometheus和内存指标记录器"""
    metric_name = "comparison_test_counter"
    
    # 同时记录相同的指标到两个记录器
    await prometheus_recorder.increment_counter(metric_name, 1.0, {"source": "comparison_test"})
    await memory_recorder.increment_counter(metric_name, 1.0, {"source": "comparison_test"})
    
    # 从内存记录器获取数据
    memory_value = memory_recorder.get_counter_value(metric_name, {"source": "comparison_test"})
    
    return {
        "prometheus_info": {
            "type": "PrometheusRecorder",
            "port": obs_config.metrics.prometheus_port,
            "endpoint": f"http://localhost:{obs_config.metrics.prometheus_port}/metrics",
            "note": "Prometheus metrics are exposed via HTTP endpoint and cannot be directly queried via API"
        },
        "memory_info": {
            "type": "MemoryMetricsRecorder",
            "counter_value": memory_value,
            "note": "Memory metrics are stored in-memory and can be directly queried via API"
        },
        "guidance": "To see the difference: 1) Visit /metrics for Prometheus formatted metrics, 2) Compare with /metrics/memory for direct in-memory metrics"
    }

if __name__ == "__main__":
    # 直接运行时启动Uvicorn服务器
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port) 