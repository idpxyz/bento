"""Kafka处理器模块"""

import json
from typing import Any, Dict

import structlog
from kafka import KafkaProducer
from kafka.errors import KafkaError
from structlog.types import BindableLogger

from ..models import KafkaHandlerConfig
from .base import AsyncProcessor


class KafkaProcessor(AsyncProcessor[KafkaHandlerConfig]):
    """Kafka异步处理器
    
    Args:
        config: Kafka处理器配置
    """
    
    def __init__(self, config: KafkaHandlerConfig):
        super().__init__(config)
        self._producer = None

    async def setup(self) -> None:
        """异步初始化"""
        self._producer = KafkaProducer(
            bootstrap_servers=self.config.bootstrap_servers,
            client_id=self.config.client_id,
            compression_type=self.config.compression_type,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=5,
            batch_size=self.config.batch_size * 1024,  # 批处理大小（字节）
            linger_ms=10,  # 延迟发送时间，允许更多消息批处理
            buffer_memory=32 * 1024 * 1024  # 缓冲区大小
        )

    async def cleanup(self) -> None:
        """异步清理"""
        if self._producer:
            self._producer.close()
            self._producer = None

    async def process_event_async(self, logger: BindableLogger, method_name: str, event_dict: Dict[str, Any]) -> None:
        """异步处理日志事件"""
        if not self._producer:
            return

        try:
            # 添加额外的元数据
            event_data = {
                **event_dict,
                "logger_name": logger.name,
                "log_level": method_name,
                "timestamp": event_dict.get("timestamp", "")
            }
            
            # 异步发送到Kafka
            future = self._producer.send(self.config.topic, event_data)
            
            # 可选：等待确认
            # record_metadata = await future.get(timeout=1.0)
            
        except KafkaError as e:
            print(f"Failed to send log to Kafka: {e}")
        except Exception as e:
            print(f"Unexpected error while sending log to Kafka: {e}")

    def __del__(self):
        """确保在对象销毁时关闭producer"""
        if self._producer:
            try:
                self._producer.close()
            except:
                pass