"""应用定义
负责FastAPI应用的创建和配置。
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from idp.framework.api.demo import demo_router
from idp.framework.bootstrap.component.lifespan import lifespan
from idp.framework.bootstrap.component.setting.app import AppConfig, setup_app_config
from idp.framework.infrastructure.config.core.manager import config_manager
from idp.framework.infrastructure.logger import logger_manager
from idp.framework.infrastructure.utils.error import format_error_detail

logger = logger_manager.get_logger(__name__)

# 全局应用实例
_app: Optional[FastAPI] = None


def setup_cors(app: FastAPI, settings: AppConfig) -> None:
    """配置CORS中间件"""
    if settings.cors_enabled and not any(
        isinstance(middleware, CORSMiddleware)
        for middleware in app.user_middleware
    ):
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=settings.cors_credentials,
            allow_methods=settings.cors_methods,
            allow_headers=settings.cors_headers,
        )
        logger.debug(f"✅ CORS已启用 (允许来源: {settings.cors_origins})")


def setup_exception_handlers(app: FastAPI) -> None:
    """配置全局异常处理器"""
    from fastapi.responses import JSONResponse

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        """通用异常处理"""
        error_detail = format_error_detail()
        logger.error(f"❌ 异常发生:\n{error_detail}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "type": type(exc).__name__,
                "path": request.url.path
            }
        )


def setup_middleware(app: FastAPI, settings: AppConfig) -> None:
    """配置中间件"""
    # 配置CORS
    setup_cors(app, settings)

    # 未来可以添加更多中间件
    # setup_logging_middleware(app)
    # setup_security_middleware(app)


def setup_routers(app: FastAPI) -> None:
    """配置路由"""
    # 注册演示路由
    app.include_router(demo_router)

    # 未来可以注册更多路由
    # app.include_router(auth_router, prefix="/auth", tags=["认证"])
    # app.include_router(user_router, prefix="/users", tags=["用户"])


async def create_app(env_name: str, config_dir: Optional[str] = None) -> FastAPI:
    """创建FastAPI应用

    如果应用已经存在，则返回现有实例，否则创建新实例。

    Args:
        env_name: 环境名称
        config_dir: 配置目录路径

    Returns:
        FastAPI: 应用实例
    """
    global _app

    # 如果应用已存在，直接返回
    if _app is not None:
        return _app

    try:
        logger.info(f"🚀 初始化应用 (环境: {env_name})")

        # 1. 确定配置目录
        config_path = Path(config_dir) if config_dir else Path(
            __file__).parent.parent / "config"
        if not config_path.exists():
            raise FileNotFoundError(f"配置目录不存在: {config_path}")

        # 2. 始终加载 / 刷新应用配置
        app_settings = await setup_app_config(env_name=env_name, config_dir=str(config_path))

        logger.debug(f"👍 Loaded app config app_name = {app_settings.app_name}")

        # 3. 创建应用
        _app = FastAPI(
            title=app_settings.app_name,
            description=app_settings.description,
            version=app_settings.version,
            debug=app_settings.debug,
            docs_url=app_settings.docs_url,
            redoc_url=app_settings.redoc_url,
            openapi_url=app_settings.openapi_url,
            lifespan=lifespan
        )

        # 4. 配置应用
        _app.state.settings = app_settings
        _app.state.config_dir = str(config_path)  # 保存配置目录到应用状态
        setup_middleware(_app, app_settings)
        setup_exception_handlers(_app)
        setup_routers(_app)

        logger.info("✨ FastAPI应用创建成功")
        return _app

    except Exception as e:
        error_detail = format_error_detail()
        logger.error(f"❌ 创建应用失败: {e}\n{error_detail}")
        raise
