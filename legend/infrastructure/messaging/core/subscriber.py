from abc import ABC, abstractmethod
from typing import Awaitable, Callable

from idp.framework.domain.base.event import DomainEvent


class AbstractEventSubscriber(ABC):
    @abstractmethod
    async def subscribe(
        self,
        topic: str,
        handler: Callable[[DomainEvent], Awaitable[None]],
        tenant_id: str | None = None,
    ): ...
