import functools
import time
from typing import Callable

from ..dlq.handler import write_to_dlq
from ..observe.hook import report_event
from .registry import register


def event_handler(event_type: str):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(event):
            start = time.time()
            try:
                await func(event)
                report_event(event, success=True, start_time=start)
            except Exception as e:
                report_event(event, success=False, start_time=start, error=str(e))
                write_to_dlq(event, reason=str(e))
                raise e  # 继续让 dispatcher 做 nack 或重试

        register(event_type, wrapper)
        return wrapper
    return decorator
