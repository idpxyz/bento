"""应用入口
负责应用的启动和运行配置。
"""

import os
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI

from idp.framework.bootstrap.app import create_app
from idp.framework.bootstrap.component.setting.app import AppConfig
from idp.framework.infrastructure.logger import logger_manager
from idp.framework.infrastructure.utils.error import format_error_detail
from idp.framework.infrastructure.utils.network import find_available_port

logger = logger_manager.get_logger(__name__)


# 全局配置，用于开发模式的热重载
_env_name: str = "dev"
_config_dir: Optional[str] = None


async def app(scope, receive, send):
    """ASGI应用入口"""
    global _env_name, _config_dir
    config_path = _config_dir or str(Path(__file__).parent.parent / "config")
    app = await create_app(_env_name, config_path)
    await app(scope, receive, send)


def run_app(env_name: str, *, host: Optional[str] = None, port: Optional[int] = None, config_dir: Optional[str] = None) -> None:
    """运行FastAPI应用"""
    import asyncio

    try:
        # 1. 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # 2. 创建应用
            config_path = config_dir or str(
                Path(__file__).parent.parent / "config")
            app = loop.run_until_complete(create_app(env_name, config_path))
            settings: AppConfig = app.state.settings

            # 3. 配置运行参数
            host = host or settings.server_host
            port = port or settings.server_port

            if port and not find_available_port(port):
                alt_port = find_available_port(
                    start_port=port + 1, max_attempts=20)
                if alt_port:
                    logger.warning(f"⚠️ 端口 {port} 已被占用，使用端口: {alt_port}")
                    port = alt_port
                else:
                    raise RuntimeError(f"端口 {port} 已被占用且无可用端口")

            # 4. 运行服务器
            logger.info(f"\n🚀 启动服务器: http://{host}:{port}")

            if settings.debug:
                # 开发模式：使用reload
                module_path = Path(__file__).parent.parent.parent.parent
                if str(module_path) not in sys.path:
                    sys.path.insert(0, str(module_path))

                # 设置全局配置，供热重载使用
                global _env_name, _config_dir
                _env_name = env_name
                _config_dir = config_path

                uvicorn.run(
                    "idp.framework.bootstrap.main:app",
                    host=host,
                    port=port,
                    reload=True,
                    reload_dirs=[str(Path(__file__).parent.parent)],
                    workers=1,
                    log_level="info"
                )
            else:
                # 生产模式：直接运行
                uvicorn.run(
                    "idp.framework.bootstrap.main:app",
                    host=host,
                    port=port,
                    workers=settings.server_workers,
                    log_level="warning",
                    access_log=False
                )

        finally:
            loop.close()

    except Exception as e:
        error_detail = format_error_detail()
        logger.error(f"❌ 应用启动失败: {e}\n{error_detail}")
        sys.exit(1)




def main() -> None:
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="IDP应用启动工具")
    parser.add_argument("environment", choices=[
                        "dev", "test", "staging", "prod"], help="运行环境")
    parser.add_argument("--config-dir", help="配置目录路径")
    parser.add_argument("--port", type=int, help="服务端口号")
    parser.add_argument("--host", help="服务主机名")

    args = parser.parse_args()
    run_app(args.environment, host=args.host,
            port=args.port, config_dir=args.config_dir)


if __name__ == "__main__":
    main()
