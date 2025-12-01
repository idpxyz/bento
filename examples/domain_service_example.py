"""Domain Service Example - Correct DDD Implementation with Bento Framework.

This example demonstrates the proper use of Domain Services in the Bento Framework,
showing how they integrate with UnitOfWork, Repository patterns, and event publishing.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from bento.core.ids import EntityId
from bento.domain.aggregate import AggregateRoot
from bento.domain.domain_event import DomainEvent
from bento.domain.domain_service import DomainService


# Domain Value Objects
@dataclass(frozen=True)
class Money:
    """Money value object."""
    amount: Decimal
    currency: str = "USD"

    @classmethod
    def zero(cls) -> "Money":
        return cls(Decimal('0'))

    def __gt__(self, other: "Money") -> bool:
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        return self.amount >= other.amount

    def __add__(self, other: "Money") -> "Money":
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: float) -> "Money":
        return Money(self.amount * Decimal(str(factor)), self.currency)


# Domain Events
@dataclass(frozen=True)
class TransferInitiatedEvent(DomainEvent):
    from_account_id: str = ""
    to_account_id: str = ""
    amount: str = ""  # Serialized Money
    topic: str = "account.transfer_initiated"


@dataclass(frozen=True)
class TransferReceivedEvent(DomainEvent):
    from_account_id: str = ""
    to_account_id: str = ""
    amount: str = ""  # Serialized Money
    topic: str = "account.transfer_received"


# Domain Exceptions
class DomainException(Exception):
    """Base domain exception."""
    pass


class InsufficientFundsException(DomainException):
    """Insufficient funds for operation."""
    pass


class AccountFrozenException(DomainException):
    """Account is frozen and cannot perform operations."""
    pass


# Aggregates
class Account(AggregateRoot):
    """Account aggregate root."""

    def __init__(self, account_id: str, balance: Money, is_active: bool = True):
        super().__init__(EntityId(account_id))
        self.balance = balance
        self.is_active = is_active
        self.is_frozen = False

    def withdraw(self, amount: Money) -> None:
        """Withdraw money from account."""
        if self.balance < amount:
            raise InsufficientFundsException(f"Insufficient funds: {self.balance.amount}")

        self.balance = self.balance - amount

    def deposit(self, amount: Money) -> None:
        """Deposit money to account."""
        self.balance = self.balance + amount

    def freeze(self) -> None:
        """Freeze the account."""
        self.is_frozen = True

    def unfreeze(self) -> None:
        """Unfreeze the account."""
        self.is_frozen = False


# ✅ CORRECT: Pure Domain Service (No Infrastructure Dependencies)
class TransferDomainService(DomainService):
    """Domain service for account transfers.

    Contains pure business logic without infrastructure dependencies.
    Focuses on business rules, validations, and domain operations.
    """

    @staticmethod
    def can_transfer(from_account: Account, to_account: Account, amount: Money) -> bool:
        """Validate if transfer is allowed by business rules.

        Args:
            from_account: Source account
            to_account: Target account
            amount: Transfer amount

        Returns:
            True if transfer is allowed
        """
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
        """Execute transfer business logic.

        Args:
            from_account: Source account
            to_account: Target account
            amount: Transfer amount

        Raises:
            DomainException: If transfer violates business rules
        """
        # Validate business rules
        if not TransferDomainService.can_transfer(from_account, to_account, amount):
            if not from_account.is_active:
                raise DomainException("Source account is inactive")
            if not to_account.is_active:
                raise DomainException("Target account is inactive")
            if from_account.is_frozen:
                raise AccountFrozenException("Source account is frozen")
            if to_account.is_frozen:
                raise AccountFrozenException("Target account is frozen")
            if from_account.balance < amount:
                raise InsufficientFundsException("Insufficient funds")
            if amount <= Money.zero():
                raise DomainException("Transfer amount must be positive")

        # Execute domain operations
        from_account.withdraw(amount)
        to_account.deposit(amount)

        # Publish domain events (will be handled by UoW)
        from_account.add_event(TransferInitiatedEvent(
            from_account_id=str(from_account.id),
            to_account_id=str(to_account.id),
            amount=str(amount.amount),
            occurred_at=datetime.now()
        ))

        to_account.add_event(TransferReceivedEvent(
            from_account_id=str(from_account.id),
            to_account_id=str(to_account.id),
            amount=str(amount.amount),
            occurred_at=datetime.now()
        ))

    @staticmethod
    def calculate_transfer_fee(amount: Money, from_account: Account, to_account: Account) -> Money:
        """Calculate transfer fee based on business rules.

        Args:
            amount: Transfer amount
            from_account: Source account
            to_account: Target account

        Returns:
            Transfer fee amount
        """
        # Base fee: 0.5%
        base_fee = amount * 0.005

        # VIP accounts get 50% discount
        if hasattr(from_account, 'is_vip') and from_account.is_vip:
            base_fee = base_fee * 0.5

        # Large transfers (>$10,000) get reduced fee
        if amount.amount > Decimal('10000'):
            base_fee = base_fee * 0.8

        # Minimum fee: $1, Maximum fee: $50
        min_fee = Money(Decimal('1'))
        max_fee = Money(Decimal('50'))

        if base_fee < min_fee:
            return min_fee
        elif base_fee > max_fee:
            return max_fee
        else:
            return base_fee


# Application Service (Coordinates Domain Service with Infrastructure)
class TransferApplicationService:
    """Application service that coordinates transfer operations.

    Responsibilities:
    - Coordinate domain operations
    - Manage transactions through UoW
    - Handle infrastructure concerns
    - Orchestrate cross-aggregate operations
    """

    def __init__(self, uow: Any):  # UnitOfWork type
        """Initialize with UnitOfWork for transaction management."""
        self.uow = uow

    async def transfer_money(self, from_account_id: str, to_account_id: str, amount: Money) -> dict:
        """Transfer money between accounts.

        Args:
            from_account_id: Source account ID
            to_account_id: Target account ID
            amount: Transfer amount

        Returns:
            Transfer result with status and details
        """
        try:
            async with self.uow:
                # Infrastructure: Data access through UoW
                account_repo = self.uow.repository(Account)
                from_account = await account_repo.get(from_account_id)
                to_account = await account_repo.get(to_account_id)

                if not from_account:
                    return {"success": False, "error": "Source account not found"}
                if not to_account:
                    return {"success": False, "error": "Target account not found"}

                # Domain: Business logic through Domain Service
                transfer_fee = TransferDomainService.calculate_transfer_fee(
                    amount, from_account, to_account
                )

                # Execute transfer with fee
                total_amount = amount + transfer_fee
                TransferDomainService.execute_transfer(from_account, to_account, total_amount)

                # Infrastructure: Transaction commit and event publishing via UoW
                await self.uow.commit()

                return {
                    "success": True,
                    "transfer_amount": str(amount.amount),
                    "fee": str(transfer_fee.amount),
                    "total_deducted": str(total_amount.amount)
                }

        except DomainException as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}


# Mock implementations for demo
class MockRepository:
    def __init__(self):
        self.accounts = {
            "acc1": Account("acc1", Money(Decimal('1000'))),
            "acc2": Account("acc2", Money(Decimal('500')))
        }

    async def get(self, account_id: str) -> Account | None:
        return self.accounts.get(account_id)


class MockUnitOfWork:
    def __init__(self):
        self._repo = MockRepository()

    def repository(self, aggregate_type):
        return self._repo

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def commit(self):
        print("💾 Transaction committed - Events published")


# Demo function
async def demo_domain_service():
    """Demonstrate correct Domain Service usage with Bento Framework."""

    print("🎯 Domain Service Example - Correct DDD Implementation")
    print("=" * 55)

    # Setup
    uow = MockUnitOfWork()
    transfer_service = TransferApplicationService(uow)

    print("\n💰 Initial Account States:")
    print("   Account 1: $1000")
    print("   Account 2: $500")

    print("\n📤 Executing Transfer: $200 from Account 1 to Account 2")

    # Execute transfer
    result = await transfer_service.transfer_money("acc1", "acc2", Money(Decimal('200')))

    print(f"\n📊 Transfer Result:")
    for key, value in result.items():
        print(f"   {key}: {value}")

    print("\n✅ Key Benefits of This Architecture:")
    benefits = [
        "🎯 Pure Domain Logic - No infrastructure dependencies in Domain Service",
        "🔒 Transaction Safety - UoW ensures ACID properties",
        "📡 Event Integration - Automatic domain event publishing",
        "🧪 Easy Testing - Domain Service can be unit tested without mocks",
        "🏗️ Clear Separation - Domain vs Application vs Infrastructure concerns",
        "📈 Bento Integration - Leverages all framework capabilities"
    ]

    for benefit in benefits:
        print(f"   {benefit}")

    print(f"\n🔄 Architecture Flow:")
    print("   1. Application Service receives request")
    print("   2. UoW provides transactional context")
    print("   3. Repository loads aggregates")
    print("   4. Domain Service executes business logic")
    print("   5. UoW commits transaction and publishes events")


if __name__ == "__main__":
    asyncio.run(demo_domain_service())
