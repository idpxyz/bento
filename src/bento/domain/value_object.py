from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject[T]:
    """Base class for value objects.

    Value objects are immutable objects that are used to represent a value in the domain.
    They are compared by their value, not by their identity.
    """

    value: T

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ValueObject):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __str__(self) -> str:
        return str(self.value)
