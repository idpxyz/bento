"""
Schema 注册监控 API 应用

该应用提供 Schema 注册监控的 API 接口和可视化界面
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse

from idp.framework.infrastructure.logger.context import LogContext
from idp.framework.infrastructure.logger.manager import logger_manager
from idp.framework.infrastructure.schema.monitor.schema_monitor import SchemaMonitor

from .routes import router

# 配置日志
log_manager = logger_manager
logger = logging.getLogger("schema-monitor-api")

# 配置模板和静态文件目录
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

# 创建模板引擎
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用程序生命周期管理器
    
    负责应用启动时的初始化和关闭时的资源清理
    """
    # 启动时
    logger.info("Schema监控API服务启动")
    # 记录应用程序配置信息
    log_context = LogContext(
        service="schema-monitor-api",
        component="api",
        action="startup"
    )
    log_manager.info("API服务启动", extra=log_context.as_dict())
    
    yield
    
    # 关闭时
    logger.info("Schema监控API服务关闭")
    log_context.action = "shutdown"
    log_manager.info("API服务关闭", extra=log_context.as_dict())

def create_app() -> FastAPI:
    """创建 FastAPI 应用实例"""
    
    app = FastAPI(
        title="Schema Monitor API",
        description="Schema 注册监控 API",
        version="1.0.0",
        docs_url="/schema-monitor/docs",
        redoc_url="/schema-monitor/redoc",
        openapi_url="/schema-monitor/openapi.json",
        lifespan=lifespan
    )
    
    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 挂载静态文件目录
    app.mount("/schema-monitor/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    
    # 创建 Schema 监控器实例
    monitor = SchemaMonitor()
    
    @app.get("/schema-monitor/", response_class=HTMLResponse)
    async def index(request: Request):
        """渲染监控页面"""
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "static_url": "/schema-monitor/static"
            }
        )
    
    @app.get("/schema-monitor/health")
    async def get_health():
        """获取健康状态"""
        result = await monitor.check_schema_health()
        return result.dict()
    
    @app.get("/schema-monitor/metrics")
    async def get_metrics():
        """获取监控指标"""
        metrics = monitor.metrics_collector.load_metrics(days=7)
        return [metric.dict() for metric in metrics]
    
    @app.get("/schema-monitor/registry")
    async def get_registry():
        """获取注册表信息"""
        registry = monitor.load_registry()
        return registry.dict()
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """全局异常处理"""
        error_id = LogContext.current.error_id
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "error_id": error_id
            }
        )
    
    return app


def start_app(host: str = "0.0.0.0", 
              port: int = 8000, 
              reload: bool = False,
              debug: bool = False) -> None:
    """启动应用服务"""
    app = create_app()
    
    # 配置日志
    log_level = "debug" if debug else "info"
    
    # 打印启动信息
    startup_msg = f"Schema监控API服务启动于 http://{host}:{port}"
    logger.info(startup_msg)
    print(f"\n{'-' * len(startup_msg)}")
    print(startup_msg)
    print(f"{'-' * len(startup_msg)}\n")
    
    # 启动服务
    uvicorn.run(
        "idp.framework.api.schema.app:create_app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        factory=True
    )


if __name__ == "__main__":
    # 从环境变量获取配置
    host = os.environ.get("SCHEMA_API_HOST", "0.0.0.0")
    port = int(os.environ.get("SCHEMA_API_PORT", "8000"))
    debug = os.environ.get("SCHEMA_API_DEBUG", "0") in ("1", "true", "yes")
    reload = os.environ.get("SCHEMA_API_RELOAD", "0") in ("1", "true", "yes")
    
    # 启动服务
    start_app(host=host, port=port, reload=reload, debug=debug) 