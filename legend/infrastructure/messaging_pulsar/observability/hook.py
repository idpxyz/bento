import logging
import time
from typing import Callable

from ..core.base_message import MessageEnvelope

logger = logging.getLogger("messaging")

def default_handler_observer(event_type: str, correlation_id: str, success: bool, duration: float, error: str = None):
    status = "success" if success else "error"
    logger.info(f"[{status.upper()}] event={event_type}, trace={correlation_id}, duration={duration:.2f}s, error={error or '-'}")


_observer: Callable = default_handler_observer

def set_observer(observer: Callable):
    """
    注册外部可观测钩子（如 Prometheus、Sentry 集成）
    """
    global _observer
    _observer = observer

def report_event(event: MessageEnvelope, success: bool, start_time: float, error: str = None):
    duration = time.time() - start_time
    _observer(event.event_type, event.correlation_id, success, duration, error)
