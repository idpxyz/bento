"""Value Object base classes.

Value Objects are immutable domain objects that are defined by their attributes
rather than a unique identity. They are compared by value equality.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject[T]:
    """Simple value object wrapper for single values.

    This is a convenient base class for wrapping a single value.
    Value objects are immutable and compared by their value, not identity.

    For multi-attribute value objects, use plain @dataclass(frozen=True)
    without inheriting from this class.

    Example:
        ```python
        # Simple value object
        @dataclass(frozen=True)
        class Email(ValueObject[str]):
            value: str

            def __post_init__(self):
                if "@" not in self.value:
                    raise ValueError("Invalid email")

        # Multi-attribute value object (don't inherit ValueObject[T])
        @dataclass(frozen=True)
        class Money:
            amount: Decimal
            currency: str

            def __post_init__(self):
                if self.amount < 0:
                    raise ValueError("Amount cannot be negative")
        ```
    """

    value: T

    def __eq__(self, other: object) -> bool:
        """Compare by value equality.

        Args:
            other: Object to compare

        Returns:
            True if values are equal
        """
        if not isinstance(other, ValueObject):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Hash based on value.

        Returns:
            Hash of the value
        """
        return hash(self.value)

    def __str__(self) -> str:
        """String representation of the value.

        Returns:
            String representation
        """
        return str(self.value)
