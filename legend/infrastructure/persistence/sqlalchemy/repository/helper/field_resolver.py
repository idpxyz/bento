"""Field resolver helper.

This module provides helper classes for resolving field paths to SQLAlchemy columns.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Union

from idp.framework.infrastructure.persistence.sqlalchemy.po.base import BasePO

T = TypeVar('T', bound=BasePO)


@dataclass
class FieldSecurityConfig:
    """字段安全配置

    Attributes:
        allowed_fields: 允许访问的字段列表（白名单）
        forbidden_fields: 禁止访问的字段列表（黑名单）
        allowed_relations: 允许访问的关系列表
        forbidden_relations: 禁止访问的关系列表
        field_permissions: 字段权限映射，格式为 {field_path: permission_level}
        relation_permissions: 关系权限映射，格式为 {relation_path: permission_level}
    """
    allowed_fields: Optional[Set[str]] = None
    forbidden_fields: Optional[Set[str]] = None
    allowed_relations: Optional[Set[str]] = None
    forbidden_relations: Optional[Set[str]] = None
    field_permissions: Optional[Dict[str, str]] = None
    relation_permissions: Optional[Dict[str, str]] = None


class FieldSecurityError(Exception):
    """字段安全错误"""
    pass


class FieldResolver:
    """Helper class for resolving field paths to SQLAlchemy columns with security validation."""

    def __init__(self, entity_type: Type[T], security_config: Optional[FieldSecurityConfig] = None):
        """Initialize field resolver.

        Args:
            entity_type: PO type to resolve fields for
            security_config: 字段安全配置
        """
        self.entity_type = entity_type
        self.security_config = security_config or FieldSecurityConfig()
        self._validate_security_config()

    def _validate_security_config(self) -> None:
        """验证安全配置的有效性"""
        config = self.security_config

        # 检查白名单和黑名单冲突
        if (config.allowed_fields and config.forbidden_fields and
                config.allowed_fields & config.forbidden_fields):
            conflicting_fields = config.allowed_fields & config.forbidden_fields
            raise ValueError(
                f"Fields cannot be both allowed and forbidden: {conflicting_fields}")

        # 检查关系白名单和黑名单冲突
        if (config.allowed_relations and config.forbidden_relations and
                config.allowed_relations & config.forbidden_relations):
            conflicting_relations = config.allowed_relations & config.forbidden_relations
            raise ValueError(
                f"Relations cannot be both allowed and forbidden: {conflicting_relations}")

    def validate_field_access(self, field_path: str, operation: str = "read") -> None:
        """验证字段访问权限

        Args:
            field_path: 字段路径
            operation: 操作类型（read, write, filter, sort等）

        Raises:
            FieldSecurityError: 当字段访问被拒绝时
        """
        if not self.security_config:
            return

        config = self.security_config
        parts = field_path.split('.')

        # 检查字段级别的权限
        if config.field_permissions:
            permission = config.field_permissions.get(field_path)
            if permission and not self._check_permission(permission, operation):
                raise FieldSecurityError(
                    f"Field '{field_path}' requires '{permission}' permission for '{operation}' operation"
                )

        # 检查关系级别的权限
        if len(parts) > 1 and config.relation_permissions:
            relation_path = '.'.join(parts[:-1])
            permission = config.relation_permissions.get(relation_path)
            if permission and not self._check_permission(permission, operation):
                raise FieldSecurityError(
                    f"Relation '{relation_path}' requires '{permission}' permission for '{operation}' operation"
                )

        # 检查白名单
        if config.allowed_fields and field_path not in config.allowed_fields:
            raise FieldSecurityError(
                f"Field '{field_path}' is not in allowed fields list")

        # 检查黑名单
        if config.forbidden_fields and field_path in config.forbidden_fields:
            raise FieldSecurityError(
                f"Field '{field_path}' is in forbidden fields list")

        # 检查关系白名单
        if len(parts) > 1 and config.allowed_relations:
            relation_path = '.'.join(parts[:-1])
            if relation_path not in config.allowed_relations:
                raise FieldSecurityError(
                    f"Relation '{relation_path}' is not in allowed relations list")

        # 检查关系黑名单
        if len(parts) > 1 and config.forbidden_relations:
            relation_path = '.'.join(parts[:-1])
            if relation_path in config.forbidden_relations:
                raise FieldSecurityError(
                    f"Relation '{relation_path}' is in forbidden relations list")

    def _check_permission(self, required_permission: str, operation: str) -> bool:
        """检查权限是否满足操作要求

        Args:
            required_permission: 所需权限级别
            operation: 操作类型

        Returns:
            是否有权限执行操作
        """
        # 权限级别定义（从低到高）
        permission_levels = {
            "read": 1,
            "filter": 2,
            "sort": 3,
            "write": 4,
            "admin": 5
        }

        required_level = permission_levels.get(required_permission, 0)
        operation_level = permission_levels.get(operation, 0)

        return operation_level >= required_level

    def resolve(self, field_path: str, return_key: bool = False, operation: str = "read") -> Union[str, Any]:
        """Resolve a field path to a SQLAlchemy column with security validation.

        Args:
            field_path: Dot-separated field path
            return_key: If True, returns the column key instead of the column object
            operation: 操作类型，用于权限检查

        Returns:
            SQLAlchemy column or column key

        Raises:
            AttributeError: If field path is invalid
            FieldSecurityError: If field access is denied
        """
        # 如果字段路径为空，抛出错误
        if not field_path:
            raise AttributeError("Field path cannot be empty")

        # 验证字段访问权限
        self.validate_field_access(field_path, operation)

        # 分割字段路径
        parts = field_path.split('.')

        # 获取第一个字段
        current = getattr(self.entity_type, parts[0])

        # 处理嵌套字段
        for part in parts[1:]:
            # 获取当前属性的表
            current_table = current.property.mapper.class_.__table__
            # 获取下一个属性
            current = getattr(current_table.columns, part)

        # 返回列对象或列键名
        if hasattr(current, 'property'):
            column = current.property.columns[0]
        elif hasattr(current, 'columns'):
            column = current.columns[0]
        else:
            column = current

        return column.key if return_key else column

    def validate_fields(self, fields: List[str], operation: str = "read") -> List[str]:
        """验证字段列表的访问权限

        Args:
            fields: 字段列表
            operation: 操作类型

        Returns:
            通过验证的字段列表

        Raises:
            FieldSecurityError: 当任何字段访问被拒绝时
        """
        if not fields:
            return []

        valid_fields = []
        invalid_fields = []

        for field in fields:
            try:
                self.validate_field_access(field, operation)
                valid_fields.append(field)
            except FieldSecurityError as e:
                invalid_fields.append(str(e))

        if invalid_fields:
            raise FieldSecurityError(
                f"Field validation failed: {'; '.join(invalid_fields)}")

        return valid_fields

    def get_allowed_fields(self) -> Set[str]:
        """获取所有允许的字段

        Returns:
            允许的字段集合
        """
        if not self.security_config or not self.security_config.allowed_fields:
            # 如果没有白名单限制，返回所有字段
            return self._get_all_entity_fields()

        return self.security_config.allowed_fields

    def get_forbidden_fields(self) -> Set[str]:
        """获取所有禁止的字段

        Returns:
            禁止的字段集合
        """
        if not self.security_config:
            return set()

        return self.security_config.forbidden_fields or set()

    def _get_all_entity_fields(self) -> Set[str]:
        """获取实体的所有字段

        Returns:
            所有字段的集合
        """
        fields = set()

        # 获取直接字段
        for column in self.entity_type.__table__.columns:
            fields.add(column.key)

        # 获取关系字段
        for relationship in self.entity_type.__mapper__.relationships:
            fields.add(relationship.key)

        return fields

    def create_secure_resolver(self, security_config: FieldSecurityConfig) -> 'FieldResolver':
        """创建具有新安全配置的字段解析器

        Args:
            security_config: 新的安全配置

        Returns:
            新的FieldResolver实例
        """
        return FieldResolver(self.entity_type, security_config)


class FieldSecurityManager:
    """字段安全管理器，用于管理不同场景下的字段安全配置"""

    def __init__(self):
        self._configs: Dict[str, FieldSecurityConfig] = {}

    def register_config(self, name: str, config: FieldSecurityConfig) -> None:
        """注册安全配置

        Args:
            name: 配置名称
            config: 安全配置
        """
        self._configs[name] = config

    def get_config(self, name: str) -> Optional[FieldSecurityConfig]:
        """获取安全配置

        Args:
            name: 配置名称

        Returns:
            安全配置或None
        """
        return self._configs.get(name)

    def create_user_config(self, user_permissions: Dict[str, str]) -> FieldSecurityConfig:
        """根据用户权限创建安全配置

        Args:
            user_permissions: 用户权限映射

        Returns:
            安全配置
        """
        allowed_fields = set()
        forbidden_fields = set()
        field_permissions = {}

        for field, permission in user_permissions.items():
            if permission == "forbidden":
                forbidden_fields.add(field)
            else:
                allowed_fields.add(field)
                field_permissions[field] = permission

        return FieldSecurityConfig(
            allowed_fields=allowed_fields if allowed_fields else None,
            forbidden_fields=forbidden_fields if forbidden_fields else None,
            field_permissions=field_permissions if field_permissions else None
        )


# 全局安全管理器实例
field_security_manager = FieldSecurityManager()
