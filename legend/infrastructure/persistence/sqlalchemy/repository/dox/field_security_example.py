"""字段安全校验使用示例

本文件展示了如何使用 FieldResolver 的字段安全校验功能。
"""

from dataclasses import dataclass
from typing import Dict, Set

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import select

from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.field_resolver import (
    FieldResolver,
    FieldSecurityConfig,
    FieldSecurityError,
    field_security_manager,
)

# 创建 SQLAlchemy Base 类
Base = declarative_base()


class UserPO(Base):
    """用户持久化对象示例"""
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(100))
    email = Column(String(200))
    password_hash = Column(String(255))
    phone = Column(String(20))
    address = Column(String(500))
    salary = Column(Float)
    department = Column(String(100))
    manager_id = Column(Integer, ForeignKey('user.id'))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    # 关系定义
    manager = relationship('UserPO', remote_side=[id])


def example_basic_security():
    """基本安全配置示例"""
    print("=== 基本安全配置示例 ===")

    # 创建安全配置
    security_config = FieldSecurityConfig(
        allowed_fields={"id", "username", "email", "department", "created_at"},
        forbidden_fields={"password_hash", "salary"},
        allowed_relations={"manager"},
        forbidden_relations={"secret_data"}
    )

    # 创建字段解析器
    resolver = FieldResolver(UserPO, security_config)

    # 测试允许的字段
    try:
        field = resolver.resolve("username", operation="read")
        print(f"✓ 允许访问字段: username")
    except FieldSecurityError as e:
        print(f"✗ 字段访问被拒绝: {e}")

    # 测试禁止的字段
    try:
        field = resolver.resolve("password_hash", operation="read")
        print(f"✓ 允许访问字段: password_hash")
    except FieldSecurityError as e:
        print(f"✗ 字段访问被拒绝: {e}")

    # 测试不在白名单中的字段
    try:
        field = resolver.resolve("phone", operation="read")
        print(f"✓ 允许访问字段: phone")
    except FieldSecurityError as e:
        print(f"✗ 字段访问被拒绝: {e}")


def example_permission_based_security():
    """基于权限的安全配置示例"""
    print("\n=== 基于权限的安全配置示例 ===")

    # 创建权限配置
    security_config = FieldSecurityConfig(
        field_permissions={
            "id": "read",
            "username": "read",
            "email": "read",
            "phone": "filter",  # 需要 filter 权限才能用于过滤
            "salary": "admin",   # 需要 admin 权限
            "password_hash": "forbidden"
        },
        relation_permissions={
            "manager": "read",
            "secret_data": "admin"
        }
    )

    resolver = FieldResolver(UserPO, security_config)

    # 测试不同操作权限
    operations = ["read", "filter", "sort", "write", "admin"]

    for operation in operations:
        print(f"\n--- {operation} 操作权限测试 ---")

        # 测试基本字段
        for field in ["id", "username", "phone", "salary"]:
            try:
                resolver.validate_field_access(field, operation)
                print(f"✓ {field}: 允许 {operation}")
            except FieldSecurityError as e:
                print(f"✗ {field}: {operation} 被拒绝 - {e}")


def example_user_role_security():
    """基于用户角色的安全配置示例"""
    print("\n=== 基于用户角色的安全配置示例 ===")

    # 模拟不同角色的用户权限
    user_permissions = {
        "admin": {
            "id": "admin",
            "username": "admin",
            "email": "admin",
            "phone": "admin",
            "salary": "admin",
            "password_hash": "admin",
            "department": "admin",
            "manager_id": "admin",
            "created_at": "admin",
            "updated_at": "admin"
        },
        "manager": {
            "id": "read",
            "username": "read",
            "email": "read",
            "phone": "filter",
            "salary": "forbidden",
            "password_hash": "forbidden",
            "department": "read",
            "manager_id": "read",
            "created_at": "read",
            "updated_at": "read"
        },
        "employee": {
            "id": "read",
            "username": "read",
            "email": "read",
            "phone": "forbidden",
            "salary": "forbidden",
            "password_hash": "forbidden",
            "department": "read",
            "manager_id": "read",
            "created_at": "read",
            "updated_at": "read"
        }
    }

    # 为每个角色创建安全配置
    for role, permissions in user_permissions.items():
        print(f"\n--- {role} 角色权限测试 ---")

        config = field_security_manager.create_user_config(permissions)
        resolver = FieldResolver(UserPO, config)

        # 测试敏感字段访问
        sensitive_fields = ["salary", "password_hash", "phone"]
        for field in sensitive_fields:
            try:
                resolver.validate_field_access(field, "read")
                print(f"✓ {field}: 允许读取")
            except FieldSecurityError as e:
                print(f"✗ {field}: 读取被拒绝")


def example_field_validation():
    """字段列表验证示例"""
    print("\n=== 字段列表验证示例 ===")

    # 创建安全配置
    security_config = FieldSecurityConfig(
        allowed_fields={"id", "username", "email", "department"},
        forbidden_fields={"password_hash", "salary"}
    )

    resolver = FieldResolver(UserPO, security_config)

    # 测试字段列表验证
    test_fields = ["id", "username", "password_hash",
                   "email", "salary", "department"]

    try:
        valid_fields = resolver.validate_fields(test_fields, operation="read")
        print(f"✓ 通过验证的字段: {valid_fields}")
    except FieldSecurityError as e:
        print(f"✗ 字段验证失败: {e}")


def example_query_builder_integration():
    """查询构建器集成示例"""
    print("\n=== 查询构建器集成示例 ===")

    from idp.framework.infrastructure.persistence.specification import (
        Filter,
        FilterOperator,
    )
    from idp.framework.infrastructure.persistence.sqlalchemy.repository.helper.query_builder import (
        QueryBuilder,
    )

    # 创建安全配置
    security_config = FieldSecurityConfig(
        allowed_fields={"id", "username", "email", "department"},
        forbidden_fields={"password_hash", "salary"}
    )

    # 创建字段解析器
    field_resolver = FieldResolver(UserPO, security_config)

    # 创建查询构建器
    query_builder = QueryBuilder(UserPO, field_resolver)

    # 创建过滤条件
    filters = [
        Filter(field="username", operator=FilterOperator.LIKE, value="john%"),
        Filter(field="email", operator=FilterOperator.EQUALS,
               value="john@example.com"),
        # 这个会被安全验证拒绝
        Filter(field="password_hash",
               operator=FilterOperator.EQUALS, value="hash123")
    ]

    # 应用过滤条件（安全验证会自动处理）
    query_builder.apply_filters(filters)

    print("✓ 查询构建器已应用安全验证")


def example_security_manager():
    """安全管理器使用示例"""
    print("\n=== 安全管理器使用示例 ===")

    # 注册预定义的安全配置
    public_config = FieldSecurityConfig(
        allowed_fields={"id", "username", "department"},
        forbidden_fields={"password_hash", "salary", "phone", "email"}
    )

    field_security_manager.register_config("public", public_config)

    # 获取配置
    config = field_security_manager.get_config("public")
    if config:
        resolver = FieldResolver(UserPO, config)

        # 测试配置
        try:
            resolver.validate_field_access("username", "read")
            print("✓ public 配置: username 允许读取")
        except FieldSecurityError as e:
            print(f"✗ public 配置: {e}")

        try:
            resolver.validate_field_access("salary", "read")
            print("✓ public 配置: salary 允许读取")
        except FieldSecurityError as e:
            print(f"✗ public 配置: {e}")


if __name__ == "__main__":
    # 运行所有示例
    example_basic_security()
    example_permission_based_security()
    example_user_role_security()
    example_field_validation()
    example_query_builder_integration()
    example_security_manager()

    print("\n=== 字段安全校验示例完成 ===")
