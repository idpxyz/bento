"""Entity base class.

Entities are domain objects that have a unique identity.
Two entities are equal if they have the same identity, regardless of their attributes.
"""

from dataclasses import dataclass

from bento.core.ids import EntityId


@dataclass
class Entity:
    """Base class for all entities in the domain.

    Entities are defined by their identity (ID), not their attributes.
    Two entities with the same ID are considered equal, even if their
    other attributes differ.

    Example:
        ```python
        class User(Entity):
            name: str
            email: str

        user1 = User(id=ID("123"), name="Alice", email="alice@example.com")
        user2 = User(id=ID("123"), name="Bob", email="bob@example.com")

        assert user1 == user2  # True - same ID
        ```
    """

    id: EntityId

    def __eq__(self, other: object) -> bool:
        """Compare entities based on identity.

        Args:
            other: Object to compare with

        Returns:
            True if other is an Entity with the same ID
        """
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on entity identity.

        Returns:
            Hash of the entity ID
        """
        return hash(self.id)
