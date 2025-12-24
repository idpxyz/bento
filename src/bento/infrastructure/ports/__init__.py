"""Infrastructure ports registry.

Provides automatic discovery of port adapter implementations.
"""

from .registry import (
    clear_port_registry,
    get_port_adapter,
    get_port_registry,
    port_for,
)

__all__ = [
    "port_for",
    "get_port_registry",
    "get_port_adapter",
    "clear_port_registry",
]
