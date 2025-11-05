from typing import Callable, Dict, List

from ..core.base_message import MessageEnvelope

_event_handlers: Dict[str, List[Callable[[MessageEnvelope], None]]] = {}


def register_handler(event_type: str, handler: Callable[[MessageEnvelope], None]) -> None:
    if event_type not in _event_handlers:
        _event_handlers[event_type] = []
    _event_handlers[event_type].append(handler)


def get_handlers(event_type: str) -> List[Callable[[MessageEnvelope], None]]:
    return _event_handlers.get(event_type, [])
