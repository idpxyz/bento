from typing import Dict, Optional, Any
from pathlib import Path
import os

from .base import ObjectStorageBase
from .factory import ObjectStorageFactory, StorageType


class StorageManager:
    """管理对象存储实例的Manager类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化存储管理器。

        Args:
            config: 从default.yaml中获取的配置字典
        """
        self.config = config.get('object_storage', {})
        self._storages: Dict[str, ObjectStorageBase] = {}
        self._default_storage: Optional[ObjectStorageBase] = None
        self._initialized = False

    async def initialize(self) -> None:
        """初始化所有启用的存储后端。"""
        if self._initialized:
            return

        try:
            # 如果启用了本地存储，则初始化本地存储
            if self.config.get('local', {}).get('enabled', False):
                local_config = self.config['local']
                local_storage = ObjectStorageFactory.create_storage(
                    StorageType.LOCAL,
                    base_path=local_config['base_path'],
                    base_url=local_config.get('base_url')
                )
                await local_storage.initialize()
                self._storages['local'] = local_storage

            # 如果启用了MinIO存储，则初始化MinIO存储
            if self.config.get('minio', {}).get('enabled', False):
                minio_config = self.config['minio']
                minio_storage = ObjectStorageFactory.create_storage(
                    StorageType.MINIO,
                    endpoint=minio_config['endpoint'],
                    access_key=minio_config['access_key'],
                    secret_key=minio_config['secret_key'],
                    bucket_name=minio_config['bucket_name'],
                    secure=minio_config.get('secure', True),
                    region=minio_config.get('region')
                )
                await minio_storage.initialize()
                self._storages['minio'] = minio_storage

            # 设置默认存储
            default_type = self.config.get('default_storage', 'local')
            if default_type in self._storages:
                self._default_storage = self._storages[default_type]
            elif self._storages:
                # 如果未找到默认存储但有存储，则使用第一个存储
                self._default_storage = next(iter(self._storages.values()))
            else:
                raise ValueError("No storage backends are enabled")

            self._initialized = True

        except Exception as e:
            # 在失败时清理任何已初始化的存储
            self._storages.clear()
            self._default_storage = None
            raise RuntimeError(f"Failed to initialize storage manager: {str(e)}")

    def get_storage(self, storage_type: Optional[str] = None) -> ObjectStorageBase:
        """
        通过类型获取存储实例。

        Args:
            storage_type: 要获取的存储类型，或None表示默认存储

        Returns:
            ObjectStorageBase: 请求的存储实例

        Raises:
            ValueError: 如果存储类型未找到或管理器未初始化
        """
        if not self._initialized:
            raise RuntimeError("Storage manager not initialized")

        if storage_type is None:
            if self._default_storage is None:
                raise ValueError("No default storage configured")
            return self._default_storage

        storage = self._storages.get(storage_type)
        if storage is None:
            raise ValueError(f"Storage type '{storage_type}' not found or not enabled")

        return storage

    def validate_file(
        self,
        file_size: int,
        content_type: str,
        file_name: str,
        storage_type: Optional[str] = None
    ) -> None:
        """
        验证文件是否符合存储配置。

        Args:
            file_size: 文件大小（字节）
            content_type: MIME类型
            file_name: 文件名
            storage_type: 可选的存储类型，用于使用特定配置

        Raises:
            ValueError: 如果文件验证失败
        """
        common_config = self.config.get('common', {})
        
        # 检查文件大小
        max_size = common_config.get('max_file_size', float('inf'))
        if file_size > max_size:
            raise ValueError(
                f"文件大小 ({file_size} 字节) 超过允许的最大大小 ({max_size} 字节)"
            )

        # 检查MIME类型
        allowed_types = common_config.get('allowed_mime_types', ['*/*'])
        if '*/*' not in allowed_types:
            content_type_base = content_type.split('/')[0] + '/*'
            if content_type not in allowed_types and content_type_base not in allowed_types:
                raise ValueError(f"文件类型 '{content_type}' 不被允许")

        # 检查文件扩展名
        allowed_extensions = common_config.get('file_extensions', [])
        if allowed_extensions:
            file_ext = os.path.splitext(file_name)[1].lower()
            if file_ext not in allowed_extensions:
                raise ValueError(f"文件扩展名 '{file_ext}' 不被允许")

    def should_compress(self, content_type: str, file_size: int) -> bool:
        """
        检查文件是否应根据配置进行压缩。

        Args:
            content_type: 文件的MIME类型
            file_size: 文件大小，单位为字节

        Returns:
            bool: 如果文件应压缩，则返回True
        """
        compression_config = self.config.get('common', {}).get('compression', {})
        if not compression_config.get('enabled', False):
            return False

        if file_size < compression_config.get('min_size', 1024):
            return False

        mime_types = compression_config.get('mime_types', [])
        content_type_base = content_type.split('/')[0] + '/*'
        return '*/*' in mime_types or content_type in mime_types or content_type_base in mime_types

    def get_cache_control(self) -> Optional[str]:
        """获取配置的cache control头值。"""
        return self.config.get('common', {}).get('cache_control')

    def get_max_versions(self) -> int:
        """获取配置的最大版本数。"""
        versioning_config = self.config.get('common', {}).get('versioning', {})
        return versioning_config.get('max_versions', 1) if versioning_config.get('enabled', False) else 1

    @property
    def initialized(self) -> bool:
        """检查管理器是否已初始化。"""
        return self._initialized 