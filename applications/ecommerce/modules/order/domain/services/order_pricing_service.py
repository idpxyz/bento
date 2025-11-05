"""Order pricing domain service.

This module demonstrates Domain Service best practices:
- Encapsulates complex business logic that spans multiple aggregates
- Stateless - operates on provided data
- Pure domain logic - no infrastructure dependencies
- Reusable across different use cases
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class CustomerTier(str, Enum):
    """Customer membership tier."""

    STANDARD = "standard"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


@dataclass
class PricingContext:
    """Context for pricing calculations.

    Best Practice:
    - Encapsulate all inputs needed for pricing
    - Makes pricing logic testable and deterministic
    - Explicit dependencies
    """

    customer_tier: CustomerTier = CustomerTier.STANDARD
    is_first_order: bool = False
    order_date: datetime | None = None
    promotion_code: str | None = None


class OrderPricingService:
    """Domain service for order pricing calculations.

    This service demonstrates:
    - Cross-aggregate business logic (Order + Customer + Promotion)
    - Complex pricing rules
    - Stateless service design
    - Pure domain logic

    Best Practices:
    - Domain services are stateless
    - They operate on aggregates but don't own them
    - Complex logic that doesn't fit naturally in a single aggregate
    - Pure functions - same input always produces same output

    Example:
        ```python
        pricing_service = OrderPricingService()
        context = PricingContext(
            customer_tier=CustomerTier.GOLD,
            is_first_order=True
        )

        subtotal = 1000.0
        total = pricing_service.calculate_total(subtotal, context)
        # Returns discounted total based on customer tier and promotions
        ```
    """

    # Pricing rules (normally from configuration or database)
    TIER_DISCOUNTS = {
        CustomerTier.STANDARD: 0.0,  # No discount
        CustomerTier.SILVER: 0.05,  # 5% off
        CustomerTier.GOLD: 0.10,  # 10% off
        CustomerTier.PLATINUM: 0.15,  # 15% off
    }

    FIRST_ORDER_DISCOUNT = 0.10  # 10% off for first order
    BULK_ORDER_THRESHOLD = 1000.0  # Orders over $1000
    BULK_ORDER_DISCOUNT = 0.05  # 5% off for bulk orders

    PROMOTION_CODES = {
        "WELCOME10": 0.10,  # 10% off
        "SAVE20": 0.20,  # 20% off
        "VIP30": 0.30,  # 30% off
    }

    def calculate_total(self, subtotal: float, context: PricingContext) -> dict[str, float]:
        """Calculate final order total with all discounts applied.

        Args:
            subtotal: Order subtotal before discounts
            context: Pricing context with customer and promotion info

        Returns:
            Dictionary containing:
            - subtotal: Original subtotal
            - tier_discount: Discount from customer tier
            - first_order_discount: First order discount
            - bulk_discount: Bulk order discount
            - promotion_discount: Promotion code discount
            - total_discount: Sum of all discounts
            - final_total: Final amount after all discounts

        Best Practice:
        - Return detailed breakdown for transparency
        - Show how final price was calculated
        - Helps with customer communication and debugging
        """
        # Start with subtotal
        total = subtotal
        discounts = {
            "subtotal": subtotal,
            "tier_discount": 0.0,
            "first_order_discount": 0.0,
            "bulk_discount": 0.0,
            "promotion_discount": 0.0,
        }

        # Apply tier discount
        tier_discount_rate = self.TIER_DISCOUNTS.get(context.customer_tier, 0.0)
        if tier_discount_rate > 0:
            tier_discount = subtotal * tier_discount_rate
            discounts["tier_discount"] = tier_discount
            total -= tier_discount

        # Apply first order discount
        if context.is_first_order:
            first_order_discount = subtotal * self.FIRST_ORDER_DISCOUNT
            discounts["first_order_discount"] = first_order_discount
            total -= first_order_discount

        # Apply bulk order discount
        if subtotal >= self.BULK_ORDER_THRESHOLD:
            bulk_discount = subtotal * self.BULK_ORDER_DISCOUNT
            discounts["bulk_discount"] = bulk_discount
            total -= bulk_discount

        # Apply promotion code discount
        if context.promotion_code:
            promo_rate = self.PROMOTION_CODES.get(context.promotion_code.upper(), 0.0)
            if promo_rate > 0:
                promotion_discount = subtotal * promo_rate
                discounts["promotion_discount"] = promotion_discount
                total -= promotion_discount

        # Calculate total discount and ensure non-negative
        total_discount = sum(
            [
                discounts["tier_discount"],
                discounts["first_order_discount"],
                discounts["bulk_discount"],
                discounts["promotion_discount"],
            ]
        )

        # Ensure total doesn't go negative
        final_total = max(0.0, total)

        return {
            **discounts,
            "total_discount": total_discount,
            "final_total": round(final_total, 2),
        }

    def calculate_tier_discount(self, subtotal: float, customer_tier: CustomerTier) -> float:
        """Calculate discount based on customer tier.

        Args:
            subtotal: Order subtotal
            customer_tier: Customer's membership tier

        Returns:
            Discount amount

        Best Practice:
        - Isolated calculation for testing
        - Single responsibility
        - Reusable in different contexts
        """
        discount_rate = self.TIER_DISCOUNTS.get(customer_tier, 0.0)
        return subtotal * discount_rate

    def is_eligible_for_bulk_discount(self, subtotal: float) -> bool:
        """Check if order qualifies for bulk discount.

        Args:
            subtotal: Order subtotal

        Returns:
            True if eligible for bulk discount

        Best Practice:
        - Explicit business rule
        - Easy to test
        - Clear intent
        """
        return subtotal >= self.BULK_ORDER_THRESHOLD

    def validate_promotion_code(self, code: str) -> tuple[bool, float]:
        """Validate promotion code and get discount rate.

        Args:
            code: Promotion code to validate

        Returns:
            Tuple of (is_valid, discount_rate)

        Best Practice:
        - Return both validation result and value
        - Avoid multiple lookups
        - Clear return type
        """
        if not code:
            return False, 0.0

        discount_rate = self.PROMOTION_CODES.get(code.upper(), 0.0)
        return discount_rate > 0, discount_rate

    def calculate_savings(self, original_total: float, discounted_total: float) -> dict[str, Any]:
        """Calculate savings information for customer.

        Args:
            original_total: Original price before discounts
            discounted_total: Final price after discounts

        Returns:
            Dictionary with savings amount and percentage

        Best Practice:
        - Provide customer-facing information
        - Show value of membership/promotions
        - Marketing insights
        """
        savings_amount = original_total - discounted_total
        savings_percentage = (savings_amount / original_total * 100) if original_total > 0 else 0.0

        return {
            "original_total": round(original_total, 2),
            "discounted_total": round(discounted_total, 2),
            "savings_amount": round(savings_amount, 2),
            "savings_percentage": round(savings_percentage, 1),
            "you_saved": f"You saved ${savings_amount:.2f} ({savings_percentage:.1f}%)",
        }

    def get_tier_benefits(self, customer_tier: CustomerTier) -> dict[str, Any]:
        """Get benefits information for a customer tier.

        Args:
            customer_tier: Customer's membership tier

        Returns:
            Dictionary with tier benefits

        Best Practice:
        - Encapsulate tier logic
        - Support customer education
        - Marketing material generation
        """
        discount_rate = self.TIER_DISCOUNTS.get(customer_tier, 0.0)
        discount_percentage = discount_rate * 100

        benefits = {
            "tier": customer_tier.value,
            "discount_percentage": discount_percentage,
            "description": f"{discount_percentage}% off all orders",
        }

        # Add tier-specific benefits
        if customer_tier == CustomerTier.GOLD:
            benefits["additional_benefits"] = [
                "Free shipping on orders over $100",
                "Priority customer support",
                "Early access to sales",
            ]
        elif customer_tier == CustomerTier.PLATINUM:
            benefits["additional_benefits"] = [
                "Free shipping on all orders",
                "Dedicated account manager",
                "Exclusive products",
                "Birthday gifts",
            ]

        return benefits

    def recommend_tier_upgrade(
        self, current_tier: CustomerTier, annual_spending: float
    ) -> dict[str, Any] | None:
        """Recommend tier upgrade based on spending.

        Args:
            current_tier: Customer's current tier
            annual_spending: Total spending in past year

        Returns:
            Upgrade recommendation or None

        Best Practice:
        - Proactive customer engagement
        - Data-driven recommendations
        - Demonstrate value of upgrades
        """
        # Define tier thresholds (in annual spending)
        tier_thresholds = {
            CustomerTier.SILVER: 1000.0,
            CustomerTier.GOLD: 5000.0,
            CustomerTier.PLATINUM: 10000.0,
        }

        # Find the highest tier customer qualifies for
        recommended_tier = None
        for tier, threshold in tier_thresholds.items():
            if annual_spending >= threshold and self._tier_level(current_tier) < self._tier_level(
                tier
            ):
                # Keep checking for higher tiers
                if recommended_tier is None or self._tier_level(tier) > self._tier_level(
                    recommended_tier
                ):
                    recommended_tier = tier

        # If a recommendation was found, calculate savings
        if recommended_tier:
            current_discount = self.TIER_DISCOUNTS[current_tier]
            new_discount = self.TIER_DISCOUNTS[recommended_tier]
            additional_savings = (new_discount - current_discount) * annual_spending

            return {
                "recommended_tier": recommended_tier.value,
                "current_tier": current_tier.value,
                "annual_spending": annual_spending,
                "additional_annual_savings": round(additional_savings, 2),
                "message": (
                    f"Upgrade to {recommended_tier.value.title()} tier and save an additional "
                    f"${additional_savings:.2f} per year!"
                ),
            }

        return None

    @staticmethod
    def _tier_level(tier: CustomerTier) -> int:
        """Get numeric level for tier comparison.

        Helper method for tier comparisons.
        """
        tier_levels = {
            CustomerTier.STANDARD: 0,
            CustomerTier.SILVER: 1,
            CustomerTier.GOLD: 2,
            CustomerTier.PLATINUM: 3,
        }
        return tier_levels.get(tier, 0)
