"""OutboxProjector - Reliable event publisher from Outbox table.

This module provides OutboxProjector, a background service that continuously
polls the Outbox table and publishes events to the message bus.

Key Components:
- OutboxProjector: Main projector class
- Configuration constants: Batch size, sleep intervals, retry limits
"""

from .config import (
    DEFAULT_BATCH_SIZE,
    MAX_RETRY,
    SLEEP_BUSY,
    SLEEP_IDLE,
    SLEEP_IDLE_MAX,
    STATUS_ERROR,
    STATUS_PENDING,
    STATUS_PUBLISHED,
    STATUS_PUBLISHING,
)
from .projector import OutboxProjector

__all__ = [
    # Main class
    "OutboxProjector",
    # Configuration
    "DEFAULT_BATCH_SIZE",
    "MAX_RETRY",
    "SLEEP_BUSY",
    "SLEEP_IDLE",
    "SLEEP_IDLE_MAX",
    "STATUS_PENDING",
    "STATUS_PUBLISHING",
    "STATUS_PUBLISHED",
    "STATUS_ERROR",
]
