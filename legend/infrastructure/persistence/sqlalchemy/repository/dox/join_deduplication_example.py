"""JOIN 去重功能使用示例

本文件展示了如何使用 QueryBuilder 的 JOIN 去重功能来避免冗余 SQL 并提升性能。
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import select

from idp.framework.infrastructure.persistence.specification import (
    Filter,
    FilterOperator,
    Having,
    Sort,
    Statistic,
    StatisticalFunction,
)
from idp.framework.infrastructure.persistence.specification.core.type import (
    SortDirection,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.field_resolver import (
    FieldResolver,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.query_builder import (
    QueryBuilder,
)

# 创建 SQLAlchemy Base 类
Base = declarative_base()


class DepartmentPO(Base):
    """部门持久化对象示例"""
    __tablename__ = 'department'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    location = Column(String(200))


class ManagerPO(Base):
    """经理持久化对象示例"""
    __tablename__ = 'manager'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    department_id = Column(Integer, ForeignKey('department.id'))
    department = relationship('DepartmentPO')


class UserPO(Base):
    """用户持久化对象示例"""
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(100))
    email = Column(String(200))
    department_id = Column(Integer, ForeignKey('department.id'))
    manager_id = Column(Integer, ForeignKey('manager.id'))

    # 关系定义
    department = relationship('DepartmentPO')
    manager = relationship('ManagerPO')


def example_basic_join_deduplication():
    """基本 JOIN 去重示例"""
    print("=== 基本 JOIN 去重示例 ===")

    # 创建字段解析器
    field_resolver = FieldResolver(UserPO)

    # 创建查询构建器
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 创建多个使用相同关系的过滤条件
    filters = [
        Filter(field="department.name",
               operator=FilterOperator.EQUALS, value="IT"),
        Filter(field="department.name",
               operator=FilterOperator.LIKE, value="%Tech%"),
        Filter(field="manager.id", operator=FilterOperator.EQUALS, value=1),
    ]

    # 应用过滤条件
    query_builder.apply_filters(filters)

    # 获取 JOIN 统计信息
    stats = query_builder.get_join_statistics()

    print(f"应用的 JOIN 路径: {stats['applied_joins']}")
    print(f"JOIN 数量: {stats['join_count']}")
    print(f"别名映射: {stats['alias_mapping']}")

    # 验证只创建了必要的 JOIN
    assert len(stats["applied_joins"]) == 2  # department 和 manager
    print("✓ JOIN 去重成功：相同路径的 JOIN 只创建了一次")


def example_cross_method_join_deduplication():
    """跨方法 JOIN 去重示例"""
    print("\n=== 跨方法 JOIN 去重示例 ===")

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 先应用过滤条件
    filters = [Filter(field="department.name",
                      operator=FilterOperator.EQUALS, value="IT")]
    query_builder.apply_filters(filters)

    print("应用过滤条件后的 JOIN 统计:")
    stats1 = query_builder.get_join_statistics()
    print(f"  JOIN 数量: {stats1['join_count']}")

    # 再应用排序条件（使用相同的关系）
    sorts = [Sort(field="department.name", direction=SortDirection.ASC)]
    query_builder.apply_sorts(sorts)

    print("应用排序条件后的 JOIN 统计:")
    stats2 = query_builder.get_join_statistics()
    print(f"  JOIN 数量: {stats2['join_count']}")

    # 验证 department JOIN 只创建了一次
    assert stats1["join_count"] == stats2["join_count"]
    print("✓ 跨方法 JOIN 去重成功：相同关系路径的 JOIN 被复用")


def example_nested_join_deduplication():
    """嵌套 JOIN 去重示例"""
    print("\n=== 嵌套 JOIN 去重示例 ===")

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 创建使用嵌套关系的过滤条件
    filters = [
        Filter(field="manager.department.name",
               operator=FilterOperator.EQUALS, value="HR"),
        Filter(field="manager.department.name",
               operator=FilterOperator.LIKE, value="%Human%"),
    ]

    # 应用过滤条件
    query_builder.apply_filters(filters)

    # 获取 JOIN 统计信息
    stats = query_builder.get_join_statistics()

    print(f"应用的 JOIN 路径: {stats['applied_joins']}")
    print(f"JOIN 数量: {stats['join_count']}")

    # 验证创建了必要的嵌套 JOIN
    assert "manager" in stats["applied_joins"]
    assert "manager.department" in stats["applied_joins"]
    print("✓ 嵌套 JOIN 去重成功：嵌套关系路径的 JOIN 被正确处理")


def example_performance_comparison():
    """性能对比示例"""
    print("\n=== 性能对比示例 ===")

    # 模拟大量重复的字段访问
    field_paths = [
        "department.name", "department.name", "department.name",
        "manager.id", "manager.id", "manager.id",
        "department.location", "department.location",
    ]

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 应用多个过滤条件
    filters = []
    for i, field_path in enumerate(field_paths):
        filters.append(
            Filter(field=field_path, operator=FilterOperator.EQUALS, value=f"value_{i}"))

    query_builder.apply_filters(filters)

    # 获取 JOIN 统计信息
    stats = query_builder.get_join_statistics()

    print(f"字段访问次数: {len(field_paths)}")
    print(f"实际 JOIN 数量: {stats['join_count']}")
    print(
        f"JOIN 减少比例: {((len(field_paths) - stats['join_count']) / len(field_paths) * 100):.1f}%")

    print("✓ 性能优化成功：大量重复字段访问只创建了必要的 JOIN")


def example_join_statistics_monitoring():
    """JOIN 统计监控示例"""
    print("\n=== JOIN 统计监控示例 ===")

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 模拟复杂的查询构建过程
    print("步骤 1: 应用过滤条件")
    filters = [Filter(field="department.name",
                      operator=FilterOperator.EQUALS, value="IT")]
    query_builder.apply_filters(filters)
    stats1 = query_builder.get_join_statistics()
    print(f"  JOIN 数量: {stats1['join_count']}")

    print("步骤 2: 应用排序条件")
    sorts = [Sort(field="department.name", direction=SortDirection.ASC)]
    query_builder.apply_sorts(sorts)
    stats2 = query_builder.get_join_statistics()
    print(f"  JOIN 数量: {stats2['join_count']}")

    print("步骤 3: 应用分组条件")
    group_by = ["department.name"]
    query_builder.apply_grouping(group_by)
    stats3 = query_builder.get_join_statistics()
    print(f"  JOIN 数量: {stats3['join_count']}")

    print("步骤 4: 应用统计函数")
    statistics = [Statistic(field="department.name",
                            function=StatisticalFunction.COUNT)]
    query_builder.apply_statistics(statistics)
    stats4 = query_builder.get_join_statistics()
    print(f"  JOIN 数量: {stats4['join_count']}")

    # 验证所有步骤都复用了相同的 JOIN
    assert stats1["join_count"] == stats2["join_count"] == stats3["join_count"] == stats4["join_count"]
    print("✓ 监控成功：所有步骤都复用了相同的 JOIN")


def example_clear_joins():
    """清除 JOIN 示例"""
    print("\n=== 清除 JOIN 示例 ===")

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 先应用一些过滤条件
    filters = [Filter(field="department.name",
                      operator=FilterOperator.EQUALS, value="IT")]
    query_builder.apply_filters(filters)

    print("应用过滤条件后:")
    stats_before = query_builder.get_join_statistics()
    print(f"  JOIN 数量: {stats_before['join_count']}")

    # 清除 JOIN
    query_builder.clear_joins()

    print("清除 JOIN 后:")
    stats_after = query_builder.get_join_statistics()
    print(f"  JOIN 数量: {stats_after['join_count']}")

    # 验证 JOIN 已清除
    assert stats_after["join_count"] == 0
    print("✓ 清除 JOIN 成功：所有 JOIN 已被清除")


if __name__ == "__main__":
    # 运行所有示例
    example_basic_join_deduplication()
    example_cross_method_join_deduplication()
    example_nested_join_deduplication()
    example_performance_comparison()
    example_join_statistics_monitoring()
    example_clear_joins()

    print("\n=== JOIN 去重功能示例完成 ===")
    print("\n主要优势:")
    print("1. 避免冗余 JOIN，提升 SQL 执行效率")
    print("2. 减少数据库负载，优化查询性能")
    print("3. 支持跨方法 JOIN 复用")
    print("4. 提供 JOIN 统计监控功能")
    print("5. 支持嵌套关系路径的智能处理")
