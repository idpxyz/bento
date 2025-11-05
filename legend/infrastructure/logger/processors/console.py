"""控制台处理器模块"""

import sys
from typing import Any, Dict, Optional

import structlog
from structlog.types import BindableLogger
from structlog.types import Processor as StructlogProcessor

from ..models import ConsoleHandlerConfig
from .base import AsyncProcessor


class ConsoleProcessor(AsyncProcessor[ConsoleHandlerConfig]):
    """异步控制台处理器

    Args:
        config: 控制台处理器配置
    """

    def __init__(self, config: ConsoleHandlerConfig):
        super().__init__(config)
        self._renderer = None

    async def setup(self) -> None:
        """异步初始化"""
        if self.config.format == "json":
            self._renderer = structlog.processors.JSONRenderer(
                ensure_ascii=False,  # 允许非ASCII字符（如中文）直接输出
                serializer=lambda obj, **kwargs: str(obj)  # 简单的序列化器
            )
        else:
            self._renderer = structlog.dev.ConsoleRenderer(
                colors=True,
                force_colors=True
            )

    async def cleanup(self) -> None:
        """异步清理"""
        pass

    async def process_event_async(self, logger: BindableLogger, method_name: str, event_dict: Dict[str, Any]) -> None:
        """异步处理日志事件"""
        if self._renderer:
            try:
                # 预处理事件字典，确保所有值都是字符串
                processed_dict = {
                    k: str(v) if not isinstance(
                        v, (str, int, float, bool)) else v
                    for k, v in event_dict.items()
                }
                # 使用渲染器格式化日志
                output = self._renderer(logger, method_name, processed_dict)
                # 使用 sys.stdout 直接写入并刷新
                sys.stdout.write(output + "\n")
                sys.stdout.flush()
            except Exception as e:
                # 如果输出失败，尝试使用 print
                print(f"Error in console processor: {e}")
                print(output)

    def get_renderer(self) -> Optional[StructlogProcessor]:
        """获取渲染器"""
        return self._renderer
