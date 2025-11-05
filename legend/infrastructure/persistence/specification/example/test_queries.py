"""Test script for demonstrating query examples.

This module shows how to use the specification pattern with mock data
and prints the results to the console.
"""

from copy import deepcopy
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

from rich import print

from idp.framework.infrastructure.persistence.specification import (
    FilterOperator,
    Specification,
)
from idp.framework.infrastructure.persistence.specification.example.order_queries import (
    find_complex_orders,
    find_high_value_orders,
    find_order_statistics,
    find_orders_by_status,
    find_orders_not_matching_criteria,
    find_recent_orders,
    search_orders,
)
from idp.framework.infrastructure.persistence.specification.example.product_queries import (
    find_available_products,
    find_trending_products,
    search_products,
)
from idp.framework.infrastructure.persistence.specification.example.user_queries import (
    find_active_users,
    find_users_by_role,
    search_users,
)


class MockRepository:
    """Mock repository for demonstration purposes."""

    def __init__(self):
        """Initialize with sample data."""
        self.users = [
            {
                "id": str(uuid4()),
                "name": "John Doe",
                "email": "john.doe@example.com",
                "role": "admin",
                "age": 35,
                "is_active": True,
                "created_at": datetime.now() - timedelta(days=15),
                "last_login": datetime.now() - timedelta(hours=2),
                "profile": {
                    "department": "IT",
                    "location": "New York"
                },
                "permissions": ["read", "write", "admin"]
            },
            {
                "id": str(uuid4()),
                "name": "Jane Smith",
                "email": "jane.smith@example.com",
                "role": "manager",
                "age": 42,
                "is_active": True,
                "created_at": datetime.now() - timedelta(days=5),
                "last_login": datetime.now() - timedelta(minutes=30),
                "profile": {
                    "department": "Sales",
                    "location": "London"
                },
                "permissions": ["read", "write"]
            }
        ]

        self.orders = [
            # ORD-001：VIP客户的高端奢侈品订单，已完全支付
            {
                "id": str(uuid4()),
                "order_number": "ORD-001",
                "status": "completed",
                "total_amount": Decimal("2500.00"),
                "created_at": datetime.now() - timedelta(days=3),
                "payment_status": "paid",
                "shipping_status": "delivered",
                "customer": {
                    "name": "John Doe",
                    "email": "john.doe@example.com",
                    "status": "vip",
                    "loyalty_points": 1500
                },
                "items": [
                    {
                        "product": {
                            "name": "Luxury Watch",
                            "sku": "LUX-001",
                            "category": "luxury"
                        },
                        "quantity": 1,
                        "unit_price": Decimal("2500.00")
                    }
                ],
                "payment": {
                    "is_verified": True,
                    "method": "credit_card",
                    "status": "completed",
                    "amount_paid": Decimal("2500.00")
                }
            },
            # ORD-002：普通客户的分期付款订单，部分支付
            {
                "id": str(uuid4()),
                "order_number": "ORD-002",
                "status": "processing",
                "total_amount": Decimal("3500.00"),
                "created_at": datetime.now() - timedelta(days=1),
                "payment_status": "partially_paid",
                "shipping_status": "pending",
                "customer": {
                    "name": "Jane Smith",
                    "email": "jane.smith@example.com",
                    "status": "regular",
                    "loyalty_points": 800
                },
                "items": [
                    {
                        "product": {
                            "name": "Premium Smartphone",
                            "sku": "PRE-001",
                            "category": "premium"
                        },
                        "quantity": 2,
                        "unit_price": Decimal("1750.00")
                    }
                ],
                "payment": {
                    "is_verified": True,
                    "method": "installment",
                    "status": "partial",
                    "amount_paid": Decimal("1000.00"),
                    "payment_plan": {
                        "total_installments": 6,
                        "paid_installments": 1,
                        "amount_per_installment": Decimal("416.67")
                    }
                }
            }
        ]

        self.products = [
            {
                "id": str(uuid4()),
                "sku": "LAP-001",
                "name": "Gaming Laptop",
                "description": "High-performance gaming laptop",
                "category": "electronics",
                "price": Decimal("1299.99"),
                "stock_level": 15,
                "rating": 4.8,
                "review_count": 25,
                "is_active": True,
                "tags": ["gaming", "portable", "high-performance"],
                "images": ["laptop1.jpg", "laptop2.jpg"],
                "variants": [
                    {
                        "sku": "LAP-001-8GB",
                        "name": "8GB RAM",
                        "stock_level": 8
                    },
                    {
                        "sku": "LAP-001-16GB",
                        "name": "16GB RAM",
                        "stock_level": 7
                    }
                ],
                "manufacturer": {
                    "name": "TechCorp",
                    "country": "USA"
                },
                "reviews": [
                    {
                        "rating": 5,
                        "comment": "Excellent performance!"
                    },
                    {
                        "rating": 4,
                        "comment": "Good but expensive"
                    }
                ]
            },
            {
                "id": str(uuid4()),
                "sku": "PHN-001",
                "name": "Smartphone",
                "description": "Latest smartphone model",
                "category": "electronics",
                "price": Decimal("799.99"),
                "stock_level": 8,
                "rating": 4.5,
                "review_count": 15,
                "is_active": True,
                "tags": ["mobile", "5g", "camera"],
                "images": ["phone1.jpg", "phone2.jpg"],
                "variants": [
                    {
                        "sku": "PHN-001-128GB",
                        "name": "128GB Storage",
                        "stock_level": 5
                    },
                    {
                        "sku": "PHN-001-256GB",
                        "name": "256GB Storage",
                        "stock_level": 3
                    }
                ],
                "manufacturer": {
                    "name": "MobileCorp",
                    "country": "Korea"
                },
                "reviews": [
                    {
                        "rating": 5,
                        "comment": "Great camera!"
                    },
                    {
                        "rating": 4,
                        "comment": "Good battery life"
                    }
                ]
            }
        ]

    # 获取嵌套字典的值
    def _get_nested_value(self, obj: Dict[str, Any], field: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        parts = field.split('.')
        value = obj
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value

    # 应用过滤器
    def _apply_filter(self, data: List[Dict[str, Any]], filter_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply filters to data."""
        filtered_data = []

        for item in data:
            matches = True
            for filter_item in filter_params.get('filters', []):
                field = filter_item.field
                op = filter_item.operator
                value = filter_item.value

                item_value = self._get_nested_value(item, field)

                # Skip comparison if item value is None
                if item_value is None:
                    matches = False
                    break

                try:
                    if op == FilterOperator.EQUALS:
                        matches = matches and item_value == value
                    elif op == FilterOperator.NOT_EQUALS:
                        matches = matches and item_value != value
                    elif op == FilterOperator.GREATER_THAN:
                        matches = matches and item_value > value
                    elif op == FilterOperator.GREATER_EQUAL:
                        matches = matches and item_value >= value
                    elif op == FilterOperator.LESS_THAN:
                        matches = matches and item_value < value
                    elif op == FilterOperator.LESS_EQUAL:
                        matches = matches and item_value <= value
                    elif op == FilterOperator.IN:
                        matches = matches and item_value in value
                    elif op == FilterOperator.NOT_IN:
                        matches = matches and item_value not in value
                    elif op == FilterOperator.BETWEEN:
                        start_val = value.get('start')
                        end_val = value.get('end')
                        if start_val is not None and end_val is not None:
                            matches = matches and start_val <= item_value <= end_val
                        elif start_val is not None:
                            matches = matches and start_val <= item_value
                        elif end_val is not None:
                            matches = matches and item_value <= end_val
                        else:
                            matches = False
                    elif op == FilterOperator.ILIKE:
                        if isinstance(item_value, str) and isinstance(value, str):
                            matches = matches and value.replace(
                                '%', '').lower() in item_value.lower()
                        else:
                            matches = False
                    elif op == FilterOperator.ARRAY_CONTAINS:
                        if isinstance(item_value, list) and isinstance(value, list):
                            matches = matches and all(
                                v in item_value for v in value)
                        else:
                            matches = False
                except TypeError:
                    # If comparison fails (e.g., comparing str with int)
                    matches = False
                    break

            if matches:
                filtered_data.append(deepcopy(item))

        return filtered_data

    # 应用排序
    def _apply_sort(self, data: List[Dict[str, Any]], sort_params: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply sorting to data."""
        if not sort_params:
            return data

        def sort_key(item):
            keys = []
            for sort_item in sort_params:
                value = self._get_nested_value(item, sort_item.field)
                # Handle None values in sorting
                if value is None:
                    value = "" if sort_item.ascending else "zzz"  # Put None values at start or end
                keys.append((value, sort_item.ascending))
            return keys

        return sorted(
            data,
            key=sort_key,
            reverse=not all(s.ascending for s in sort_params)
        )

    # 应用分页
    def _apply_pagination(self, data: List[Dict[str, Any]], page_params: Optional[Dict[str, int]]) -> List[Dict[str, Any]]:
        """Apply pagination to data."""
        if not page_params:
            return data

        page = getattr(page_params, 'page', 1)
        size = getattr(page_params, 'size', len(data))
        offset = (page - 1) * size
        return data[offset:offset + size]

    # 选择特定字段
    def _select_fields(self, data: List[Dict[str, Any]], fields: List[str]) -> List[Dict[str, Any]]:
        """Select specific fields from data."""
        if not fields:
            return data

        result = []
        for item in data:
            new_item = {}
            for field in fields:
                value = self._get_nested_value(item, field)
                if value is not None:
                    parts = field.split('.')
                    current = new_item
                    for part in parts[:-1]:
                        current = current.setdefault(part, {})
                    current[parts[-1]] = value
            result.append(new_item)
        return result

    # 计算统计数据
    def _calculate_statistics(self, data: List[Dict[str, Any]], params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistics based on specification."""
        stats = {}

        if not data:
            return stats

        for key, value in params.items():
            if key.startswith('count_'):
                field = value['field']
                if value.get('distinct'):
                    stats[value['alias']] = len(set(
                        str(self._get_nested_value(item, field))
                        for item in data
                    ))
                else:
                    stats[value['alias']] = len(data)
            elif key.startswith('sum_'):
                field = value['field']
                stats[value['alias']] = sum(
                    self._get_nested_value(item, field) or 0
                    for item in data
                )
            elif key.startswith('avg_'):
                field = value['field']
                values = [
                    self._get_nested_value(item, field)
                    for item in data
                    if self._get_nested_value(item, field) is not None
                ]
                if values:
                    stats[value['alias']] = sum(values) / len(values)
                else:
                    stats[value['alias']] = 0
            elif key.startswith('min_'):
                field = value['field']
                values = [
                    self._get_nested_value(item, field)
                    for item in data
                    if self._get_nested_value(item, field) is not None
                ]
                if values:
                    stats[value['alias']] = min(values)
            elif key.startswith('max_'):
                field = value['field']
                values = [
                    self._get_nested_value(item, field)
                    for item in data
                    if self._get_nested_value(item, field) is not None
                ]
                if values:
                    stats[value['alias']] = max(values)

        return stats

    # 包含关系
    def _include_relations(self, data: List[Dict[str, Any]], includes: List[str]) -> List[Dict[str, Any]]:
        """Include related data based on includes parameter."""
        if not includes:
            return data

        result = []
        for item in deepcopy(data):
            new_item = deepcopy(item)
            for include in includes:
                value = self._get_nested_value(item, include)
                if value is not None:
                    # Build nested structure
                    parts = include.split('.')
                    current = new_item
                    for part in parts[:-1]:
                        current = current.setdefault(part, {})
                    current[parts[-1]] = value
            result.append(new_item)
        return result

    # 应用规范
    def apply_specification(self, spec: Specification) -> Dict[str, Any]:
        """Apply specification to mock data and return results."""
        params = spec.to_query_params()

        # Determine which dataset to use based on the query
        query_str = str(params)
        if any(key in query_str for key in ['role', 'email', 'permissions']):
            data = deepcopy(self.users)
        elif any(key in query_str for key in ['order_number', 'total_amount', 'customer']):
            data = deepcopy(self.orders)
        else:
            data = deepcopy(self.products)

        # Apply filters
        filtered_data = self._apply_filter(data, params)

        # Apply sorting
        sorted_data = self._apply_sort(filtered_data, params.get('sorts', []))

        # Include relations if specified
        if 'includes' in params:
            sorted_data = self._include_relations(
                sorted_data, params['includes'])

        # Select fields
        if 'fields' in params:
            selected_data = self._select_fields(sorted_data, params['fields'])
        else:
            selected_data = sorted_data

        # Apply pagination
        if 'page' in params:
            paginated_data = self._apply_pagination(
                selected_data, params['page'])
        else:
            paginated_data = selected_data

        # Calculate statistics if requested
        stats = {}
        if any(key.startswith(('count_', 'sum_', 'avg_', 'min_', 'max_')) for key in params):
            stats = self._calculate_statistics(filtered_data, params)

        return {
            "query_params": params,
            "mock_data": paginated_data,
            **({"statistics": stats} if stats else {})
        }

# 格式化值


def format_value(value: Any) -> str:
    """Format a value for display."""
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {format_value(v)}" for k, v in value.items()) + "}"
    elif isinstance(value, list):
        return "[" + ", ".join(format_value(v) for v in value) + "]"
    elif isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(value, Decimal):
        return f"{value:.2f}"
    else:
        return str(value)

# 打印查询结果


def print_query_result(name: str, spec: Specification) -> None:
    """Print a specification's query parameters and mock results."""
    print("\n" + "=" * 100)
    print(f"{name:^100}")
    print("=" * 100 + "\n")

    # Create mock repository and apply specification
    repo = MockRepository()
    result = repo.apply_specification(spec)

    # Print query parameters
    print("QUERY PARAMETERS")
    print("-" * 100)
    params = result["query_params"]

    if "filters" in params:
        print("\nFilters:")
        for f in params["filters"]:
            value = format_value(f.value)
            print(f"  - {f.field:<20} {f.operator.value:<10} {value}")

    if "sorts" in params:
        print("\nSorts:")
        for s in params["sorts"]:
            print(f"  - {s.field:<20} {'ASC' if s.ascending else 'DESC'}")

    if "fields" in params:
        print("\nFields:")
        # Split fields into chunks of 5 for better readability
        fields = params["fields"]
        for i in range(0, len(fields), 5):
            chunk = fields[i:i + 5]
            print("  " + ", ".join(chunk))

    if "includes" in params:
        print("\nIncludes:")
        # Split includes into chunks of 3 for better readability
        includes = params["includes"]
        for i in range(0, len(includes), 3):
            chunk = includes[i:i + 3]
            print("  " + ", ".join(chunk))

    if "page" in params:
        print("\nPagination:")
        print(f"  page={params['page'].page}, size={params['page'].size}")

    # Print statistics if available
    if "statistics" in result:
        print("\nSTATISTICS")
        print("-" * 100)
        for key, value in result["statistics"].items():
            formatted_value = format_value(value)
            print(f"  {key:<30} {formatted_value}")

    # Print mock results
    print("\nRESULTS")
    print("-" * 100)

    if not result["mock_data"]:
        print("\n  No results found matching the specified criteria.")
    else:
        for item in result["mock_data"]:
            print("\nRecord:")
            # Print each field on a new line with proper indentation
            for key, value in item.items():
                formatted_value = format_value(value)
                print(f"  {key:<20} {formatted_value}")

    print("\n" + "=" * 100 + "\n")


def main():
    # Test user queries
    print("\nTesting User Queries:")

    active_users_spec = find_active_users()
    print_query_result("Active Users Query", active_users_spec)

    admin_users_spec = find_users_by_role("admin", include_inactive=False)
    print_query_result("Admin Users Query", admin_users_spec)

    user_search_spec = search_users(
        search_text="john",
        roles=["user", "manager"],
        min_age=25,
        max_age=50
    )
    print_query_result("User Search Query", user_search_spec)

    # Test order queries
    print("\nTesting Order Queries:")

    recent_orders_spec = find_recent_orders(days=7)
    print_query_result("Recent Orders Query", recent_orders_spec)

    high_value_orders_spec = find_high_value_orders(
        threshold=Decimal("1000.00"),
        include_items=True
    )
    print_query_result("High Value Orders Query", high_value_orders_spec)

    orders_not_matching_criteria_spec = find_orders_not_matching_criteria(
        min_amount=Decimal("1000.00"),
        excluded_statuses=["cancelled", "pending"],
        days_ago=7
    )
    print_query_result("Orders Not Matching Criteria Query",
                       orders_not_matching_criteria_spec)

    # Test complex order query with filter groups
    complex_orders_spec = find_complex_orders(
        min_amount=Decimal("2000.00"),
        vip_categories=["luxury", "premium", "exclusive"],
        days_ago=30
    )
    print_query_result(
        "Complex Orders Query with Filter Groups", complex_orders_spec)

    # Test product queries
    print("\nTesting Product Queries:")

    available_products_spec = find_available_products(
        category="electronics",
        min_stock=5
    )
    print_query_result("Available Products Query", available_products_spec)

    product_search_spec = search_products(
        search_text="laptop",
        categories=["electronics", "computers"],
        min_price=Decimal("500.00"),
        max_price=Decimal("2000.00"),
        min_rating=4.0,
        tags=["gaming", "portable"]
    )
    print_query_result("Product Search Query", product_search_spec)

    trending_products_spec = find_trending_products(
        min_rating=4.5,
        min_reviews=20
    )
    print_query_result("Trending Products Query", trending_products_spec)


if __name__ == "__main__":
    main()
