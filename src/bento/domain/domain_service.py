"""Domain Service base class.

Domain Services encapsulate pure business logic that doesn't naturally fit within
a single Entity or Value Object. They coordinate multiple aggregates and contain
stateless domain operations, calculations, and business rules.

Domain Services should be:
- Stateless (no instance variables)
- Pure domain logic (no infrastructure dependencies)
- Focused on business rules and calculations
- Independent of data access concerns

Requires Python 3.12+ for optimal performance and modern type features.
"""

from __future__ import annotations

from typing import Any, TypeGuard, final
from warnings import warn

from bento.domain.aggregate import AggregateRoot


class DomainService:
    """Base class for domain services.

    Domain services contain pure business logic that:
    - Doesn't naturally belong to a single entity or value object
    - Coordinates business rules across multiple aggregates
    - Performs domain calculations and validations
    - Enforces business invariants and constraints

    Key Principles:
    - Stateless: No instance variables, only static/class methods
    - Pure: No dependencies on infrastructure (Repository, Database, etc.)
    - Focused: Only domain logic, no orchestration or data access
    - Testable: Easy to unit test without mocking infrastructure

    Examples:
        ```python
        # Example 1: Business Rule Validation
        class TransferDomainService(DomainService):
            @staticmethod
            def can_transfer(from_account: Account, to_account: Account, amount: Money) -> bool:
                \"\"\"Validate if transfer is allowed by business rules.\"\"\"
                return (
                    from_account.is_active and
                    to_account.is_active and
                    from_account.balance >= amount and
                    amount > Money.zero() and
                    not from_account.is_frozen and
                    not to_account.is_frozen
                )

            @staticmethod
            def execute_transfer(from_account: Account, to_account: Account, amount: Money) -> None:
                \"\"\"Execute transfer business logic.\"\"\"
                if not TransferDomainService.can_transfer(from_account, to_account, amount):
                    raise DomainException("Transfer violates business rules")

                # Pure domain logic - modify aggregates
                from_account.withdraw(amount)
                to_account.deposit(amount)

                # Domain events will be automatically published by UoW
                from_account.add_domain_event(
                    TransferInitiatedEvent(from_account.id, to_account.id, amount)
                )
                to_account.add_domain_event(
                    TransferReceivedEvent(from_account.id, to_account.id, amount)
                )

        # Example 2: Domain Calculations
        class PricingDomainService(DomainService):
            @staticmethod
            def calculate_discount(customer: Customer, order: Order) -> Money:
                \"\"\"Calculate customer discount based on business rules.\"\"\"
                base_discount = Money.zero()

                # VIP customer discount
                if customer.is_vip():
                    base_discount = order.subtotal * 0.1

                # Large order discount
                if order.subtotal > Money(1000):
                    base_discount = max(base_discount, order.subtotal * 0.05)

                # Loyalty points discount
                if customer.loyalty_points > 1000:
                    points_discount = Money(min(customer.loyalty_points / 10, 100))
                    base_discount = max(base_discount, points_discount)

                return base_discount

        # Example 3: Complex Business Validation
        class OrderDomainService(DomainService):
            @staticmethod
            def validate_order_modification(order: Order, new_items: list[OrderItem]) -> bool:
                \"\"\"Validate if order can be modified according to business rules.\"\"\"
                if order.status != OrderStatus.PENDING:
                    return False

                # Check business hours
                if not OrderDomainService._is_modification_allowed_time():
                    return False

                # Check inventory constraints would be handled by aggregate
                return order.can_modify_items(new_items)

            @staticmethod
            def _is_modification_allowed_time() -> bool:
                \"\"\"Check if current time allows order modifications.\"\"\"
                from datetime import datetime, time
                now = datetime.now().time()
                return time(9, 0) <= now <= time(17, 0)  # Business hours
        ```

    Integration with Bento Framework:
        Domain Services work seamlessly with Bento's architecture:

        ```python
        # Application Service coordinates using Domain Service
        class TransferApplicationService:
            def __init__(self, uow: UnitOfWork):
                self.uow = uow

            async def transfer_money(self, command: TransferCommand) -> TransferResult:
                async with self.uow:
                    # Data access through UoW
                    account_repo = self.uow.repository(Account)
                    from_account = await account_repo.get(command.from_account_id)
                    to_account = await account_repo.get(command.to_account_id)

                    # Business logic through Domain Service
                    TransferDomainService.execute_transfer(
                        from_account, to_account, command.amount
                    )

                    # UoW handles transaction and event publishing
                    await self.uow.commit()
                    return TransferResult.success()
        ```
    """

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Ensure domain services follow Python 3.12+ best practices."""
        super().__init_subclass__(**kwargs)

        # Validate that domain service doesn't have instance state
        if hasattr(cls, "__init__") and cls.__init__ != DomainService.__init__:
            # Enhanced warning message for Python 3.12+
            warn(
                f" {cls.__name__} defines custom __init__ method. "
                f"Domain Services should be stateless for optimal performance in Python 3.12+. "
                f" Consider using @staticmethod, @classmethod, or module-level functions instead.",
                UserWarning,
                stacklevel=2,
            )

    @final
    def __init__(self) -> None:
        """Domain Services should be stateless (Python 3.12+ optimized).

        This base __init__ is marked @final to prevent overriding.
        Subclasses should use static methods for better performance.

        Note: Python 3.12+ provides significant performance improvements
        for static method calls over instance method calls.
        """
        pass

    @classmethod
    def validate_aggregates(cls, *aggregates: AggregateRoot | None) -> None:
        """Validate aggregates with Python 3.12+ type safety.

        Args:
            *aggregates: Aggregates to validate (can include None for convenience)

        Raises:
            ValueError: If any aggregate is None or in invalid state
        """
        for i, aggregate in enumerate(aggregates):
            if aggregate is None:
                raise ValueError(
                    f" Aggregate at position {i} cannot be None. "
                    f" Check your repository queries or domain logic."
                )

            # Python 3.12+ enhanced type checking
            if not isinstance(aggregate, AggregateRoot):
                raise TypeError(
                    f" Object at position {i} is not an AggregateRoot. "
                    f" Got: {type(aggregate).__name__}, Expected: AggregateRoot"
                )

    @staticmethod
    def is_valid_aggregate(obj: Any) -> TypeGuard[AggregateRoot]:
        """Type guard for aggregate validation (Python 3.12+ feature).

        Args:
            obj: Object to validate

        Returns:
            True if obj is a valid AggregateRoot
        """
        return isinstance(obj, AggregateRoot) and obj is not None

    @classmethod
    def create_domain_exception(cls, message: str, *, cause: Exception | None = None) -> Exception:
        """Create enhanced domain exception with Python 3.12+ features.

        Args:
            message: Error message
            cause: Optional underlying cause

        Returns:
            Enhanced exception with better debugging info
        """
        enhanced_message = f" Domain Logic Error in {cls.__name__}: {message}"

        if cause:
            enhanced_message += f"\n Caused by: {type(cause).__name__}: {cause}"

        # Python 3.12+ provides better exception chaining
        exception = ValueError(enhanced_message)
        if cause:
            exception.__cause__ = cause

        return exception
