import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class EntityId:
    """Entity identifier (legacy name)."""

    value: str

    @staticmethod
    def generate() -> "EntityId":
        """Generate a new unique identifier."""
        return EntityId(str(uuid.uuid4()))


@dataclass(frozen=True)
class ID(EntityId):
    """Modern identifier class for aggregates and entities.

    Subclassing EntityId ensures compatibility with generic bounds like
    `TypeVar("ID", bound=EntityId)` used across repository protocols.
    """

    @staticmethod
    def generate() -> "ID":
        """Generate a new unique identifier."""
        return ID(str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value
