"""Order query examples.

This module provides practical examples of using the specification pattern
for common order-related queries.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from infrastructure.persistence.specification.core.type import SortDirection

from idp.framework.infrastructure.persistence.specification import (
    SpecificationBuilder,
    FilterOperator,
    Specification
)

def find_recent_orders(days: int = 7) -> Specification:
    """Find orders created in the last N days.
    
    Args:
        days: Number of days to look back
        
    Returns:
        Specification for finding recent orders
    """
    return (SpecificationBuilder()
        .between(
            "created_at",
            datetime.now() - timedelta(days=days),
            datetime.now()
        )
        .select(
            "id", "order_number", "status",
            "total_amount", "created_at"
        )
        .include("customer.name", "items")
        .add_sort("created_at", direction=SortDirection.DESC)
        .build())

def find_orders_by_status(
    status: str,
    customer_id: Optional[UUID] = None,
    page: int = 0,
    size: int = 20
) -> Specification:
    """Find orders by status with optional customer filter.
    
    Args:
        status: Order status to filter by
        customer_id: Optional customer ID to filter by
        page: Page number (0-based)
        size: Page size
        
    Returns:
        Specification for finding orders by status
    """
    builder = (SpecificationBuilder()
        .filter("status", status)
        .select(
            "id", "order_number", "status",
            "total_amount", "created_at",
            "updated_at"
        )
        .include("customer", "items.product"))
    
    if customer_id:
        builder.filter("customer_id", customer_id)
    
    return (builder
        .add_sort("created_at", direction=SortDirection.DESC)
        .set_page(offset=page * size, limit=size)
        .build())

def search_orders(
    search_text: str,
    min_amount: Optional[Decimal] = None,
    max_amount: Optional[Decimal] = None,
    statuses: Optional[List[str]] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 0,
    size: int = 20
) -> Specification:
    """Search orders with various criteria.
    
    Args:
        search_text: Text to search in order number or customer name
        min_amount: Minimum order amount
        max_amount: Maximum order amount
        statuses: List of order statuses to include
        start_date: Start date for order creation
        end_date: End date for order creation
        page: Page number (0-based)
        size: Page size
        
    Returns:
        Specification for searching orders
    """
    builder = SpecificationBuilder()
    
    # Text search in order number or customer name
    builder.or_(
        lambda b: b.text_search("order_number", search_text),
        lambda b: b.text_search("customer.name", search_text)
    )
    
    # Amount range
    if min_amount is not None or max_amount is not None:
        builder.between(
            "total_amount",
            min_amount or Decimal('0'),
            max_amount or Decimal('999999999.99')
        )
    
    # Status filter
    if statuses:
        builder.where("status", "in", statuses)
    
    # Date range
    if start_date or end_date:
        builder.between(
            "created_at",
            start_date or datetime.min,
            end_date or datetime.now()
        )
    
    # Select fields and includes
    builder.select(
        "id", "order_number", "status",
        "total_amount", "created_at",
        "payment_status", "shipping_status"
    )
    
    builder.include(
        "customer.name",
        "customer.email",
        "items.product.name",
        "items.quantity",
        "items.unit_price"
    )
    
    # Sorting and pagination
    return (builder
        .add_sort("created_at", direction=SortDirection.DESC)
        .set_page(offset=page * size, limit=size)
        .build())

def find_order_statistics(
    start_date: datetime,
    end_date: datetime
) -> Specification:
    """Get order statistics for a date range.
    
    Args:
        start_date: Start date for analysis
        end_date: End date for analysis
        
    Returns:
        Specification for order statistics
    """
    return (SpecificationBuilder()
        # Date range filter
        .between("created_at", start_date, end_date)
        
        # Group by status and date
        .group_by("status", "DATE(created_at)")
        
        # Statistics
        .count("id", alias="order_count")
        .sum("total_amount", alias="total_sales")
        .avg("total_amount", alias="average_order_value")
        .count("customer_id", alias="unique_customers", distinct=True)
        
        # Having condition for meaningful groups
        .having("order_count", ">=", 5)
        
        # Sort by date and count
        .add_sort("DATE(created_at)")
        .add_sort("order_count", direction=SortDirection.DESC)
        .build())

def find_high_value_orders(
    threshold: Decimal,
    include_items: bool = True
) -> Specification:
    """Find high-value orders above a threshold.
    
    Args:
        threshold: Minimum order amount
        include_items: Whether to include order items
        
    Returns:
        Specification for finding high-value orders
    """
    builder = (SpecificationBuilder()
        # Amount threshold
        .where("total_amount", ">=", threshold)
        
        # Basic fields
        .select(
            "id", "order_number", "status",
            "total_amount", "created_at",
            "customer_id"
        ))
    
    # Include related data if requested
    if include_items:
        builder.include(
            "customer.name",
            "customer.vip_status",
            "items.product.name",
            "items.quantity",
            "items.unit_price"
        )
    
    return (builder
        .add_sort("total_amount", direction=SortDirection.DESC)
        .build())

def find_orders_not_matching_criteria(
    min_amount: Decimal,
    excluded_statuses: List[str],
    days_ago: int = 7
) -> Specification:
    """Find orders that don't match specific criteria.
    
    This demonstrates using not_() method with complex conditions.
    
    Args:
        min_amount: Minimum order amount threshold
        excluded_statuses: List of order statuses to exclude
        days_ago: Number of days to look back (default: 7)
        
    Returns:
        Specification for finding orders not matching criteria
    """
    return (SpecificationBuilder()
        # Base criteria
        .where("total_amount", ">=", min_amount)
        .where("status", "not_in", excluded_statuses)
        .where(
            "created_at",
            ">=",
            datetime.now() - timedelta(days=days_ago)
        )
        .select(
            "id", "order_number", "status",
            "total_amount", "created_at",
            "customer_id"
        )
        .include(
            "customer.name",
            "customer.email",
            "items.product.name",
            "items.quantity"
        )
        .add_sort("created_at", direction=SortDirection.DESC)
        .build())


# 基础条件（订单金额 >= 2000，30天内创建）
# 客户条件（VIP状态，积分 > 1000，VIP类别购买）
# 支付条件（支付验证，全额支付或分期）
def find_complex_orders(
    min_amount: Decimal,
    vip_categories: List[str],
    days_ago: int = 30
) -> Specification:
    """Find orders matching complex business rules using filter groups.
    
    Complex business rules:
    1. Base criteria:
       - Order amount >= minimum threshold
       - Created within specified days
       - Not deleted
       
    2. Customer criteria (ANY of):
       - VIP customer (status = 'vip')
       - Has loyalty points > 1000
       - Made purchases in VIP categories
       
    3. Payment criteria (ALL of):
       - Payment verified
       - Either:
         * Paid in full
         * (Has deposit AND scheduled payment)
    
    Args:
        min_amount: Minimum order amount threshold
        vip_categories: List of VIP product categories
        days_ago: Number of days to look back (default: 30)
        
    Returns:
        Specification for finding orders matching complex criteria
    """
    return (SpecificationBuilder()
        # Base criteria
        .and_(
            lambda b: b.where("total_amount", ">=", min_amount),
            lambda b: b.where(
                "created_at",
                ">=",
                datetime.now() - timedelta(days=days_ago)
            ),
            lambda b: b.where("is_deleted", "=", False)
        )
        
        # Customer criteria (OR group)
        .or_(
            lambda b: b.where("customer.status", "=", "vip"),
            lambda b: b.where("customer.loyalty_points", ">", 1000),
            lambda b: b.where("items.category", "in", vip_categories)
        )
        
        # Payment criteria (AND group with nested OR)
        .and_(
            lambda b: b.where("payment.is_verified", "=", True),
            lambda b: b.or_(
                lambda b: b.where("payment.status", "=", "paid"),
                lambda b: b.and_(
                    lambda b: b.where("payment.has_deposit", "=", True),
                    lambda b: b.where("payment.is_scheduled", "=", True)
                )
            )
        )
        
        # Select relevant fields
        .select(
            "id", "order_number", "total_amount",
            "created_at", "status", "payment_status"
        )
        
        # Include related data
        .include(
            "customer.status",
            "customer.loyalty_points",
            "items.category",
            "payment"
        )
        
        # Sort by amount and date
        .add_sort("total_amount", direction=SortDirection.DESC)
        .add_sort("created_at", direction=SortDirection.DESC)
        .build())