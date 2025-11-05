"""文件处理器模块"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import aiofiles
import structlog
from structlog.types import BindableLogger

from ..models import FileHandlerConfig
from .base import AsyncProcessor


class FileProcessor(AsyncProcessor[FileHandlerConfig]):
    """异步文件处理器

    Args:
        config: 文件处理器配置
    """

    def __init__(self, config: FileHandlerConfig):
        super().__init__(config)
        self._current_size = 0
        self._file = None
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(__name__)

    async def setup(self) -> None:
        """异步初始化"""
        try:
            # 确保日志目录存在
            log_path = Path(self.config.file_path).parent
            log_path.mkdir(parents=True, exist_ok=True)

            # 获取当前文件大小
            if Path(self.config.file_path).exists():
                self._current_size = Path(self.config.file_path).stat().st_size

            # 打开文件
            self._file = await aiofiles.open(self.config.file_path, mode='a', encoding='utf-8')

            # 写入一条标记消息，确保文件被创建
            await self._write_log({
                "timestamp": datetime.now().isoformat(),
                "message": "=== Logger initialized ===",
                "level": "INFO",
                "logger": "idp.framework.infrastructure.logger.setup"
            })

        except Exception as e:
            self._logger.error(f"Error in FileProcessor setup: {e}")
            # 如果文件打开失败，尝试使用标准同步方式创建文件
            try:
                with open(self.config.file_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "timestamp": datetime.now().isoformat(),
                        "message": "Fallback logger initialization",
                        "level": "INFO",
                        "logger": "idp.framework.infrastructure.logger.setup"
                    }) + "\n")
            except Exception:
                pass

    async def cleanup(self) -> None:
        """异步清理"""
        if self._file:
            try:
                # 写入一条关闭标记
                await self._write_log({
                    "timestamp": datetime.now().isoformat(),
                    "message": "=== Logger shutdown ===",
                    "level": "INFO",
                    "logger": "idp.framework.infrastructure.logger.setup"
                })

                # 关闭文件
                await self._file.close()
                self._file = None
            except Exception as e:
                self._logger.error(f"Error closing log file: {e}")
                # 强制关闭
                self._file = None

    async def _rotate_file(self) -> None:
        """异步文件轮转"""
        if self._file:
            await self._file.close()

        # 执行文件轮转
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for i in range(self.config.backup_count - 1, 0, -1):
            old_path = f"{self.config.file_path}.{i}"
            new_path = f"{self.config.file_path}.{i + 1}"
            if Path(old_path).exists():
                Path(old_path).rename(new_path)

        if Path(self.config.file_path).exists():
            Path(self.config.file_path).rename(
                f"{self.config.file_path}.{timestamp}")

        # 重新打开文件
        self._file = await aiofiles.open(self.config.file_path, mode='a', encoding='utf-8')
        self._current_size = 0

    async def _write_log(self, log_data: Dict[str, Any]) -> None:
        """写入日志数据"""
        if not self._file:
            return

        try:
            # 转换为JSON字符串
            log_line = json.dumps(log_data) + "\n"
            line_size = len(log_line.encode('utf-8'))

            async with self._lock:
                # 检查是否需要轮转
                if self._current_size + line_size > self.config.max_size:
                    await self._rotate_file()

                # 写入日志
                await self._file.write(log_line)
                await self._file.flush()
                os.fsync(self._file.fileno())
                self._current_size += line_size

        except Exception as e:
            self._logger.error(f"Error writing to log file: {e}")

    async def process_event_async(self, logger: BindableLogger, method_name: str, event_dict: Dict[str, Any]) -> None:
        """异步处理日志事件"""
        if not self._file:
            return

        try:
            # 构建日志数据
            log_data = {
                "timestamp": event_dict.get("timestamp", datetime.now().isoformat()),
                "logger": logger.name,
                "level": method_name.upper(),
                "message": event_dict.get("event", "") or event_dict.get("message", ""),
                **{k: v for k, v in event_dict.items() if k not in ["timestamp", "event", "message"]}
            }

            # 移除可能导致JSON序列化问题的字段
            if "exc_info" in log_data and not isinstance(log_data["exc_info"], str):
                log_data["exc_info"] = str(log_data["exc_info"])

            # 写入日志
            await self._write_log(log_data)

        except Exception as e:
            self._logger.error(f"Error processing log event: {e}")

    def __del__(self):
        """确保在对象销毁时关闭文件"""
        if hasattr(self, "_file") and self._file:
            # 在析构函数中不能使用异步操作，只能尝试同步关闭
            try:
                # 使用底层文件对象的close方法
                if hasattr(self._file, "_file") and self._file._file:
                    self._file._file.close()
            except:
                pass
