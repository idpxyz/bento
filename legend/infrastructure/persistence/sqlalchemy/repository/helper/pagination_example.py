"""分页和查询限制功能使用示例

本文件展示了如何使用 QueryBuilder 的分页和查询限制功能。
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import select

from idp.framework.infrastructure.persistence.specification import (
    Filter,
    FilterOperator,
    Page,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.field_resolver import (
    FieldResolver,
)
from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.query_builder import (
    QueryBuilder,
)

# 创建 SQLAlchemy Base 类
Base = declarative_base()


class UserPO(Base):
    """用户持久化对象示例"""
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(100))
    email = Column(String(200))
    created_at = Column(DateTime)


@dataclass
class PageParams:
    """分页参数示例"""
    page: int = 1
    size: int = 20


@dataclass
class OffsetLimitParams:
    """偏移量分页参数示例"""
    offset: int = 0
    limit: int = 50


def example_basic_pagination():
    """基本分页示例"""
    print("=== 基本分页示例 ===")

    # 创建字段解析器
    field_resolver = FieldResolver(UserPO)

    # 创建查询构建器
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 创建分页参数
    page_params = PageParams(page=2, size=10)

    # 应用分页
    query_builder.apply_pagination(page_params)

    # 获取查询限制配置
    limits = query_builder.get_query_limits()
    print(f"查询限制配置: {limits}")

    print("✓ 基本分页应用成功")


def example_smart_pagination():
    """智能分页示例"""
    print("\n=== 智能分页示例 ===")

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 测试不同的分页参数
    test_cases = [
        (1, 20),      # 正常参数
        (0, 10),      # 页码为0（会被修正为1）
        (5, 200),     # 页面大小过大（会被限制）
        (1000, 10),   # 页码过大（会被限制）
    ]

    for page_num, page_size in test_cases:
        print(f"\n测试参数: page_num={page_num}, page_size={page_size}")

        # 验证参数
        valid_page_num, valid_page_size = query_builder.validate_pagination_params(
            page_num, page_size)
        print(f"修正后参数: page_num={valid_page_num}, page_size={valid_page_size}")

        # 应用智能分页
        query_builder.reset().apply_smart_pagination(valid_page_num, valid_page_size)

        # 模拟总记录数
        total_count = 1000
        pagination_info = query_builder.get_pagination_info(
            valid_page_num, valid_page_size, total_count)
        print(f"分页信息: {pagination_info}")


def example_query_limits():
    """查询限制示例"""
    print("\n=== 查询限制示例 ===")

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 设置自定义查询限制
    query_builder.set_query_limits(
        max_limit=500,
        default_limit=25,
        max_offset=5000,
        max_page_size=50,
        default_page_size=10
    )

    print("设置自定义查询限制:")
    limits = query_builder.get_query_limits()
    for key, value in limits.items():
        print(f"  {key}: {value}")

    # 测试查询限制
    test_limits = [None, 10, 100, 1000, -5]

    for limit in test_limits:
        print(f"\n测试查询限制: {limit}")
        query_builder.reset()

        if limit is None:
            query_builder.apply_query_limit()  # 使用默认限制
        else:
            query_builder.apply_query_limit(limit)

        print(f"应用的限制: 使用默认限制" if limit is None else f"应用的限制: {limit}")


def example_offset_pagination():
    """偏移量分页示例"""
    print("\n=== 偏移量分页示例 ===")

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 测试偏移量分页
    test_cases = [
        (0, 20),      # 正常参数
        (-10, 20),    # 负偏移量（会被修正为0）
        (1000, 50),   # 大偏移量（会被限制）
        (0, 200),     # 大限制（会被限制）
    ]

    for offset, limit in test_cases:
        print(f"\n测试参数: offset={offset}, limit={limit}")

        # 应用偏移量
        query_builder.reset().apply_offset(offset).apply_query_limit(limit)

        print(f"应用的偏移量: {offset}")
        print(f"应用的限制: {limit}")


def example_pagination_with_filters():
    """带过滤条件的分页示例"""
    print("\n=== 带过滤条件的分页示例 ===")

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 创建过滤条件
    filters = [
        Filter(field="username", operator=FilterOperator.LIKE, value="john%"),
        Filter(field="email", operator=FilterOperator.CONTAINS,
               value="@example.com"),
    ]

    # 应用过滤条件
    query_builder.apply_filters(filters)

    # 应用分页
    page_params = PageParams(page=1, size=15)
    query_builder.apply_pagination(page_params)

    # 获取JOIN统计信息
    join_stats = query_builder.get_join_statistics()
    print(f"JOIN统计: {join_stats}")

    print("✓ 带过滤条件的分页应用成功")


def example_performance_protection():
    """性能保护示例"""
    print("\n=== 性能保护示例 ===")

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 测试恶意的大偏移量查询
    malicious_cases = [
        (999999, 10),     # 超大偏移量
        (1, 999999),      # 超大页面大小
        (999999, 999999),  # 超大偏移量和页面大小
    ]

    for page_num, page_size in malicious_cases:
        print(f"\n恶意参数: page_num={page_num}, page_size={page_size}")

        # 验证参数
        valid_page_num, valid_page_size = query_builder.validate_pagination_params(
            page_num, page_size)
        print(f"修正后参数: page_num={valid_page_num}, page_size={valid_page_size}")

        # 计算偏移量
        offset = (valid_page_num - 1) * valid_page_size
        print(f"实际偏移量: {offset}")

        # 检查是否在安全范围内
        limits = query_builder.get_query_limits()
        is_safe = offset <= limits['max_offset'] and valid_page_size <= limits['max_page_size']
        print(f"是否安全: {'✓' if is_safe else '✗'}")


def example_cursor_pagination():
    """游标分页示例"""
    print("\n=== 游标分页示例 ===")

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 测试游标分页
    test_cases = [
        (None, 20),           # 无游标，默认限制
        ("user_123", 10),     # 有游标，小限制
        ("user_456", 100),    # 有游标，大限制（会被限制）
    ]

    for cursor, limit in test_cases:
        print(f"\n测试参数: cursor={cursor}, limit={limit}")

        # 应用游标分页
        query_builder.reset().apply_cursor_pagination(cursor, limit)

        print(f"应用的游标: {cursor}")
        print(f"应用的限制: {limit}")


def example_pagination_info():
    """分页信息示例"""
    print("\n=== 分页信息示例 ===")

    # 创建查询构建器
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 模拟不同的分页场景
    scenarios = [
        (1, 20, 100),    # 第一页，有下一页
        (5, 20, 100),    # 中间页
        (5, 20, 100),    # 最后一页
        (1, 20, 0),      # 无数据
        (1, 20, 15),     # 数据不足一页
    ]

    for page_num, page_size, total_count in scenarios:
        print(
            f"\n场景: page_num={page_num}, page_size={page_size}, total_count={total_count}")

        # 获取分页信息
        pagination_info = query_builder.get_pagination_info(
            page_num, page_size, total_count)

        print(f"分页信息:")
        for key, value in pagination_info.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    # 运行所有示例
    example_basic_pagination()
    example_smart_pagination()
    example_query_limits()
    example_offset_pagination()
    example_pagination_with_filters()
    example_performance_protection()
    example_cursor_pagination()
    example_pagination_info()

    print("\n=== 分页和查询限制功能示例完成 ===")
    print("\n主要特性:")
    print("1. 智能分页参数验证和修正")
    print("2. 性能保护，防止恶意的大偏移量查询")
    print("3. 可配置的查询限制")
    print("4. 支持多种分页方式（页码分页、偏移量分页、游标分页）")
    print("5. 完整的分页信息计算")
    print("6. 与过滤条件和JOIN去重的完美集成")
