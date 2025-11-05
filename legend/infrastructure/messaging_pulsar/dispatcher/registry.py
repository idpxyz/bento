from typing import Callable, Dict, List

from ..core.base_message import MessageEnvelope

_handler_registry: Dict[str, List[Callable[[MessageEnvelope], None]]] = {}


def register(event_type: str, handler: Callable[[MessageEnvelope], None]) -> None:
    if event_type not in _handler_registry:
        _handler_registry[event_type] = []
    _handler_registry[event_type].append(handler)


def get_handlers(event_type: str) -> List[Callable[[MessageEnvelope], None]]:
    return _handler_registry.get(event_type, [])
