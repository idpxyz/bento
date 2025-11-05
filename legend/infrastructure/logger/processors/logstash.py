"""Logstash处理器模块"""

import json
import logging
from typing import Any, Dict, Optional

import aiohttp
import structlog
from structlog.types import BindableLogger

from ..models import LogstashHandlerConfig
from .base import AsyncProcessor


class LogstashProcessor(AsyncProcessor[LogstashHandlerConfig]):
    """Logstash异步处理器
    
    Args:
        config: Logstash处理器配置
    """
    
    def __init__(self, config: LogstashHandlerConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._url = f"http://{config.host}:{config.port}"

    async def setup(self) -> None:
        """异步初始化"""
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )

    async def cleanup(self) -> None:
        """异步清理"""
        if self._session:
            await self._session.close()
            self._session = None

    async def process_event_async(self, logger: BindableLogger, method_name: str, event_dict: Dict[str, Any]) -> None:
        """异步处理日志事件"""
        if not self._session:
            return

        try:
            # 构建日志数据
            log_data = {
                "@timestamp": event_dict.get("timestamp", ""),
                "logger_name": logger.name,
                "level": method_name.upper(),
                "message": event_dict.get("event", "") or event_dict.get("message", ""),
                "data": event_dict
            }

            # 异步发送到Logstash
            async with self._session.post(
                self._url,
                json=log_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status >= 400:
                    print(f"Failed to send log to Logstash. Status: {response.status}")
                    
        except aiohttp.ClientError as e:
            print(f"Logstash connection error: {e}")
        except Exception as e:
            print(f"Unexpected error while sending log to Logstash: {e}")