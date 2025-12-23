from dataclasses import dataclass
from datetime import datetime, timezone
import uuid

@dataclass(frozen=True)
class DomainEvent:
    event_id: str
    occurred_at: str

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def new_id() -> str:
        return uuid.uuid4().hex
