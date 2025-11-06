"""Specification Pattern 使用示例

This example demonstrates how to use the Specification pattern
in the Bento framework for building complex, reusable queries.
"""

from datetime import datetime, timedelta

from bento.persistence.specification import (
    AggregateSpecificationBuilder,
    EntitySpecificationBuilder,
    SortDirection,
    SpecificationBuilder,
)
from bento.persistence.specification.criteria import (
    BetweenCriterion,
    ContainsCriterion,
    EqualsCriterion,
    InCriterion,
    LastNDaysCriterion,
    Or,
    TodayCriterion,
)


def example_1_simple_filter():
    """示例1：简单过滤查询"""
    print("\n=== 示例1：简单过滤查询 ===")

    # 查询状态为"active"的记录
    spec = (
        SpecificationBuilder()
        .where("status", "=", "active")
        .build()
    )

    print(f"过滤条件数量: {len(spec.filters)}")
    first_filter = spec.filters[0]
    print(
        f"第一个过滤条件: field={first_filter.field}, "
        f"operator={first_filter.operator}, value={first_filter.value}"
    )


def example_2_multiple_filters():
    """示例2：多条件查询"""
    print("\n=== 示例2：多条件查询 ===")

    # 查询：status=active AND age >= 18 AND age < 65
    spec = (
        SpecificationBuilder()
        .where("status", "=", "active")
        .where("age", ">=", 18)
        .where("age", "<", 65)
        .build()
    )

    print(f"过滤条件数量: {len(spec.filters)}")
    for i, filter in enumerate(spec.filters):
        print(f"条件{i+1}: {filter.field} {filter.operator.value} {filter.value}")


def example_3_sorting_and_pagination():
    """示例3：排序和分页"""
    print("\n=== 示例3：排序和分页 ===")

    # 按创建时间降序，分页查询
    spec = (
        SpecificationBuilder()
        .where("status", "=", "active")
        .order_by("created_at", SortDirection.DESC)
        .order_by("name", SortDirection.ASC)
        .paginate(page=2, size=20)
        .build()
    )

    print(f"过滤条件数量: {len(spec.filters)}")
    print(f"排序条件数量: {len(spec.sorts)}")
    print(f"排序: {[(s.field, s.direction.value) for s in spec.sorts]}")
    if spec.page:
        print(f"分页: page={spec.page.page}, size={spec.page.size}")


def example_4_complex_query():
    """示例4：复杂查询（Range + 文本搜索）"""
    print("\n=== 示例4：复杂查询 ===")

    # 金额范围 + 名称搜索
    spec = (
        SpecificationBuilder()
        .add_criterion(BetweenCriterion("amount", 100, 1000))
        .add_criterion(ContainsCriterion("name", "Premium"))
        .order_by("amount", SortDirection.DESC)
        .paginate(page=1, size=50)
        .build()
    )

    print(f"过滤条件数量: {len(spec.filters)}")
    for filter in spec.filters:
        print(f"  - {filter.field}: {filter.operator.value} = {filter.value}")


def example_5_date_queries():
    """示例5：日期查询"""
    print("\n=== 示例5：日期查询 ===")

    # 最近7天的记录
    recent_spec = (
        SpecificationBuilder()
        .add_criterion(LastNDaysCriterion("created_at", 7))
        .order_by("created_at", SortDirection.DESC)
        .build()
    )

    print(f"最近7天查询: {len(recent_spec.filters)} 个过滤条件")

    # 今天的记录
    today_spec = (
        SpecificationBuilder()
        .add_criterion(TodayCriterion("created_at"))
        .build()
    )

    print(f"今天查询: {len(today_spec.filters)} 个过滤条件")
    print(f"  - 今天日期: {today_spec.filters[0].value}")


def example_6_logical_operators():
    """示例6：逻辑操作符（AND/OR）"""
    print("\n=== 示例6：逻辑操作符 ===")

    # (status = "active" OR status = "pending")
    status_or = Or(
        EqualsCriterion("status", "active"),
        EqualsCriterion("status", "pending")
    )

    # 获取FilterGroup
    filter_group = status_or.to_filter_group()
    print(f"OR条件组: {len(filter_group.filters)} 个条件")
    print(f"  - 条件1: {filter_group.filters[0].value}")
    print(f"  - 条件2: {filter_group.filters[1].value}")


def example_7_entity_spec():
    """示例7：Entity Specification"""
    print("\n=== 示例7：Entity Specification ===")

    # 查询未删除的、最近创建的记录
    yesterday = datetime.now() - timedelta(days=1)
    spec = (
        EntitySpecificationBuilder()
        # 默认行为：自动排除软删除的记录 (deleted_at IS NULL)
        .created_after(yesterday)
        .order_by("created_at", SortDirection.DESC)
        .build()
    )

    print(f"Entity查询: {len(spec.filters)} 个过滤条件")
    for filter in spec.filters:
        print(f"  - {filter.field}: {filter.operator.value}")


def example_7_5_soft_delete_queries():
    """示例7.5：软删除查询（三种状态）"""
    print("\n=== 示例7.5：软删除查询 ===")

    # 情况1：默认行为 - 自动排除软删除记录
    default_spec = (
        EntitySpecificationBuilder()
        .where("status", "=", "active")
        .build()
    )
    print(f"1. 默认查询（排除软删除）: {len(default_spec.filters)} 个过滤条件")
    print("   - deleted_at IS NULL (自动添加)")
    print("   - status = active")

    # 情况2：包含软删除记录
    include_deleted_spec = (
        EntitySpecificationBuilder()
        .where("status", "=", "active")
        .include_deleted()  # 移除默认的 deleted_at IS NULL 过滤
        .build()
    )
    print(f"\n2. 包含软删除记录: {len(include_deleted_spec.filters)} 个过滤条件")
    print("   - status = active (无 deleted_at 过滤)")

    # 情况3：只查询软删除记录
    only_deleted_spec = (
        EntitySpecificationBuilder()
        .include_deleted()  # 先移除默认过滤
        .only_deleted()     # 再添加 deleted_at IS NOT NULL
        .build()
    )
    print(f"\n3. 只查询软删除记录: {len(only_deleted_spec.filters)} 个过滤条件")
    for filter in only_deleted_spec.filters:
        print(f"   - {filter.field}: {filter.operator.value}")


def example_8_aggregate_spec():
    """示例8：Aggregate Specification"""
    print("\n=== 示例8：Aggregate Specification ===")

    # 查询特定版本的聚合
    spec = (
        AggregateSpecificationBuilder()
        .with_version(5)  # version = 5
        .order_by("created_at", SortDirection.DESC)
        .build()
    )

    print(f"Aggregate查询: {len(spec.filters)} 个过滤条件")
    print(f"  - 版本过滤: version = {spec.filters[0].value}")

    # 查询最低版本的聚合
    min_version_spec = (
        AggregateSpecificationBuilder()
        .with_minimum_version(3)  # version >= 3
        .build()
    )

    print(f"最低版本查询: {len(min_version_spec.filters)} 个过滤条件")
    print(f"  - 最低版本: version >= {min_version_spec.filters[0].value}")


def example_9_reusable_specs():
    """示例9：可重用的Specification类"""
    print("\n=== 示例9：可重用的Specification ===")

    class ActiveRecordsSpec:
        """可重用的"活跃记录"规格"""

        @staticmethod
        def build():
            return (
                EntitySpecificationBuilder()
                .where("status", "=", "active")
                # 默认行为：自动过滤软删除的记录
                .build()
            )

    class RecentRecordsSpec:
        """可重用的"最近记录"规格"""

        @staticmethod
        def build(days: int = 7):
            return (
                SpecificationBuilder()
                .add_criterion(LastNDaysCriterion("created_at", days))
                .order_by("created_at", SortDirection.DESC)
                .build()
            )

    # 使用可重用的规格
    active_spec = ActiveRecordsSpec.build()
    recent_spec = RecentRecordsSpec.build(days=30)

    print(f"ActiveRecordsSpec: {len(active_spec.filters)} 个过滤条件")
    print(f"RecentRecordsSpec: {len(recent_spec.filters)} 个过滤条件")


def example_10_dynamic_query():
    """示例10：动态查询构建"""
    print("\n=== 示例10：动态查询构建 ===")

    def build_search_spec(filters: dict, page: int = 1, size: int = 20):
        """根据动态参数构建查询规格"""
        builder = SpecificationBuilder()

        # 动态添加过滤条件
        for key, value in filters.items():
            if value is not None:
                if isinstance(value, list):
                    builder = builder.add_criterion(InCriterion(key, value))
                elif isinstance(value, tuple) and len(value) == 2:
                    # 范围查询 (min, max)
                    builder = builder.add_criterion(
                        BetweenCriterion(key, value[0], value[1])
                    )
                else:
                    builder = builder.add_criterion(EqualsCriterion(key, value))

        return builder.paginate(page, size).build()

    # 动态查询示例
    search_filters = {
        "status": ["active", "pending"],  # IN查询
        "amount": (100, 1000),  # BETWEEN查询
        "category": "electronics",  # EQUALS查询
    }

    spec = build_search_spec(search_filters, page=1, size=50)

    print(f"动态查询: {len(spec.filters)} 个过滤条件")
    for i, filter in enumerate(spec.filters):
        print(f"  - 条件{i+1}: {filter.field} {filter.operator.value}")


def main():
    """运行所有示例"""
    print("=" * 60)
    print("Bento Framework - Specification Pattern 示例")
    print("=" * 60)

    example_1_simple_filter()
    example_2_multiple_filters()
    example_3_sorting_and_pagination()
    example_4_complex_query()
    example_5_date_queries()
    example_6_logical_operators()
    example_7_entity_spec()
    example_7_5_soft_delete_queries()
    example_8_aggregate_spec()
    example_9_reusable_specs()
    example_10_dynamic_query()

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
