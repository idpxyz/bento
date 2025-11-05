from enum import Enum
from typing import Dict, Optional, Type, Union
from pathlib import Path

from .base import ObjectStorageBase
from .local import LocalObjectStorage
from .minio import MinioObjectStorage


class StorageType(Enum):
    """支持的存储类型。"""
    LOCAL = "local"
    MINIO = "minio"
    # S3 = "s3"  # Future implementation


class ObjectStorageFactory:
    """创建对象存储实例的工厂。"""
    
    _storage_classes: Dict[StorageType, Type[ObjectStorageBase]] = {
        StorageType.LOCAL: LocalObjectStorage,
        StorageType.MINIO: MinioObjectStorage,
        # StorageType.S3: S3ObjectStorage,  # Future implementation
    }

    @classmethod
    def create_storage(
        cls,
        storage_type: Union[StorageType, str],
        **config
    ) -> ObjectStorageBase:
        """
        根据指定的类型和配置创建存储实例。

        Args:
            storage_type: 存储类型
            **config: 存储配置参数

        Returns:
            ObjectStorageBase: 配置的存储实例

        Raises:
            ValueError: If storage_type is invalid or required config is missing
        """
        # 如果传入的是字符串，则转换为枚举类型
        if isinstance(storage_type, str):
            try:
                storage_type = StorageType(storage_type.lower())
            except ValueError:
                raise ValueError(f"Invalid storage type: {storage_type}")

        # 获取存储类
        storage_class = cls._storage_classes.get(storage_type)
        if not storage_class:
            raise ValueError(f"Unsupported storage type: {storage_type}")

        # 验证和准备配置
        if storage_type == StorageType.LOCAL:
            required_params = {'base_path'}
            if not required_params.issubset(config.keys()):
                raise ValueError(f"Missing required parameters for local storage: {required_params - set(config.keys())}")
            
            # 将字符串路径转换为Path对象
            if isinstance(config['base_path'], str):
                config['base_path'] = Path(config['base_path'])

        elif storage_type == StorageType.MINIO:
            required_params = {'endpoint', 'access_key', 'secret_key', 'bucket_name'}
            if not required_params.issubset(config.keys()):
                raise ValueError(f"Missing required parameters for MinIO storage: {required_params - set(config.keys())}")

        # 创建并返回存储实例
        return storage_class(**config)

    @classmethod
    def register_storage_class(
        cls,
        storage_type: StorageType,
        storage_class: Type[ObjectStorageBase]
    ) -> None:
        """
        注册一个新的存储类实现。

        Args:
            storage_type: 存储类型标识符
            storage_class: 存储类实现

        Raises:
            ValueError: 如果存储类型已注册
            TypeError: 如果存储类没有继承自ObjectStorageBase
        """
        if storage_type in cls._storage_classes:
            raise ValueError(f"Storage type {storage_type} is already registered")
        
        if not issubclass(storage_class, ObjectStorageBase):
            raise TypeError("Storage class must inherit from ObjectStorageBase")
        
        cls._storage_classes[storage_type] = storage_class 