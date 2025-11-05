import logging
from typing import Sequence

from idp.framework.domain.base.event import DomainEvent
from idp.framework.infrastructure.messaging.core.event_bus import AbstractEventBus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Reference adapter – prints events to stdout (for local dev / tests)
# ---------------------------------------------------------------------


class ConsoleEventBus(AbstractEventBus):
    # type: ignore[override]
    async def publish(self, events: Sequence[DomainEvent]) -> None:
        logger.info(
            "ConsoleEventBus received %d events to publish", len(events))
        try:
            for evt in events:
                # Using repr() so hash & schema_id are visible in logs
                logger.info(f"[ConsoleBus] Publishing event: {evt!r}")
                logger.debug(
                    f"[ConsoleBus] Event details: type={evt.__class__.__name__}, id={evt.event_id}, aggregate={evt.aggregate_id}")
        except Exception as e:
            logger.error("Failed to publish events: %s", str(e), exc_info=True)
            raise
