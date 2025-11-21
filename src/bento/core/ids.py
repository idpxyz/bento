"""Identity types for entities and aggregates.

This module provides type-safe identity classes that behave like strings
but maintain type safety in the domain layer.
"""

import uuid
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntityId:
    """Entity identifier (legacy name)."""

    value: str

    @staticmethod
    def generate() -> "EntityId":
        """Generate a new unique identifier."""
        return EntityId(str(uuid.uuid4()))

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.value}')"


@dataclass(frozen=True)
class ID(EntityId):
    """Modern identifier class for aggregates and entities.

    This class behaves like a string in most contexts while maintaining
    type safety. It automatically converts to string when needed and
    supports string operations transparently.

    Subclassing EntityId ensures compatibility with generic bounds like
    `TypeVar("ID", bound=EntityId)` used across repository protocols.

    Example:
        ```python
        # Create ID
        user_id = ID.generate()

        # Acts like a string
        print(f"User: {user_id}")  # Works
        assert user_id == "some-uuid-string"  # Works
        path = "/users/" + user_id  # Works

        # But maintains type safety
        def get_user(id: ID) -> User: ...
        get_user(user_id)  # ✅ Type-safe
        get_user("raw-string")  # ❌ Type error
        ```
    """

    @staticmethod
    def generate() -> "ID":
        """Generate a new unique identifier."""
        return ID(str(uuid.uuid4()))

    def __str__(self) -> str:
        """Convert to string."""
        return self.value

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"ID('{self.value}')"

    def __eq__(self, other: object) -> bool:
        """Compare with other IDs or strings.

        Allows: id == "string" and id == other_id
        """
        if isinstance(other, (EntityId, ID)):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False

    def __hash__(self) -> int:
        """Hash based on value for use in sets/dicts."""
        return hash(self.value)

    def __format__(self, format_spec: str) -> str:
        """Support string formatting.

        Example: f"ID: {user_id:>20}"
        """
        return format(self.value, format_spec)

    def __add__(self, other: Any) -> str:
        """Support string concatenation: id + "suffix"."""
        return self.value + str(other)

    def __radd__(self, other: Any) -> str:
        """Support reverse string concatenation: "prefix" + id."""
        return str(other) + self.value

    def __len__(self) -> int:
        """Return length of ID string."""
        return len(self.value)

    def __getitem__(self, key: Any) -> str:
        """Support indexing and slicing: id[0], id[:8]."""
        return self.value[key]

    def __contains__(self, item: str) -> bool:
        """Support 'in' operator: "abc" in id."""
        return item in self.value

    # Proxy common string methods to make ID act like a string

    def lower(self) -> str:
        """Convert to lowercase."""
        return self.value.lower()

    def upper(self) -> str:
        """Convert to uppercase."""
        return self.value.upper()

    def startswith(self, prefix: str) -> bool:
        """Check if ID starts with prefix."""
        return self.value.startswith(prefix)

    def endswith(self, suffix: str) -> bool:
        """Check if ID ends with suffix."""
        return self.value.endswith(suffix)

    def split(self, sep: str | None = None, maxsplit: int = -1) -> list[str]:
        """Split ID string."""
        return self.value.split(sep, maxsplit)

    def replace(self, old: str, new: str, count: int = -1) -> str:
        """Replace substring in ID."""
        return self.value.replace(old, new, count)

    def strip(self) -> str:
        """Strip whitespace."""
        return self.value.strip()
