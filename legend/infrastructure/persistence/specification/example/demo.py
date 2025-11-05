"""Specification pattern usage examples.

This module demonstrates various ways to use the specification pattern
for building complex queries.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List
from uuid import UUID

from infrastructure.persistence.specification.core.type import SortDirection

from idp.framework.infrastructure.persistence.specification import (
    FilterOperator,
    Specification,
)
from idp.framework.infrastructure.persistence.specification.builder import (
    SpecificationBuilder,
)
from idp.framework.infrastructure.persistence.specification.criteria import (
    AndCriterion,
    BetweenCriterion,
    ComparisonCriterion,
    EqualsCriterion,
    OrCriterion,
)


def basic_query_example() -> Specification:
    """Basic query example using simple criteria.
    
    Returns:
        Specification for finding active users created in the last 7 days,
        sorted by creation date.
    """
    return (SpecificationBuilder()
        .compare("is_active", True, FilterOperator.EQUALS)
        .compare("created_at", datetime.now() - timedelta(days=7), FilterOperator.GREATER_EQUAL)
        .add_sort("created_at", direction=SortDirection.DESC)
        .build())


def complex_search_example(user_id: UUID, search_text: str) -> Specification:
    """Complex search example using logical operators.
    
    Args:
        user_id: User ID to match
        search_text: Text to search for in name or email
        
    Returns:
        Specification for finding a user by ID and text search in name/email
    """
    return (SpecificationBuilder()
        .and_(
            lambda b: b.by_id(user_id),
            lambda b: b.or_(
                lambda b: b.text_search("name", search_text),
                lambda b: b.text_search("email", search_text)
            )
        )
        .build())


def array_operations_example(tags: List[str]) -> Specification:
    """Array operations example.
    
    Args:
        tags: List of tags to check
        
    Returns:
        Specification for finding items with specific array conditions
    """
    return (SpecificationBuilder()
        .array_contains("categories", ["important", "urgent"])
        .where("tags", "not_in", tags)  # Using direct negation instead of not_()
        .array_empty("comments", is_empty=False)  # Has comments
        .build())


def json_operations_example(status: str, settings: Dict) -> Specification:
    """JSON operations example.
    
    Args:
        status: Status to check in metadata
        settings: Settings to check for
        
    Returns:
        Specification for finding items with specific JSON conditions
    """
    return (SpecificationBuilder()
        .json_contains("metadata", {"status": status})
        .json_exists("config", {"theme": {"dark_mode": True}})
        .json_has_key("settings", "notifications")
        .build())


def text_search_example(search_text: str) -> Specification:
    """Text search example using various text operators.
    
    Args:
        search_text: Text to search for
        
    Returns:
        Specification for finding items matching text patterns
    """
    return (SpecificationBuilder()
        .regex("name", f"^{search_text}.*", case_sensitive=False)
        .or_(
            lambda b: b.compare("status", "active", FilterOperator.EQUALS),
            lambda b: b.and_(
                lambda b: b.compare("status", "pending", FilterOperator.EQUALS),
                lambda b: b.is_null("deleted_at", is_null=True)
            )
        )
        .build())


def pagination_example(page: int, size: int) -> Specification:
    """Pagination example with sorting.
    
    Args:
        page: Page number (0-based)
        size: Page size
        
    Returns:
        Specification with pagination and sorting
    """
    return (SpecificationBuilder()
        .compare("is_active", True, FilterOperator.EQUALS)
        .add_sort("created_at", direction=SortDirection.DESC)
        .add_sort("name", direction=SortDirection.ASC)
        .set_page(offset=page * size, limit=size)
        .build())


def range_query_example(
    min_age: int,
    max_age: int,
    min_score: float,
    max_score: float
) -> Specification:
    """Range query example using between operator.
    
    Args:
        min_age: Minimum age
        max_age: Maximum age
        min_score: Minimum score
        max_score: Maximum score
        
    Returns:
        Specification for finding items within ranges
    """
    return (SpecificationBuilder()
        .between("age", min_age, max_age)
        .between("score", min_score, max_score)
        .build())


def full_example() -> Specification:
    """Comprehensive example combining multiple features.
    
    Returns:
        Complex specification using various operators and conditions
    """
    one_week_ago = datetime.now() - timedelta(days=7)
    
    return (SpecificationBuilder()
        # Basic conditions
        .compare("is_active", True, FilterOperator.EQUALS)
        .compare("status", "published", FilterOperator.EQUALS)
        
        # Date range
        .between("created_at", one_week_ago, datetime.now())
        
        # Complex logical combination
        .and_(
            # Array conditions
            lambda b: b.array_contains("tags", ["featured", "trending"]),
            lambda b: b.array_empty("warnings", is_empty=True),
            
            # Nested OR condition
            lambda b: b.or_(
                # JSON conditions
                lambda b: b.json_contains("metadata", {"verified": True}),
                lambda b: b.and_(
                    lambda b: b.json_has_key("settings", "premium"),
                    lambda b: b.compare("subscription_type", "pro", FilterOperator.EQUALS)
                )
            )
        )
        
        # Text search
        .text_search("title", "important", case_sensitive=True)
        .regex("code", "^[A-Z]{2}-\\d{4}$")
        
        # Null checks
        .is_null("deleted_at", is_null=True)
        .is_null("archived_at", is_null=True)
        
        # Sorting
        .add_sort("priority", direction=SortDirection.DESC)
        .add_sort("created_at", direction=SortDirection.DESC)
        
        # Pagination
        .set_page(offset=0, limit=20)
        .build()
    )


def convenience_methods_example() -> Specification:
    """Example using the new convenience methods.
    
    Returns:
        Specification using various shorthand methods
    """
    return (SpecificationBuilder()
        # 基本比较
        .where("age", ">=", 18)
        .where("status", "in", ["active", "pending"])
        
        # 简写方法
        .filter("type", "user")          # 等同于 where("type", "=", "user")
        .exclude("role", "admin")        # 等同于 where("role", "!=", "admin")
        
        # NULL 检查
        .where("deleted_at", "is_null")
        .where("updated_at", "is_not_null")
        
        # BETWEEN 操作
        .where("score", "between", [60, 100])  # 等同于 between("score", 60, 100)
        
        # 文本搜索
        .where("name", "like", "%john%")
        .where("email", "contains", "@example.com")
        .where("code", "starts_with", "USR-")
        
        # 数组操作
        .where("tags", "array_contains", ["important"])
        .where("comments", "array_not_empty")
        
        # JSON 操作
        .where("metadata", "json_contains", {"verified": True})
        .where("settings", "json_has_key", "theme")
        
        # 排序和分页
        .add_sort("created_at", direction=SortDirection.DESC)
        .set_page(offset=0, limit=10)
        .build()
    )


def json_query_example() -> Specification:
    """Example of building a specification from JSON/dict data.
    
    This demonstrates how to use the specification builder with JSON data
    as typically received from API requests.
    
    Returns:
        Specification built from JSON data
    """
    # 模拟从 API 请求接收的 JSON 数据
    json_data = {
        # 基础过滤条件
        "filters": [
            {"field": "age", "operator": ">=", "value": 18},
            {"field": "status", "operator": "in", "value": ["active", "pending"]},
            {"field": "email", "operator": "contains", "value": "@example.com"},
            {"field": "last_login", "operator": "is_not_null", "value": None},
            {"field": "is_deleted", "operator": "=", "value": False}
        ],
        
        # 过滤组
        "groups": [
            {
                "operator": "or",
                "filters": [
                    {"field": "status", "operator": "=", "value": "active"},
                    {"field": "status", "operator": "=", "value": "pending"}
                ]
            },
            {
                "operator": "and",
                "filters": [
                    {"field": "created_at", "operator": ">=", "value": "2024-01-01T00:00:00Z"},
                    {"field": "updated_at", "operator": "<=", "value": "2024-12-31T23:59:59Z"}
                ]
            }
        ],
        
        # 排序
        "sorts": [
            {"field": "created_at", "direction": "desc"},
            {"field": "name", "direction": "asc"}
        ],
        
        # 分页
        "page": {
            "offset": 0,
            "limit": 20
        },
        
        # 字段选择
        "fields": ["id", "name", "email", "status", "created_at"],
        
        # 关联加载
        "includes": ["profile", "orders.items"]
    }
    
    # 从 JSON 数据构建规范
    return SpecificationBuilder.from_dict(json_data).build()


def field_selection_example() -> Specification:
    """Example using field selection and relation inclusion.
    
    Returns:
        Specification with selected fields and included relations
    """
    return (SpecificationBuilder()
        # 选择特定字段
        .select(
            "id",
            "username",
            "email",
            "created_at"
        )
        # 包含关联数据
        .include(
            "profile",              # 包含用户档案
            "orders.items",         # 包含订单及其项目
            "permissions.role"      # 包含权限及其角色
        )
        # 基础条件
        .where("is_active", "=", True)
        .where("created_at", ">=", datetime.now() - timedelta(days=30))
        # 排序和分页
        .add_sort("created_at", direction=SortDirection.DESC)
        .set_page(offset=0, limit=20)
        .build())


def statistical_example() -> Specification:
    """Example using statistical functions.
    
    Returns:
        Specification with various statistical calculations
    """
    return (SpecificationBuilder()
        # Basic statistics
        .count("id", alias="total_users")
        .sum("score", alias="total_score")
        .avg("rating", alias="average_rating", distinct=True)
        
        # Grouped statistics
        .group_by("department", "role")
        .count("id", alias="employee_count")
        .avg("salary", alias="average_salary")
        .min("join_date", alias="earliest_join")
        .max("join_date", alias="latest_join")
        
        # String concatenation
        .group_concat("name", separator=", ", alias="employee_names", distinct=True)
        
        # Conditions
        .where("is_active", "=", True)
        .where("join_date", ">=", datetime.now() - timedelta(days=365))
        
        # Group filtering
        .having("employee_count", ">", 5)
        
        # Sorting
        .add_sort("department", direction=SortDirection.ASC)
        .add_sort("employee_count", direction=SortDirection.DESC)
        .build())


def filter_groups_example() -> Specification:
    """使用过滤组演示复杂的逻辑组合查询.
    
    这个示例展示了如何使用过滤组构建复杂的逻辑查询条件：
    1. 状态过滤: status IN ('active', 'pending')
    2. 日期范围: created_at >= (now - 30 days) AND updated_at <= now
    3. 权限检查: role = 'admin' OR (has_permission = True AND permission_level >= 5)
    
    最终的逻辑表达式等价于:
    (status = 'active' OR status = 'pending')
    AND (created_at >= now-30d AND updated_at <= now)
    AND (role = 'admin' OR (has_permission = True AND permission_level >= 5))
    AND is_deleted = False
    
    Returns:
        包含复杂逻辑组合的规范对象
    """
    return (SpecificationBuilder()
        # 第一组: 状态过滤 (OR)
        # 查找状态为active或pending的记录
        .or_(
            lambda b: b.where("status", "=", "active"),
            lambda b: b.where("status", "=", "pending")
        )
        
        # 第二组: 日期范围过滤 (AND)
        # 查找最近30天内创建且已更新的记录
        .and_(
            lambda b: b.where("created_at", ">=", datetime.now() - timedelta(days=30)),
            lambda b: b.where("updated_at", "<=", datetime.now())
        )
        
        # 第三组: 权限检查 (复杂组合)
        # 检查是否为管理员或具有足够的权限级别
        .or_(
            lambda b: b.where("role", "=", "admin"),
            lambda b: b.and_(
                lambda b: b.where("has_permission", "=", True),
                lambda b: b.where("permission_level", ">=", 5)
            )
        )
        
        # 全局过滤条件
        .where("is_deleted", "=", False)  # 排除已删除记录
        
        # 排序和分页
        .add_sort("created_at", direction=SortDirection.DESC)  # 按创建时间降序
        .set_page(offset=0, limit=20)  # 分页设置
        .build())


def find_premium_products() -> Specification:
    """Find premium products that are not on sale.
    
    This demonstrates using direct negation operators to exclude products
    that are either on sale or have a discount.
    
    Returns:
        Specification for finding premium products
    """
    return (SpecificationBuilder()
        # Not on sale AND no discount
        .and_(
            lambda b: b.where("is_on_sale", "=", False),
            lambda b: b.where("discount_percentage", "<=", 0)
        )
        .where("price", ">=", Decimal("1000"))
        .filter("is_active", True)
        .select(
            "id", "name", "description",
            "price", "category", "rating"
        )
        .add_sort("price", direction=SortDirection.DESC)
        .build())


def find_available_products_not_in_category(
    excluded_category: str,
    min_stock: int = 1
) -> Specification:
    """Find available products not in a specific category.
    
    Args:
        excluded_category: Category to exclude
        min_stock: Minimum stock level required
        
    Returns:
        Specification for finding products
    """
    return (SpecificationBuilder()
        .filter("is_active", True)
        .where("stock_level", ">=", min_stock)
        .where("category", "!=", excluded_category)  # Using "ne" (not equals) operator
        .select(
            "id", "name", "category",
            "price", "stock_level"
        )
        .add_sort("name", direction=SortDirection.ASC)
        .build())


def find_orders_with_complex_conditions(
    min_amount: Decimal,
    excluded_statuses: List[str]
) -> Specification:
    """Find orders with complex conditions.
    
    Args:
        min_amount: Minimum order amount
        excluded_statuses: List of statuses to exclude
        
    Returns:
        Specification for finding orders
    """
    return (SpecificationBuilder()
        .where("total_amount", ">=", min_amount)
        .where("status", "not_in", excluded_statuses)
        .where("is_deleted", "is_null")
        .select(
            "id", "order_number", "status",
            "total_amount", "created_at"
        )
        .include("customer", "items")
        .add_sort("created_at", direction=SortDirection.DESC)
        .build())


def find_users_not_in_groups(groups: List[str]) -> Specification:
    """Find users not in specific groups.
    
    Args:
        groups: List of groups to exclude
        
    Returns:
        Specification for finding users
    """
    return (SpecificationBuilder()
        .where("group", "not_in", groups)
        .filter("is_active", True)
        .select("id", "name", "email", "group")
        .build())


def find_products_without_reviews() -> Specification:
    """Find products that have no reviews.
    
    Returns:
        Specification for finding products without reviews
    """
    return (SpecificationBuilder()
        .where("reviews", "array_empty")
        .filter("is_active", True)
        .select("id", "name", "category")
        .build())


def find_orders_not_in_date_range(
    start_date: datetime,
    end_date: datetime
) -> Specification:
    """Find orders outside a date range.
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        Specification for finding orders
    """
    return (SpecificationBuilder()
        .or_(
            lambda b: b.where("created_at", "<", start_date),
            lambda b: b.where("created_at", ">", end_date)
        )
        .select("id", "created_at", "status")
        .build())


def find_products_not_matching_criteria(
    price_range: tuple[Decimal, Decimal],
    categories: List[str],
    min_rating: float
) -> Specification:
    """Find products that don't match specific criteria.
    
    Args:
        price_range: (min_price, max_price) tuple
        categories: List of categories
        min_rating: Minimum rating threshold
        
    Returns:
        Specification for finding products
    """
    return (SpecificationBuilder()
        .or_(
            lambda b: b.where("price", "<", price_range[0]),
            lambda b: b.where("price", ">", price_range[1]),
            lambda b: b.where("category", "not_in", categories),
            lambda b: b.where("rating", "<", min_rating)
        )
        .filter("is_active", True)
        .select(
            "id", "name", "category",
            "price", "rating"
        )
        .build())


def main():
    """运行所有示例并打印查询参数"""
    print("\nSpecification Pattern Examples\n" + "="*30 + "\n")
    
    # Test basic queries
    print("\nBasic Queries:")
    print_query_result("Basic Query", basic_query_example())
    
    # Test complex search
    user_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    print_query_result("Complex Search", complex_search_example(user_id, "john"))
    
    # Test array operations
    tags = ["important", "urgent"]
    print_query_result("Array Operations", array_operations_example(tags))
    
    # Test JSON operations
    settings = {"theme": "dark", "notifications": True}
    print_query_result("JSON Operations", json_operations_example("active", settings))
    
    # Test text search
    print_query_result("Text Search", text_search_example("test"))
    
    # Test pagination
    print_query_result("Pagination", pagination_example(0, 10))
    
    # Test range query
    print_query_result("Range Query", range_query_example(18, 65, 0.0, 100.0))
    
    # Test full example
    print_query_result("Full Example", full_example())
    
    # Test convenience methods
    print_query_result("Convenience Methods", convenience_methods_example())
    
    # Test JSON query
    print_query_result("JSON Query", json_query_example())
    
    # Test field selection
    print_query_result("Field Selection", field_selection_example())
    
    # Test statistics
    print_query_result("Statistics", statistical_example())
    
    # Test filter groups
    print_query_result("Filter Groups", filter_groups_example())
    
    # Test NOT operator examples
    print("\nNOT Operator Examples:")
    print_query_result("Premium Products", find_premium_products())
    print_query_result("Products Not in Category", find_available_products_not_in_category("Electronics"))
    print_query_result("Orders with Complex Conditions", 
                      find_orders_with_complex_conditions(Decimal("1000"), ["completed", "cancelled"]))
    print_query_result("Users Not in Groups", find_users_not_in_groups(["Marketing", "Sales"]))
    print_query_result("Products Without Reviews", find_products_without_reviews())
    print_query_result("Orders Not in Date Range", 
                      find_orders_not_in_date_range(datetime(2024, 1, 1), datetime(2024, 12, 31)))
    print_query_result("Products Not Matching Criteria", 
                      find_products_not_matching_criteria((Decimal("500"), Decimal("2000")), 
                                                       ["Electronics", "Computers"], 4.0))

def format_value(value: Any) -> str:
    """Format value for display.
    
    Args:
        value: Value to format
        
    Returns:
        Formatted string representation
    """
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(str(v) for v in value) + "]"
    elif isinstance(value, dict):
        return "{" + ", ".join(f"{k}: {v}" for k, v in value.items()) + "}"
    elif isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(value, UUID):
        return str(value)
    return str(value)

def print_query_result(name: str, spec: Specification) -> None:
    """Print formatted query result.
    
    Args:
        name: Query name
        spec: Specification to print
    """
    print(f"\n{name}:")
    print("-" * len(name))
    
    params = spec.to_query_params()
    
    # Print filters
    if params.get("filters"):
        print("\nFilters:")
        for f in params["filters"]:
            print(f"  {f.field} {f.operator} {format_value(f.value)}")
    
    # Print filter groups
    if params.get("groups"):
        print("\nFilter Groups:")
        for g in params["groups"]:
            print(f"  {g.operator}:")
            for f in g.filters:
                print(f"    {f.field} {f.operator} {format_value(f.value)}")
    
    # Print sorts
    if params.get("sorts"):
        print("\nSort:")
        for s in params["sorts"]:
            direction = "ASC" if s.direction == SortDirection.ASC else "DESC"
            print(f"  {s.field} {direction}")
    
    # Print pagination
    if params.get("page"):
        print("\nPagination:")
        print(f"  Offset: {params['page'].offset}")
        print(f"  Limit: {params['page'].limit}")
    
    # Print selected fields
    if params.get("fields"):
        print("\nSelected Fields:")
        print(f"  {', '.join(params['fields'])}")
    
    # Print includes
    if params.get("includes"):
        print("\nIncludes:")
        print(f"  {', '.join(params['includes'])}")
    
    # Print statistics
    if params.get("statistics"):
        print("\nStatistics:")
        for stat in params["statistics"]:
            distinct = "DISTINCT " if stat.distinct else ""
            print(f"  {stat.function}({distinct}{stat.field}) AS {stat.alias}")
    
    # Print group by
    if params.get("group_by"):
        print("\nGroup By:")
        print(f"  {', '.join(params['group_by'])}")
    
    # Print having
    if params.get("having"):
        print("\nHaving:")
        for h in params["having"]:
            print(f"  {h.field} {h.operator} {format_value(h.value)}")

if __name__ == "__main__":
    main()
