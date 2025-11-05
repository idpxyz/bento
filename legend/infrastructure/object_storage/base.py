from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, Union
from urllib.parse import urlparse


class ObjectStorageError(Exception):
    """Base exception for all object storage related errors."""
    pass


class ObjectNotFoundError(ObjectStorageError):
    """Raised when an object is not found in storage."""
    pass


class InvalidObjectPathError(ObjectStorageError):
    """Raised when an object path is invalid."""
    pass


class StoragePermissionError(ObjectStorageError):
    """Raised when permission is denied for a storage operation."""
    pass


@dataclass
class ObjectMetadata:
    """Metadata for stored objects."""
    size: int
    content_type: str
    last_modified: datetime
    etag: Optional[str] = None
    version_id: Optional[str] = None
    extra: Dict[str, Any] = None


class ObjectVisibility(Enum):
    """Visibility options for stored objects."""
    PRIVATE = "private"
    PUBLIC_READ = "public-read"
    PUBLIC_READ_WRITE = "public-read-write"


class ObjectStorageBase(ABC):
    """Abstract base class for object storage implementations."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the storage backend with necessary setup."""
        pass

    @abstractmethod
    async def upload(
        self,
        data: Union[bytes, BinaryIO, Path],
        object_path: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        visibility: ObjectVisibility = ObjectVisibility.PRIVATE
    ) -> ObjectMetadata:
        """
        Upload an object to storage.

        Args:
            data: The data to upload (bytes, file-like object, or Path)
            object_path: The path/key where the object will be stored
            content_type: The MIME type of the object
            metadata: Optional custom metadata for the object
            visibility: Visibility/access level for the object

        Returns:
            ObjectMetadata: Metadata of the uploaded object

        Raises:
            StoragePermissionError: If permission is denied
            InvalidObjectPathError: If the object path is invalid
            ObjectStorageError: For other storage-related errors
        """
        pass

    @abstractmethod
    async def download(
        self,
        object_path: str,
        version_id: Optional[str] = None
    ) -> bytes:
        """
        Download an object from storage.

        Args:
            object_path: The path/key of the object to download
            version_id: Optional version ID for versioned objects

        Returns:
            bytes: The object's data

        Raises:
            ObjectNotFoundError: If the object doesn't exist
            StoragePermissionError: If permission is denied
            ObjectStorageError: For other storage-related errors
        """
        pass

    @abstractmethod
    async def delete(
        self,
        object_path: str,
        version_id: Optional[str] = None
    ) -> None:
        """
        Delete an object from storage.

        Args:
            object_path: The path/key of the object to delete
            version_id: Optional version ID for versioned objects

        Raises:
            ObjectNotFoundError: If the object doesn't exist
            StoragePermissionError: If permission is denied
            ObjectStorageError: For other storage-related errors
        """
        pass

    @abstractmethod
    async def get_metadata(
        self,
        object_path: str,
        version_id: Optional[str] = None
    ) -> ObjectMetadata:
        """
        Get metadata for an object.

        Args:
            object_path: The path/key of the object
            version_id: Optional version ID for versioned objects

        Returns:
            ObjectMetadata: The object's metadata

        Raises:
            ObjectNotFoundError: If the object doesn't exist
            StoragePermissionError: If permission is denied
            ObjectStorageError: For other storage-related errors
        """
        pass

    @abstractmethod
    async def generate_presigned_url(
        self,
        object_path: str,
        expiration: int = 3600,
        version_id: Optional[str] = None
    ) -> str:
        """
        Generate a pre-signed URL for temporary access to an object.

        Args:
            object_path: The path/key of the object
            expiration: URL expiration time in seconds (default: 1 hour)
            version_id: Optional version ID for versioned objects

        Returns:
            str: Pre-signed URL for the object

        Raises:
            ObjectNotFoundError: If the object doesn't exist
            StoragePermissionError: If permission is denied
            ObjectStorageError: For other storage-related errors
        """
        pass

    @abstractmethod
    async def exists(
        self,
        object_path: str,
        version_id: Optional[str] = None
    ) -> bool:
        """
        Check if an object exists in storage.

        Args:
            object_path: The path/key of the object
            version_id: Optional version ID for versioned objects

        Returns:
            bool: True if the object exists, False otherwise
        """
        pass

    def validate_object_path(self, object_path: str) -> None:
        """
        Validate an object path/key.

        Args:
            object_path: The path/key to validate

        Raises:
            InvalidObjectPathError: If the path is invalid
        """
        if not object_path or object_path.isspace():
            raise InvalidObjectPathError("Object path cannot be empty")
        
        # Remove leading/trailing whitespace and slashes
        object_path = object_path.strip().strip('/')
        
        try:
            # Check if the path is URL-safe
            parsed = urlparse(f"s3://{object_path}")
            if not all(c.isprintable() for c in object_path):
                raise InvalidObjectPathError("Object path contains non-printable characters")
        except Exception as e:
            raise InvalidObjectPathError(f"Invalid object path format: {str(e)}")
