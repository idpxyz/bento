"""Ports layer – **AbstractEventBus** & default Console adapter.

* `AbstractEventBus`  ➜  The hexagonal *Port* exposed to UoW / Projector.
* `ConsoleBus`        ➜  Minimal adapter for dev / unit‑test environments.

Concrete production adapters (e.g. `PulsarEventBus`, `KafkaEventBus`) should
inherit from `AbstractEventBus` and implement `publish()`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod 
from typing import Sequence

from idp.framework.domain.base.event import DomainEvent


class AbstractEventBus(ABC):
    """Port interface – decouples domain/application layers from transport."""

    @abstractmethod
    async def publish(self, events: Sequence[DomainEvent]) -> None:  # pragma: no cover
        """Publish one or more DomainEvents to external broker.

        Implementations **must** be *at‑least‑once* (retry/ack) and raise
        exception on permanent failure so that UoW / Projector can handle it.
        """
        raise NotImplementedError
