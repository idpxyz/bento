"""Value Object base classes.

Value Objects are immutable domain objects that are defined by their attributes
rather than a unique identity. They are compared by value equality.

Key characteristics:
- Immutable (frozen dataclass)
- Compared by value, not identity
- Self-validating
- No side effects
"""

from dataclasses import dataclass, fields
from typing import Any, Self


@dataclass(frozen=True)
class ValueObject[T]:
    """Simple value object wrapper for single values.

    This is a convenient base class for wrapping a single value.
    Value objects are immutable and compared by their value, not identity.

    For multi-attribute value objects, use CompositeValueObject instead.

    Example:
        ```python
        @dataclass(frozen=True)
        class Email(ValueObject[str]):
            value: str

            def validate(self) -> None:
                if "@" not in self.value:
                    raise ValueError("Invalid email format")

        # Usage
        email = Email.create("user@example.com")
        ```
    """

    value: T

    def __post_init__(self) -> None:
        """Call validate after initialization."""
        self.validate()

    def validate(self) -> None:
        """Override to add custom validation logic.

        Raises:
            ValueError: If validation fails
        """
        pass

    @classmethod
    def create(cls, value: T) -> Self:
        """Factory method to create a value object.

        Args:
            value: The value to wrap

        Returns:
            New ValueObject instance

        Example:
            ```python
            email = Email.create("user@example.com")
            ```
        """
        return cls(value=value)

    def __eq__(self, other: object) -> bool:
        """Compare by value equality."""
        if not isinstance(other, ValueObject):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        """Hash based on value."""
        return hash(self.value)

    def __str__(self) -> str:
        """String representation of the value."""
        return str(self.value)

    def to_primitive(self) -> T:
        """Convert to primitive value for serialization.

        Returns:
            The underlying primitive value
        """
        return self.value


@dataclass(frozen=True)
class CompositeValueObject:
    """Base class for multi-attribute value objects.

    Use this for value objects with multiple attributes.
    Provides automatic validation, equality, hashing, and serialization.

    Example:
        ```python
        from decimal import Decimal

        @dataclass(frozen=True)
        class Money(CompositeValueObject):
            amount: Decimal
            currency: str

            def validate(self) -> None:
                if self.amount < 0:
                    raise ValueError("Amount cannot be negative")
                if len(self.currency) != 3:
                    raise ValueError("Currency must be 3-letter code")

        @dataclass(frozen=True)
        class Address(CompositeValueObject):
            street: str
            city: str
            country: str
            postal_code: str

            def validate(self) -> None:
                if not self.street:
                    raise ValueError("Street is required")
                if not self.city:
                    raise ValueError("City is required")

        # Usage
        money = Money.create(amount=Decimal("100.00"), currency="USD")
        address = Address.create(
            street="123 Main St",
            city="New York",
            country="USA",
            postal_code="10001"
        )

        # Serialization
        money_dict = money.to_dict()  # {"amount": Decimal("100.00"), "currency": "USD"}
        money2 = Money.from_dict(money_dict)
        assert money == money2
        ```
    """

    def __post_init__(self) -> None:
        """Call validate after initialization."""
        self.validate()

    def validate(self) -> None:
        """Override to add custom validation logic.

        This method is called automatically after __init__.
        Raise ValueError or domain-specific exceptions for validation failures.

        Example:
            ```python
            def validate(self) -> None:
                if self.amount < 0:
                    raise ValueError("Amount cannot be negative")
            ```
        """
        pass

    @classmethod
    def create(cls, **kwargs: Any) -> Self:
        """Factory method to create a composite value object.

        Args:
            **kwargs: Attribute values

        Returns:
            New CompositeValueObject instance

        Example:
            ```python
            money = Money.create(amount=Decimal("100"), currency="USD")
            ```
        """
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary of attribute names to values

        Example:
            ```python
            money = Money(amount=Decimal("100"), currency="USD")
            data = money.to_dict()  # {"amount": Decimal("100"), "currency": "USD"}
            ```
        """
        result: dict[str, Any] = {}
        for field in fields(self):
            value = getattr(self, field.name)
            # Recursively convert nested value objects
            if isinstance(value, CompositeValueObject):
                result[field.name] = value.to_dict()
            elif isinstance(value, ValueObject):
                result[field.name] = value.to_primitive()
            else:
                result[field.name] = value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create instance from dictionary.

        Args:
            data: Dictionary of attribute values

        Returns:
            New CompositeValueObject instance

        Example:
            ```python
            data = {"amount": Decimal("100"), "currency": "USD"}
            money = Money.from_dict(data)
            ```
        """
        return cls(**data)

    def __eq__(self, other: object) -> bool:
        """Compare by value equality (all attributes)."""
        if not isinstance(other, self.__class__):
            return False
        return all(getattr(self, f.name) == getattr(other, f.name) for f in fields(self))

    def __hash__(self) -> int:
        """Hash based on all attribute values."""
        return hash(tuple(getattr(self, f.name) for f in fields(self)))

    def replace(self, **kwargs: Any) -> Self:
        """Create a new instance with some attributes replaced.

        Since value objects are immutable, this creates a new instance.

        Args:
            **kwargs: Attributes to replace

        Returns:
            New instance with replaced values

        Example:
            ```python
            money = Money(amount=Decimal("100"), currency="USD")
            money_eur = money.replace(currency="EUR")
            ```
        """
        current = self.to_dict()
        current.update(kwargs)
        return self.__class__(**current)
