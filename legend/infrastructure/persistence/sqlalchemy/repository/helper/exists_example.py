"""EXISTS 和 NOT EXISTS 功能使用示例

本文件展示了如何使用 QueryBuilder 的 EXISTS 和 NOT EXISTS 功能。
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import select

from idp.framework.infrastructure.persistence.specification import (
    ExistsSpec,
    Filter,
    FilterGroup,
    FilterOperator,
    LogicalOperator,
    NotExistsSpec,
    Sort,
)
from idp.framework.infrastructure.persistence.specification.core.type import SortDirection
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
    status = Column(String(20))  # active, inactive
    created_at = Column(DateTime)


class OrderPO(Base):
    """订单持久化对象示例"""
    __tablename__ = 'order'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    order_number = Column(String(50))
    status = Column(String(20))  # pending, completed, cancelled
    amount = Column(Integer)
    created_at = Column(DateTime)

    # 关系
    user = relationship("UserPO", back_populates="orders")


class CommentPO(Base):
    """评论持久化对象示例"""
    __tablename__ = 'comment'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    content = Column(Text)
    rating = Column(Integer)  # 1-5
    created_at = Column(DateTime)

    # 关系
    user = relationship("UserPO", back_populates="comments")


# 添加反向关系
UserPO.orders = relationship("OrderPO", back_populates="user")
UserPO.comments = relationship("CommentPO", back_populates="user")


def create_query_builder_with_entity_mapping():
    """创建带有实体类型映射的查询构建器"""
    field_resolver = FieldResolver(UserPO)
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 重写实体类型映射方法以支持示例
    def get_entity_type_by_name(entity_name: str):
        entity_mapping = {
            'User': UserPO,
            'Order': OrderPO,
            'Comment': CommentPO,
        }
        return entity_mapping.get(entity_name)

    query_builder._get_entity_type_by_name = get_entity_type_by_name
    return query_builder


def example_basic_exists():
    """基本 EXISTS 示例"""
    print("=== 基本 EXISTS 示例 ===")

    # 创建查询构建器
    query_builder = create_query_builder_with_entity_mapping()

    # 创建 EXISTS 规范：查找有订单的用户
    exists_spec = ExistsSpec(
        entity_type="Order",
        filters=[
            Filter(field="user_id", operator=FilterOperator.EQUALS, value="id"),
            Filter(field="status", operator=FilterOperator.EQUALS,
                   value="completed")
        ],
        correlation_field="user_id",
        correlation_main_field="id"
    )

    # 应用 EXISTS 条件
    query_builder.apply_exists(exists_spec)

    # 构建查询
    query = query_builder.build()
    print(f"EXISTS 查询: {query}")

    print("✓ 基本 EXISTS 应用成功")


def example_not_exists():
    """NOT EXISTS 示例"""
    print("\n=== NOT EXISTS 示例 ===")

    # 创建查询构建器
    query_builder = create_query_builder_with_entity_mapping()

    # 创建 NOT EXISTS 规范：查找没有评论的用户
    not_exists_spec = NotExistsSpec(
        entity_type="Comment",
        filters=[
            Filter(field="user_id", operator=FilterOperator.EQUALS, value="id")
        ],
        correlation_field="user_id",
        correlation_main_field="id"
    )

    # 应用 NOT EXISTS 条件
    query_builder.apply_not_exists(not_exists_spec)

    # 构建查询
    query = query_builder.build()
    print(f"NOT EXISTS 查询: {query}")

    print("✓ NOT EXISTS 应用成功")


def example_exists_with_filters():
    """带过滤条件的 EXISTS 示例"""
    print("\n=== 带过滤条件的 EXISTS 示例 ===")

    # 创建查询构建器
    query_builder = create_query_builder_with_entity_mapping()

    # 主查询过滤条件
    main_filters = [
        Filter(field="status", operator=FilterOperator.EQUALS, value="active")
    ]
    query_builder.apply_filters(main_filters)

    # EXISTS 规范：查找有高额订单的用户
    exists_spec = ExistsSpec(
        entity_type="Order",
        filters=[
            Filter(field="user_id", operator=FilterOperator.EQUALS, value="id"),
            Filter(field="amount", operator=FilterOperator.GREATER_THAN, value=1000),
            Filter(field="status", operator=FilterOperator.EQUALS,
                   value="completed")
        ],
        correlation_field="user_id",
        correlation_main_field="id"
    )

    # 应用 EXISTS 条件
    query_builder.apply_exists(exists_spec)

    # 构建查询
    query = query_builder.build()
    print(f"带过滤条件的 EXISTS 查询: {query}")

    print("✓ 带过滤条件的 EXISTS 应用成功")


def example_exists_with_filter_groups():
    """带过滤组的 EXISTS 示例"""
    print("\n=== 带过滤组的 EXISTS 示例 ===")

    # 创建查询构建器
    query_builder = create_query_builder_with_entity_mapping()

    # EXISTS 规范：查找有订单或评论的用户
    exists_spec = ExistsSpec(
        entity_type="Order",
        filter_groups=[
            FilterGroup(
                filters=[
                    Filter(field="user_id",
                           operator=FilterOperator.EQUALS, value="id"),
                    Filter(field="status",
                           operator=FilterOperator.EQUALS, value="completed")
                ],
                operator=LogicalOperator.AND
            )
        ],
        correlation_field="user_id",
        correlation_main_field="id"
    )

    # 应用 EXISTS 条件
    query_builder.apply_exists(exists_spec)

    # 构建查询
    query = query_builder.build()
    print(f"带过滤组的 EXISTS 查询: {query}")

    print("✓ 带过滤组的 EXISTS 应用成功")


def example_complex_exists():
    """复杂 EXISTS 示例"""
    print("\n=== 复杂 EXISTS 示例 ===")

    # 创建查询构建器
    query_builder = create_query_builder_with_entity_mapping()

    # 主查询：活跃用户
    main_filters = [
        Filter(field="status", operator=FilterOperator.EQUALS, value="active")
    ]
    query_builder.apply_filters(main_filters)

    # EXISTS 规范：查找有高评分评论的用户
    exists_spec = ExistsSpec(
        entity_type="Comment",
        filters=[
            Filter(field="user_id", operator=FilterOperator.EQUALS, value="id"),
            Filter(field="rating", operator=FilterOperator.GREATER_EQUAL, value=4)
        ],
        correlation_field="user_id",
        correlation_main_field="id"
    )

    # 应用 EXISTS 条件
    query_builder.apply_exists(exists_spec)

    # 添加排序
    query_builder.apply_sorts([
        Sort(field="created_at", direction=SortDirection.DESC)
    ])

    # 构建查询
    query = query_builder.build()
    print(f"复杂 EXISTS 查询: {query}")

    print("✓ 复杂 EXISTS 应用成功")


def example_multiple_exists():
    """多个 EXISTS 条件示例"""
    print("\n=== 多个 EXISTS 条件示例 ===")

    # 创建查询构建器
    query_builder = create_query_builder_with_entity_mapping()

    # 第一个 EXISTS：有订单的用户
    exists_spec1 = ExistsSpec(
        entity_type="Order",
        filters=[
            Filter(field="user_id", operator=FilterOperator.EQUALS, value="id"),
            Filter(field="status", operator=FilterOperator.EQUALS,
                   value="completed")
        ],
        correlation_field="user_id",
        correlation_main_field="id"
    )

    # 第二个 EXISTS：有评论的用户
    exists_spec2 = ExistsSpec(
        entity_type="Comment",
        filters=[
            Filter(field="user_id", operator=FilterOperator.EQUALS, value="id"),
            Filter(field="rating", operator=FilterOperator.GREATER_EQUAL, value=3)
        ],
        correlation_field="user_id",
        correlation_main_field="id"
    )

    # 应用多个 EXISTS 条件
    query_builder.apply_exists(exists_spec1)
    query_builder.apply_exists(exists_spec2)

    # 构建查询
    query = query_builder.build()
    print(f"多个 EXISTS 查询: {query}")

    print("✓ 多个 EXISTS 条件应用成功")


def example_exists_with_pagination():
    """EXISTS 与分页结合示例"""
    print("\n=== EXISTS 与分页结合示例 ===")

    # 创建查询构建器
    query_builder = create_query_builder_with_entity_mapping()

    # EXISTS 规范：有高额订单的用户
    exists_spec = ExistsSpec(
        entity_type="Order",
        filters=[
            Filter(field="user_id", operator=FilterOperator.EQUALS, value="id"),
            Filter(field="amount", operator=FilterOperator.GREATER_THAN, value=500)
        ],
        correlation_field="user_id",
        correlation_main_field="id"
    )

    # 应用 EXISTS 条件
    query_builder.apply_exists(exists_spec)

    # 应用分页
    from dataclasses import dataclass

    @dataclass
    class PageParams:
        page: int = 1
        size: int = 10

    page_params = PageParams(page=1, size=5)
    query_builder.apply_pagination(page_params)

    # 构建查询
    query = query_builder.build()
    print(f"EXISTS 与分页查询: {query}")

    print("✓ EXISTS 与分页结合成功")


def example_error_handling():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")

    # 创建查询构建器
    query_builder = create_query_builder_with_entity_mapping()

    # 测试无效的 EXISTS 规范
    try:
        # 缺少必要字段的 EXISTS 规范
        invalid_exists_spec = ExistsSpec(
            entity_type="",  # 空的实体类型
            filters=[]  # 空的过滤条件
        )
        query_builder.apply_exists(invalid_exists_spec)
    except Exception as e:
        print(f"预期的错误: {e}")

    # 测试未知实体类型
    try:
        unknown_entity_spec = ExistsSpec(
            entity_type="UnknownEntity",
            filters=[
                Filter(field="id", operator=FilterOperator.EQUALS, value=1)
            ]
        )
        query_builder.apply_exists(unknown_entity_spec)
    except Exception as e:
        print(f"预期的错误: {e}")

    print("✓ 错误处理测试完成")


if __name__ == "__main__":
    # 运行所有示例
    example_basic_exists()
    example_not_exists()
    example_exists_with_filters()
    example_exists_with_filter_groups()
    example_complex_exists()
    example_multiple_exists()
    example_exists_with_pagination()
    example_error_handling()

    print("\n=== EXISTS 和 NOT EXISTS 功能示例完成 ===")
    print("\n主要特性:")
    print("1. 支持 EXISTS 和 NOT EXISTS 子查询")
    print("2. 支持复杂的过滤条件和过滤组")
    print("3. 支持关联字段配置")
    print("4. 与现有功能完美集成（过滤、排序、分页等）")
    print("5. 完善的错误处理和日志记录")
    print("6. 字段安全验证支持")
