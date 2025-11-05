"""Pulsar Adapter - Apache Pulsar message bus implementation.

This package provides the Pulsar adapter for the MessageBus port.

Components:
- PulsarConfig: Configuration for Pulsar client
- PulsarMessageBus: MessageBus implementation using Pulsar
"""

from bento.adapters.messaging.pulsar.config import PulsarConfig, get_pulsar_config
from bento.adapters.messaging.pulsar.message_bus import PulsarMessageBus

__all__ = [
    "PulsarConfig",
    "PulsarMessageBus",
    "get_pulsar_config",
]
