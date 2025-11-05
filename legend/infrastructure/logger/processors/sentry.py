"""Sentry处理器模块"""

from typing import Any, Dict

import structlog
from structlog.types import BindableLogger

from ..models import SentryHandlerConfig
from .base import AsyncProcessor


class SentryProcessor(AsyncProcessor[SentryHandlerConfig]):
    """Sentry处理器
    
    Args:
        config: Sentry处理器配置
    """
    
    def __init__(self, config: SentryHandlerConfig):
        super().__init__(config)
        self._initialized = False

    async def setup(self) -> None:
        """异步初始化"""
        import sentry_sdk
        sentry_sdk.init(
            dsn=self.config.dsn,
            environment=self.config.environment,
            traces_sample_rate=1.0,
        )
        self._initialized = True

    async def cleanup(self) -> None:
        """异步清理"""
        pass

    async def process_event_async(self, logger: BindableLogger, method_name: str, event_dict: Dict[str, Any]) -> None:
        """异步处理日志事件"""
        if self._initialized:
            import sentry_sdk

            # 提取错误信息
            message = event_dict.get("event", "") or event_dict.get("message", "")
            # 构建额外信息
            extras = {k: v for k, v in event_dict.items() if k not in ("event", "message")}
            
            # 发送到Sentry
            sentry_sdk.capture_message(
                message,
                level=method_name,
                extras=extras
            )