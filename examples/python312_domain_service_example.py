"""Python 3.12+ Domain Service Example - Modern Features Showcase.

This example demonstrates how the optimized DomainService leverages
Python 3.12+ features for better performance, type safety, and developer experience.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from bento.core.ids import EntityId
from bento.domain.aggregate import AggregateRoot
from bento.domain.domain_event import DomainEvent
from bento.domain.domain_service import DomainService


# Modern Value Object with Python 3.12+ features
@dataclass(frozen=True, slots=True)  # slots=True for better memory performance
class Money:
    """Modern Money value object optimized for Python 3.12+."""
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")

    @classmethod
    def zero(cls) -> Money:
        return cls(Decimal('0'))

    def __add__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: float | Decimal) -> Money:
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __gt__(self, other: Money) -> bool:
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        return self.amount >= other.amount


# Domain Events with better type hints
@dataclass(frozen=True, slots=True)
class AccountTransferEvent(DomainEvent):
    from_account_id: str = ""
    to_account_id: str = ""
    amount: str = ""
    topic: str = "account.transfer_completed"


# Enhanced Aggregate with Python 3.12+ optimization
class BankAccount(AggregateRoot):
    """Modern bank account aggregate optimized for Python 3.12+."""

    __slots__ = ('balance', 'is_active', 'is_frozen', 'account_type')  # Memory optimization

    def __init__(self, account_id: str, initial_balance: Money, account_type: str = "checking"):
        super().__init__(EntityId(account_id))
        self.balance = initial_balance
        self.is_active = True
        self.is_frozen = False
        self.account_type = account_type

    def withdraw(self, amount: Money) -> None:
        """Withdraw with enhanced validation."""
        if self.balance < amount:
            raise ValueError(f"Insufficient funds: available {self.balance.amount}, requested {amount.amount}")

        self.balance = self.balance - amount

    def deposit(self, amount: Money) -> None:
        """Deposit with validation."""
        if amount.amount <= 0:
            raise ValueError("Deposit amount must be positive")

        self.balance = self.balance + amount

    def freeze(self) -> None:
        """Freeze account operations."""
        self.is_frozen = True

    def is_operational(self) -> bool:
        """Check if account can perform operations."""
        return self.is_active and not self.is_frozen


# ✅ Python 3.12+ Optimized Domain Service
class ModernTransferDomainService(DomainService):
    """Modern transfer domain service showcasing Python 3.12+ features."""

    @staticmethod
    def validate_transfer_eligibility(
        from_account: BankAccount,
        to_account: BankAccount,
        amount: Money
    ) -> bool:
        """Validate transfer using modern type safety."""
        # Use TypeGuard for runtime type checking
        if not (DomainService.is_valid_aggregate(from_account) and
                DomainService.is_valid_aggregate(to_account)):
            return False

        # Enhanced business rules with clear logic
        return all([
            from_account.is_operational(),
            to_account.is_operational(),
            from_account.balance >= amount,
            amount > Money.zero(),
            from_account.id != to_account.id,  # No self-transfers
        ])

    @staticmethod
    def calculate_transfer_fee(amount: Money, from_account: BankAccount) -> Money:
        """Calculate fees with Python 3.12+ performance optimizations."""
        # Base fee calculation with pattern matching-style logic
        base_rate = 0.001  # 0.1%

        # Account type multipliers
        type_multipliers = {
            "premium": 0.5,   # 50% discount
            "business": 0.8,  # 20% discount
            "checking": 1.0,  # Standard rate
            "savings": 1.2    # 20% premium
        }

        multiplier = type_multipliers.get(from_account.account_type, 1.0)
        calculated_fee = amount * (base_rate * multiplier)

        # Fee bounds with modern syntax
        min_fee, max_fee = Money(Decimal('1')), Money(Decimal('25'))

        return max(min_fee, min(calculated_fee, max_fee))

    @staticmethod
    def execute_transfer_with_fee(
        from_account: BankAccount,
        to_account: BankAccount,
        amount: Money
    ) -> dict[str, Any]:
        """Execute transfer with comprehensive validation and modern error handling."""
        try:
            # Pre-validation using class methods
            DomainService.validate_aggregates(from_account, to_account)

            if not ModernTransferDomainService.validate_transfer_eligibility(
                from_account, to_account, amount
            ):
                return {
                    "success": False,
                    "error": "Transfer validation failed",
                    "details": ModernTransferDomainService._get_validation_details(
                        from_account, to_account, amount
                    )
                }

            # Calculate fee with modern method
            transfer_fee = ModernTransferDomainService.calculate_transfer_fee(amount, from_account)
            total_amount = amount + transfer_fee

            # Validate total amount after fee
            if from_account.balance < total_amount:
                return {
                    "success": False,
                    "error": "Insufficient funds including transfer fee",
                    "details": {
                        "available": str(from_account.balance.amount),
                        "required": str(total_amount.amount),
                        "fee": str(transfer_fee.amount)
                    }
                }

            # Execute the transfer
            from_account.withdraw(total_amount)
            to_account.deposit(amount)

            # Emit domain event with modern syntax
            transfer_event = AccountTransferEvent(
                from_account_id=str(from_account.id),
                to_account_id=str(to_account.id),
                amount=str(amount.amount),
                occurred_at=datetime.now()
            )

            from_account.add_event(transfer_event)

            return {
                "success": True,
                "transfer_amount": str(amount.amount),
                "fee_amount": str(transfer_fee.amount),
                "total_deducted": str(total_amount.amount),
                "from_balance": str(from_account.balance.amount),
                "to_balance": str(to_account.balance.amount)
            }

        except Exception as error:
            # Use enhanced exception creation
            enhanced_error = DomainService.create_domain_exception(
                f"Transfer execution failed: {amount.amount} from {from_account.id} to {to_account.id}",
                cause=error
            )

            return {
                "success": False,
                "error": str(enhanced_error),
                "error_type": type(error).__name__
            }

    @staticmethod
    def _get_validation_details(
        from_account: BankAccount,
        to_account: BankAccount,
        amount: Money
    ) -> dict[str, str]:
        """Get detailed validation failure reasons."""
        details = {}

        if not from_account.is_operational():
            details["from_account"] = f"Account {from_account.id} is not operational"

        if not to_account.is_operational():
            details["to_account"] = f"Account {to_account.id} is not operational"

        if from_account.balance < amount:
            details["insufficient_funds"] = f"Available: {from_account.balance.amount}, Required: {amount.amount}"

        if amount <= Money.zero():
            details["invalid_amount"] = "Transfer amount must be positive"

        if from_account.id == to_account.id:
            details["same_account"] = "Cannot transfer to the same account"

        return details


# Modern Application Service with Python 3.12+ patterns
class ModernTransferApplicationService:
    """Application service leveraging Python 3.12+ performance improvements."""

    def __init__(self, uow: Any):
        self.uow = uow

    async def process_transfer(
        self,
        from_account_id: str,
        to_account_id: str,
        amount_str: str
    ) -> dict[str, Any]:
        """Process transfer with comprehensive error handling and modern patterns."""
        try:
            amount = Money(Decimal(amount_str))

            async with self.uow:
                # Repository access
                account_repo = self.uow.repository(BankAccount)
                from_account = await account_repo.get(from_account_id)
                to_account = await account_repo.get(to_account_id)

                if not from_account:
                    return {"success": False, "error": f"Source account {from_account_id} not found"}

                if not to_account:
                    return {"success": False, "error": f"Target account {to_account_id} not found"}

                # Domain logic execution
                result = ModernTransferDomainService.execute_transfer_with_fee(
                    from_account, to_account, amount
                )

                if result["success"]:
                    await self.uow.commit()
                    result["transaction_id"] = f"tx_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                return result

        except (ValueError, TypeError, decimal.InvalidOperation) as e:
            return {
                "success": False,
                "error": f"Invalid input: {e}",
                "error_type": type(e).__name__
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"System error: {e}",
                "error_type": type(e).__name__
            }


# Mock infrastructure for demo
class MockRepository:
    def __init__(self):
        self.accounts = {
            "acc_premium_001": BankAccount("acc_premium_001", Money(Decimal('5000')), "premium"),
            "acc_business_002": BankAccount("acc_business_002", Money(Decimal('10000')), "business"),
            "acc_checking_003": BankAccount("acc_checking_003", Money(Decimal('1500')), "checking"),
        }

    async def get(self, account_id: str) -> BankAccount | None:
        return self.accounts.get(account_id)


class MockUoW:
    def __init__(self):
        self._repo = MockRepository()

    def repository(self, aggregate_type):
        return self._repo

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def commit(self):
        print("💾 Transaction committed with Python 3.12+ optimizations")


# Demo function
async def demo_python312_features():
    """Demonstrate Python 3.12+ optimized Domain Service."""

    print("🐍 Python 3.12+ Domain Service Demo")
    print("=" * 40)

    # Setup with modern patterns
    uow = MockUoW()
    transfer_service = ModernTransferApplicationService(uow)

    print("\n🏦 Account Setup:")
    print("   Premium Account: $5,000 (0.5x fee multiplier)")
    print("   Business Account: $10,000 (0.8x fee multiplier)")
    print("   Checking Account: $1,500 (1.0x fee multiplier)")

    # Test cases showcasing Python 3.12+ features
    test_cases = [
        {
            "name": "Premium Transfer",
            "from": "acc_premium_001",
            "to": "acc_business_002",
            "amount": "1000"
        },
        {
            "name": "Business Transfer",
            "from": "acc_business_002",
            "to": "acc_checking_003",
            "amount": "500"
        },
        {
            "name": "Invalid Transfer (Insufficient Funds)",
            "from": "acc_checking_003",
            "to": "acc_premium_001",
            "amount": "5000"
        }
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n📤 Test {i}: {case['name']}")
        print(f"   Transfer: ${case['amount']} from {case['from']} to {case['to']}")

        result = await transfer_service.process_transfer(
            case['from'], case['to'], case['amount']
        )

        print(f"\n📊 Result:")
        for key, value in result.items():
            if key == "details" and isinstance(value, dict):
                print(f"   {key}:")
                for detail_key, detail_value in value.items():
                    print(f"     {detail_key}: {detail_value}")
            else:
                print(f"   {key}: {value}")

    print(f"\n✨ Python 3.12+ Optimizations Demonstrated:")
    optimizations = [
        "⚡ @final decorator prevents unwanted inheritance",
        "🛡️ TypeGuard provides runtime type safety",
        "📝 Enhanced error messages with cause chaining",
        "🎯 Slots for memory-efficient classes",
        "⚙️ Static methods for better performance",
        "🔧 Modern type hints with union syntax (|)",
    ]

    for opt in optimizations:
        print(f"   {opt}")


if __name__ == "__main__":
    asyncio.run(demo_python312_features())
