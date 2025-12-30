"""Outbox Pattern implementation for reliable event delivery.

This module implements the Transactional Outbox pattern for ensuring
exactly-once event delivery in event-driven architectures.

Pattern:
1. Events are stored in an "outbox" table within the same transaction as business data
2. A separate process (Projector) polls the outbox and publishes events
3. Events are marked as published after successful delivery

"""

from .record import OutboxRecord, SqlAlchemyOutbox

__all__ = [
    # Core components（Outbox 只负责存储）
    "OutboxRecord",
    "SqlAlchemyOutbox",
]

# 注意：Outbox 事件处理由 OutboxProjector 负责
# 位置：bento.infrastructure.projection.projector.OutboxProjector
