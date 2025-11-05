from datetime import datetime, timedelta
from typing import Dict, Optional, Union, BinaryIO
from pathlib import Path
import io
from minio import Minio
from minio.error import S3Error
from urllib3.exceptions import HTTPError

from .base import (
    ObjectStorageBase,
    ObjectMetadata,
    ObjectVisibility,
    ObjectNotFoundError,
    StoragePermissionError,
    ObjectStorageError,
)


class MinioObjectStorage(ObjectStorageBase):
    """MinIO implementation of object storage."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        secure: bool = True,
        region: Optional[str] = None
    ):
        """
        Initialize MinIO storage.

        Args:
            endpoint: MinIO server endpoint
            access_key: Access key for authentication
            secret_key: Secret key for authentication
            bucket_name: Name of the bucket to use
            secure: Whether to use HTTPS (default: True)
            region: Optional region name
        """
        self.endpoint = endpoint
        self.bucket_name = bucket_name
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
            region=region
        )

    async def initialize(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise ObjectStorageError(f"Failed to initialize MinIO storage: {str(e)}")
        except Exception as e:
            raise ObjectStorageError(f"Unexpected error initializing MinIO storage: {str(e)}")

    async def upload(
        self,
        data: Union[bytes, BinaryIO, Path],
        object_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        visibility: ObjectVisibility = ObjectVisibility.PRIVATE,
    ) -> ObjectMetadata:
        self.validate_object_path(object_path)
        
        try:
            # Convert data to file-like object if needed
            if isinstance(data, bytes):
                data = io.BytesIO(data)
            elif isinstance(data, Path):
                data = data.open('rb')
            
            # Determine content type if not provided
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Prepare metadata
            meta = metadata or {}
            if visibility != ObjectVisibility.PRIVATE:
                meta['x-amz-acl'] = visibility.value
            
            # Get file size for proper upload
            if hasattr(data, 'seek') and hasattr(data, 'tell'):
                data.seek(0, 2)  # Seek to end
                size = data.tell()
                data.seek(0)  # Reset to beginning
            else:
                size = -1  # Unknown size
            
            # Upload the object
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_path.lstrip('/'),
                data=data,
                length=size,
                content_type=content_type,
                metadata=meta
            )
            
            return await self.get_metadata(object_path)
            
        except S3Error as e:
            if 'AccessDenied' in str(e):
                raise StoragePermissionError(f"Permission denied while uploading {object_path}")
            raise ObjectStorageError(f"Failed to upload {object_path}: {str(e)}")
        except Exception as e:
            raise ObjectStorageError(f"Unexpected error uploading {object_path}: {str(e)}")
        finally:
            # Close file if it was opened from Path
            if isinstance(data, (io.IOBase, Path)) and hasattr(data, 'close'):
                data.close()

    async def download(
        self,
        object_path: str,
        version_id: Optional[str] = None
    ) -> bytes:
        self.validate_object_path(object_path)
        
        try:
            # Get the object
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_path.lstrip('/'),
                version_id=version_id
            )
            
            # Read all data
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
                
        except S3Error as e:
            if 'NoSuchKey' in str(e):
                raise ObjectNotFoundError(f"Object {object_path} not found")
            if 'AccessDenied' in str(e):
                raise StoragePermissionError(f"Permission denied while downloading {object_path}")
            raise ObjectStorageError(f"Failed to download {object_path}: {str(e)}")
        except Exception as e:
            raise ObjectStorageError(f"Unexpected error downloading {object_path}: {str(e)}")

    async def delete(
        self,
        object_path: str,
        version_id: Optional[str] = None
    ) -> None:
        self.validate_object_path(object_path)
        
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_path.lstrip('/'),
                version_id=version_id
            )
        except S3Error as e:
            if 'NoSuchKey' in str(e):
                raise ObjectNotFoundError(f"Object {object_path} not found")
            if 'AccessDenied' in str(e):
                raise StoragePermissionError(f"Permission denied while deleting {object_path}")
            raise ObjectStorageError(f"Failed to delete {object_path}: {str(e)}")
        except Exception as e:
            raise ObjectStorageError(f"Unexpected error deleting {object_path}: {str(e)}")

    async def get_metadata(
        self,
        object_path: str,
        version_id: Optional[str] = None
    ) -> ObjectMetadata:
        self.validate_object_path(object_path)
        
        try:
            stat = self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_path.lstrip('/'),
                version_id=version_id
            )
            
            return ObjectMetadata(
                size=stat.size,
                content_type=stat.content_type,
                last_modified=stat.last_modified,
                etag=stat.etag,
                version_id=version_id or stat.version_id,
                extra=stat.metadata
            )
            
        except S3Error as e:
            if 'NoSuchKey' in str(e):
                raise ObjectNotFoundError(f"Object {object_path} not found")
            if 'AccessDenied' in str(e):
                raise StoragePermissionError(f"Permission denied while getting metadata for {object_path}")
            raise ObjectStorageError(f"Failed to get metadata for {object_path}: {str(e)}")
        except Exception as e:
            raise ObjectStorageError(f"Unexpected error getting metadata for {object_path}: {str(e)}")

    async def generate_presigned_url(
        self,
        object_path: str,
        expiration: int = 3600,
        version_id: Optional[str] = None
    ) -> str:
        self.validate_object_path(object_path)
        
        try:
            return self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_path.lstrip('/'),
                expires=timedelta(seconds=expiration),
                version_id=version_id
            )
        except S3Error as e:
            if 'NoSuchKey' in str(e):
                raise ObjectNotFoundError(f"Object {object_path} not found")
            if 'AccessDenied' in str(e):
                raise StoragePermissionError(f"Permission denied while generating URL for {object_path}")
            raise ObjectStorageError(f"Failed to generate URL for {object_path}: {str(e)}")
        except Exception as e:
            raise ObjectStorageError(f"Unexpected error generating URL for {object_path}: {str(e)}")

    async def exists(
        self,
        object_path: str,
        version_id: Optional[str] = None
    ) -> bool:
        self.validate_object_path(object_path)
        
        try:
            self.client.stat_object(
                bucket_name=self.bucket_name,
                object_name=object_path.lstrip('/'),
                version_id=version_id
            )
            return True
        except S3Error as e:
            if 'NoSuchKey' in str(e):
                return False
            raise ObjectStorageError(f"Error checking existence of {object_path}: {str(e)}")
        except Exception as e:
            raise ObjectStorageError(f"Unexpected error checking existence of {object_path}: {str(e)}") 