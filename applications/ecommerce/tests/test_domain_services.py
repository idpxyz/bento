"""Tests for order domain services.

This module demonstrates testing best practices for domain services:
- Testing business logic in isolation
- Parameterized tests for multiple scenarios
- Clear test names describing business rules
- Testing edge cases and boundary conditions
"""

import pytest

from applications.ecommerce.modules.order.domain.services import (
    CustomerTier,
    OrderPricingService,
    PricingContext,
)


class TestOrderPricingService:
    """Test OrderPricingService.

    Best Practices Demonstrated:
    - Test pure domain logic without infrastructure
    - Parameterized tests for multiple scenarios
    - Clear assertions on business rules
    - Test return value structure
    """

    def setup_method(self):
        """Set up test fixture."""
        self.pricing_service = OrderPricingService()

    # Test basic tier discounts

    def test_standard_tier_no_discount(self):
        """Test that standard tier gets no discount."""
        context = PricingContext(customer_tier=CustomerTier.STANDARD)
        result = self.pricing_service.calculate_total(100.0, context)

        assert result["subtotal"] == 100.0
        assert result["tier_discount"] == 0.0
        assert result["final_total"] == 100.0

    def test_silver_tier_5_percent_discount(self):
        """Test that silver tier gets 5% discount."""
        context = PricingContext(customer_tier=CustomerTier.SILVER)
        result = self.pricing_service.calculate_total(100.0, context)

        assert result["subtotal"] == 100.0
        assert result["tier_discount"] == 5.0  # 5% of 100
        assert result["final_total"] == 95.0

    def test_gold_tier_10_percent_discount(self):
        """Test that gold tier gets 10% discount."""
        context = PricingContext(customer_tier=CustomerTier.GOLD)
        result = self.pricing_service.calculate_total(100.0, context)

        assert result["subtotal"] == 100.0
        assert result["tier_discount"] == 10.0  # 10% of 100
        assert result["final_total"] == 90.0

    def test_platinum_tier_15_percent_discount(self):
        """Test that platinum tier gets 15% discount."""
        context = PricingContext(customer_tier=CustomerTier.PLATINUM)
        result = self.pricing_service.calculate_total(100.0, context)

        assert result["subtotal"] == 100.0
        assert result["tier_discount"] == 15.0  # 15% of 100
        assert result["final_total"] == 85.0

    # Test first order discount

    def test_first_order_gets_10_percent_discount(self):
        """Test that first order gets additional 10% discount."""
        context = PricingContext(customer_tier=CustomerTier.STANDARD, is_first_order=True)
        result = self.pricing_service.calculate_total(100.0, context)

        assert result["first_order_discount"] == 10.0
        assert result["final_total"] == 90.0

    def test_first_order_with_tier_stacks_discounts(self):
        """Test that first order discount stacks with tier discount."""
        context = PricingContext(
            customer_tier=CustomerTier.GOLD,  # 10% tier discount
            is_first_order=True,  # 10% first order discount
        )
        result = self.pricing_service.calculate_total(100.0, context)

        assert result["tier_discount"] == 10.0
        assert result["first_order_discount"] == 10.0
        assert result["total_discount"] == 20.0
        assert result["final_total"] == 80.0

    # Test bulk order discount

    def test_bulk_order_over_threshold_gets_discount(self):
        """Test that orders over $1000 get bulk discount."""
        context = PricingContext(customer_tier=CustomerTier.STANDARD)
        result = self.pricing_service.calculate_total(1500.0, context)

        assert result["bulk_discount"] == 75.0  # 5% of 1500
        assert result["final_total"] == 1425.0

    def test_bulk_order_at_threshold_gets_discount(self):
        """Test that order exactly at $1000 gets bulk discount."""
        context = PricingContext(customer_tier=CustomerTier.STANDARD)
        result = self.pricing_service.calculate_total(1000.0, context)

        assert result["bulk_discount"] == 50.0  # 5% of 1000
        assert result["final_total"] == 950.0

    def test_order_below_threshold_no_bulk_discount(self):
        """Test that orders under $1000 don't get bulk discount."""
        context = PricingContext(customer_tier=CustomerTier.STANDARD)
        result = self.pricing_service.calculate_total(999.0, context)

        assert result["bulk_discount"] == 0.0
        assert result["final_total"] == 999.0

    # Test promotion codes

    def test_valid_promotion_code_applies_discount(self):
        """Test that valid promotion code applies discount."""
        context = PricingContext(customer_tier=CustomerTier.STANDARD, promotion_code="WELCOME10")
        result = self.pricing_service.calculate_total(100.0, context)

        assert result["promotion_discount"] == 10.0
        assert result["final_total"] == 90.0

    def test_promotion_code_case_insensitive(self):
        """Test that promotion codes are case-insensitive."""
        context = PricingContext(customer_tier=CustomerTier.STANDARD, promotion_code="welcome10")
        result = self.pricing_service.calculate_total(100.0, context)

        assert result["promotion_discount"] == 10.0

    def test_invalid_promotion_code_no_discount(self):
        """Test that invalid promotion code doesn't apply discount."""
        context = PricingContext(customer_tier=CustomerTier.STANDARD, promotion_code="INVALID")
        result = self.pricing_service.calculate_total(100.0, context)

        assert result["promotion_discount"] == 0.0
        assert result["final_total"] == 100.0

    # Test stacking of multiple discounts

    def test_all_discounts_stack_correctly(self):
        """Test that all applicable discounts stack correctly.

        Demonstrates:
        - Complex business rule testing
        - Multiple discount types
        - Real-world scenario
        """
        context = PricingContext(
            customer_tier=CustomerTier.PLATINUM,  # 15% tier discount
            is_first_order=True,  # 10% first order
            promotion_code="SAVE20",  # 20% promo code
        )
        result = self.pricing_service.calculate_total(2000.0, context)

        # 15% + 10% + 5% (bulk) + 20% = 50% total discount
        assert result["tier_discount"] == 300.0  # 15% of 2000
        assert result["first_order_discount"] == 200.0  # 10% of 2000
        assert result["bulk_discount"] == 100.0  # 5% of 2000
        assert result["promotion_discount"] == 400.0  # 20% of 2000
        assert result["total_discount"] == 1000.0
        assert result["final_total"] == 1000.0

    # Test helper methods

    def test_calculate_tier_discount_isolated(self):
        """Test tier discount calculation in isolation."""
        discount = self.pricing_service.calculate_tier_discount(200.0, CustomerTier.GOLD)
        assert discount == 20.0  # 10% of 200

    def test_is_eligible_for_bulk_discount_true(self):
        """Test bulk discount eligibility - eligible."""
        assert self.pricing_service.is_eligible_for_bulk_discount(1000.0) is True
        assert self.pricing_service.is_eligible_for_bulk_discount(1500.0) is True

    def test_is_eligible_for_bulk_discount_false(self):
        """Test bulk discount eligibility - not eligible."""
        assert self.pricing_service.is_eligible_for_bulk_discount(999.0) is False
        assert self.pricing_service.is_eligible_for_bulk_discount(500.0) is False

    def test_validate_promotion_code_valid(self):
        """Test promotion code validation - valid codes."""
        is_valid, rate = self.pricing_service.validate_promotion_code("WELCOME10")
        assert is_valid is True
        assert rate == 0.10

        is_valid, rate = self.pricing_service.validate_promotion_code("SAVE20")
        assert is_valid is True
        assert rate == 0.20

    def test_validate_promotion_code_invalid(self):
        """Test promotion code validation - invalid codes."""
        is_valid, rate = self.pricing_service.validate_promotion_code("INVALID")
        assert is_valid is False
        assert rate == 0.0

    def test_validate_promotion_code_empty(self):
        """Test promotion code validation - empty code."""
        is_valid, rate = self.pricing_service.validate_promotion_code("")
        assert is_valid is False
        assert rate == 0.0

    # Test savings calculation

    def test_calculate_savings_with_discount(self):
        """Test savings calculation when discount is applied."""
        savings = self.pricing_service.calculate_savings(100.0, 80.0)

        assert savings["original_total"] == 100.0
        assert savings["discounted_total"] == 80.0
        assert savings["savings_amount"] == 20.0
        assert savings["savings_percentage"] == 20.0
        assert "You saved $20.00 (20.0%)" in savings["you_saved"]

    def test_calculate_savings_no_discount(self):
        """Test savings calculation when no discount applied."""
        savings = self.pricing_service.calculate_savings(100.0, 100.0)

        assert savings["savings_amount"] == 0.0
        assert savings["savings_percentage"] == 0.0

    # Test tier benefits

    def test_get_tier_benefits_gold(self):
        """Test getting benefits for gold tier."""
        benefits = self.pricing_service.get_tier_benefits(CustomerTier.GOLD)

        assert benefits["tier"] == "gold"
        assert benefits["discount_percentage"] == 10.0
        assert "additional_benefits" in benefits
        assert "Free shipping" in benefits["additional_benefits"][0]

    def test_get_tier_benefits_platinum(self):
        """Test getting benefits for platinum tier."""
        benefits = self.pricing_service.get_tier_benefits(CustomerTier.PLATINUM)

        assert benefits["tier"] == "platinum"
        assert benefits["discount_percentage"] == 15.0
        assert "additional_benefits" in benefits
        assert len(benefits["additional_benefits"]) == 4

    # Test tier upgrade recommendations

    def test_recommend_tier_upgrade_qualifies(self):
        """Test tier upgrade recommendation when customer qualifies."""
        recommendation = self.pricing_service.recommend_tier_upgrade(
            CustomerTier.STANDARD,
            annual_spending=5000.0,  # Qualifies for GOLD
        )

        assert recommendation is not None
        assert recommendation["recommended_tier"] == "gold"
        assert recommendation["current_tier"] == "standard"
        assert recommendation["annual_spending"] == 5000.0
        assert recommendation["additional_annual_savings"] > 0

    def test_recommend_tier_upgrade_no_qualification(self):
        """Test tier upgrade recommendation when customer doesn't qualify."""
        recommendation = self.pricing_service.recommend_tier_upgrade(
            CustomerTier.STANDARD,
            annual_spending=500.0,  # Below SILVER threshold
        )

        assert recommendation is None

    def test_recommend_tier_upgrade_already_max_tier(self):
        """Test no upgrade recommendation for platinum customers."""
        recommendation = self.pricing_service.recommend_tier_upgrade(
            CustomerTier.PLATINUM, annual_spending=50000.0
        )

        assert recommendation is None

    # Test edge cases

    def test_zero_subtotal(self):
        """Test handling of zero subtotal."""
        context = PricingContext(customer_tier=CustomerTier.GOLD)
        result = self.pricing_service.calculate_total(0.0, context)

        assert result["final_total"] == 0.0
        assert result["total_discount"] == 0.0

    def test_negative_subtotal_prevented(self):
        """Test that final total doesn't go negative (edge case).

        Note: In practice, negative subtotals shouldn't happen,
        but service should handle gracefully.
        """
        context = PricingContext(customer_tier=CustomerTier.STANDARD)
        # Hypothetical edge case
        result = self.pricing_service.calculate_total(0.01, context)

        assert result["final_total"] >= 0.0

    def test_very_large_order(self):
        """Test handling of very large orders."""
        context = PricingContext(customer_tier=CustomerTier.PLATINUM)
        result = self.pricing_service.calculate_total(100000.0, context)

        # Should handle large numbers correctly
        assert result["tier_discount"] == 15000.0  # 15%
        assert result["bulk_discount"] == 5000.0  # 5%
        assert result["final_total"] == 80000.0


class TestPricingContext:
    """Test PricingContext dataclass.

    Best Practices:
    - Test data structures used in domain services
    - Verify default values
    - Test immutability if needed
    """

    def test_pricing_context_defaults(self):
        """Test default values of PricingContext."""
        context = PricingContext()

        assert context.customer_tier == CustomerTier.STANDARD
        assert context.is_first_order is False
        assert context.order_date is None
        assert context.promotion_code is None

    def test_pricing_context_with_values(self):
        """Test PricingContext with explicit values."""
        context = PricingContext(
            customer_tier=CustomerTier.GOLD,
            is_first_order=True,
            promotion_code="SAVE20",
        )

        assert context.customer_tier == CustomerTier.GOLD
        assert context.is_first_order is True
        assert context.promotion_code == "SAVE20"


# Parameterized tests for comprehensive coverage
class TestPricingServiceParameterized:
    """Parameterized tests for pricing service.

    Demonstrates:
    - Testing multiple scenarios efficiently
    - Data-driven testing
    - Comprehensive coverage with less code
    """

    @pytest.mark.parametrize(
        "tier,expected_discount_rate",
        [
            (CustomerTier.STANDARD, 0.0),
            (CustomerTier.SILVER, 0.05),
            (CustomerTier.GOLD, 0.10),
            (CustomerTier.PLATINUM, 0.15),
        ],
    )
    def test_tier_discount_rates(self, tier, expected_discount_rate):
        """Test all tier discount rates with parameterized test."""
        pricing_service = OrderPricingService()
        discount = pricing_service.calculate_tier_discount(100.0, tier)
        expected_discount = 100.0 * expected_discount_rate

        assert discount == expected_discount

    @pytest.mark.parametrize(
        "subtotal,expected_eligible",
        [
            (999.0, False),
            (1000.0, True),
            (1001.0, True),
            (5000.0, True),
        ],
    )
    def test_bulk_eligibility_boundaries(self, subtotal, expected_eligible):
        """Test bulk discount eligibility at various price points."""
        pricing_service = OrderPricingService()
        is_eligible = pricing_service.is_eligible_for_bulk_discount(subtotal)

        assert is_eligible == expected_eligible

    @pytest.mark.parametrize(
        "promo_code,expected_rate",
        [
            ("WELCOME10", 0.10),
            ("SAVE20", 0.20),
            ("VIP30", 0.30),
            ("INVALID", 0.0),
            ("", 0.0),
        ],
    )
    def test_promotion_codes(self, promo_code, expected_rate):
        """Test various promotion codes."""
        pricing_service = OrderPricingService()
        is_valid, rate = pricing_service.validate_promotion_code(promo_code)

        if expected_rate > 0:
            assert is_valid is True
        else:
            assert is_valid is False
        assert rate == expected_rate
