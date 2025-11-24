"""Outbox Pattern implementation for reliable event delivery.

This module implements the Transactional Outbox pattern for ensuring
exactly-once event delivery in event-driven architectures.

Pattern:
1. Events are stored in an "outbox" table within the same transaction as business data
2. A separate process (Projector) polls the outbox and publishes events
3. Events are marked as published after successful delivery

Benefits:
- Exactly-once event delivery
- Transactional consistency between data and events
- Resilience to message broker failures

Components:
- OutboxRecord: SQLAlchemy model for the outbox table
- SqlAlchemyOutbox: Outbox implementation
- Outbox Listener: SQLAlchemy event listener (optional)
"""

from bento.persistence.outbox.record import OutboxRecord, SqlAlchemyOutbox

__all__ = [
    "OutboxRecord",
    "SqlAlchemyOutbox",
]
