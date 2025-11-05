"""SQLAlchemy实体元数据管理

提供实体元数据的管理功能，减少对实体类的侵入性。
通过元数据注册表存储实体的配置信息，而不是直接在实体上添加属性。
"""

from typing import Dict, Type, TypeVar, Any, Optional, Set, Generic
from dataclasses import dataclass, field

T = TypeVar('T')

@dataclass
class EntityMetadata(Generic[T]):
    """实体元数据
    
    存储实体的配置信息，包括审计、乐观锁、软删除等设置。
    
    Attributes:
        entity_type: 实体类型
        enable_optimistic_lock: 是否启用乐观锁
        enable_audit: 是否启用审计
        enable_soft_delete: 是否启用软删除
        version_field: 版本字段名称
        audit_fields: 审计字段映射
        soft_delete_fields: 软删除字段映射
        custom_metadata: 自定义元数据
    """
    entity_type: Type[T]
    enable_optimistic_lock: bool = True
    enable_audit: bool = True
    enable_soft_delete: bool = True
    version_field: str = "version"
    audit_fields: Dict[str, str] = field(default_factory=lambda: {
        "created_at": "created_at",
        "created_by": "created_by",
        "updated_at": "updated_at",
        "updated_by": "updated_by"
    })
    soft_delete_fields: Dict[str, str] = field(default_factory=lambda: {
        "deleted_at": "deleted_at",
        "deleted_by": "deleted_by"
    })
    custom_metadata: Dict[str, Any] = field(default_factory=dict)

class EntityMetadataRegistry:
    """实体元数据注册表
    
    管理所有实体类型的元数据。
    提供注册、获取和检查元数据的方法。
    
    Examples:
        >>> # 注册实体元数据
        >>> metadata = EntityMetadata(entity_type=UserPO)
        >>> EntityMetadataRegistry.register_metadata(metadata)
        >>> 
        >>> # 获取实体元数据
        >>> metadata = EntityMetadataRegistry.get_metadata(UserPO)
        >>> 
        >>> # 检查实体是否启用某个功能
        >>> is_enabled = EntityMetadataRegistry.is_feature_enabled(UserPO, "optimistic_lock")
    """
    
    _registry: Dict[Type, EntityMetadata] = {}
    
    @classmethod
    def register_metadata(cls, metadata: EntityMetadata) -> None:
        """注册实体元数据
        
        Args:
            metadata: 实体元数据
        """
        cls._registry[metadata.entity_type] = metadata
    
    @classmethod
    def get_metadata(cls, entity_type: Type[T]) -> Optional[EntityMetadata[T]]:
        """获取实体元数据
        
        Args:
            entity_type: 实体类型
            
        Returns:
            实体元数据，如果不存在则返回None
        """
        return cls._registry.get(entity_type)
    
    @classmethod
    def ensure_metadata(cls, entity_type: Type[T]) -> EntityMetadata[T]:
        """确保实体元数据存在
        
        如果实体元数据不存在，则创建默认元数据。
        
        Args:
            entity_type: 实体类型
            
        Returns:
            实体元数据
        """
        if entity_type not in cls._registry:
            cls._registry[entity_type] = EntityMetadata(entity_type=entity_type)
        return cls._registry[entity_type]
    
    @classmethod
    def is_feature_enabled(cls, entity_type: Type[T], feature: str) -> bool:
        """检查实体是否启用某个功能
        
        Args:
            entity_type: 实体类型
            feature: 功能名称，如"optimistic_lock"、"audit"、"soft_delete"
            
        Returns:
            是否启用该功能
        """
        metadata = cls.get_metadata(entity_type)
        if not metadata:
            return True  # 默认启用
        
        feature_attr = f"enable_{feature}"
        return getattr(metadata, feature_attr, True)
    
    @classmethod
    def get_field_name(cls, entity_type: Type[T], field_category: str, field_name: str) -> Optional[str]:
        """获取字段映射名称
        
        Args:
            entity_type: 实体类型
            field_category: 字段类别，如"audit_fields"、"soft_delete_fields"
            field_name: 字段名称
            
        Returns:
            映射后的字段名称，如果不存在则返回None
        """
        metadata = cls.get_metadata(entity_type)
        if not metadata:
            return field_name  # 默认使用原字段名
        
        fields_dict = getattr(metadata, field_category, {})
        return fields_dict.get(field_name, field_name)
    
    @classmethod
    def clear(cls) -> None:
        """清空注册表"""
        cls._registry.clear()
    
    @classmethod
    def get_registered_types(cls) -> Set[Type]:
        """获取所有已注册的实体类型
        
        Returns:
            已注册的实体类型集合
        """
        return set(cls._registry.keys())

# 装饰器函数，用于简化实体元数据的注册
def entity_metadata(
    enable_optimistic_lock: bool = True,
    enable_audit: bool = True,
    enable_soft_delete: bool = True,
    version_field: str = "version",
    audit_fields: Optional[Dict[str, str]] = None,
    soft_delete_fields: Optional[Dict[str, str]] = None,
    **custom_metadata
):
    """实体元数据装饰器
    
    用于简化实体元数据的注册。
    
    Args:
        enable_optimistic_lock: 是否启用乐观锁
        enable_audit: 是否启用审计
        enable_soft_delete: 是否启用软删除
        version_field: 版本字段名称
        audit_fields: 审计字段映射
        soft_delete_fields: 软删除字段映射
        **custom_metadata: 自定义元数据
        
    Returns:
        装饰器函数
        
    Examples:
        >>> @entity_metadata(enable_soft_delete=False)
        >>> class UserPO(Base):
        >>>     __tablename__ = "users"
        >>>     # ...
    """
    def decorator(cls):
        metadata = EntityMetadata(
            entity_type=cls,
            enable_optimistic_lock=enable_optimistic_lock,
            enable_audit=enable_audit,
            enable_soft_delete=enable_soft_delete,
            version_field=version_field,
            audit_fields=audit_fields or {},
            soft_delete_fields=soft_delete_fields or {},
            custom_metadata=custom_metadata
        )
        EntityMetadataRegistry.register_metadata(metadata)
        return cls
    
    return decorator 