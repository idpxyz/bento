from domain.messaging.events import DomainEvent


class EventHandler:
    def __init__(self, event_type: str):
        self.event_type = event_type
    
    async def handle(self, event: DomainEvent) -> None:
        pass

from dataclasses import dataclass


@dataclass
class PublishEventCommand:
    event_type: str
    payload: dict
    source: str
