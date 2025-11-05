import os
import json
import shutil
import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Dict, Optional, Union

from .base import (
    ObjectStorageBase,
    ObjectMetadata,
    ObjectVisibility,
    ObjectStorageError,
    ObjectNotFoundError,
)

class LocalObjectStorage(ObjectStorageBase):
    def __init__(self, base_path: str, base_url: Optional[str] = None):
        self.base_path = Path(base_path)
        self.files_path = self.base_path / "files"
        self.metadata_path = self.base_path / "metadata"
        self.base_url = base_url.rstrip('/') if base_url else None

    def generate_unique_filename(self, original_filename: str, base_path: Optional[str] = None) -> str:
        """Generate a unique filename based on original filename.
        
        Args:
            original_filename: The original filename
            base_path: Optional base path to prepend
            
        Returns:
            A unique path for the file
        """
        # Get file extension
        _, extension = os.path.splitext(original_filename)
        extension = extension.lower()

        # Generate UUID for uniqueness
        unique_id = str(uuid.uuid4().hex)

        # Get date-based path
        date_path = self._get_date_path()

        # Combine parts
        if base_path:
            # Remove leading/trailing slashes
            base_path = base_path.strip('/')
            return f"{base_path}/{date_path}/{unique_id}{extension}"
        
        return f"{date_path}/{unique_id}{extension}"

    async def initialize(self) -> None:
        """Initialize the storage directories."""
        self.files_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)

    def _get_date_path(self) -> Path:
        """Get the date-based path structure."""
        now = datetime.now()
        return Path(f"{now.year}/{now.month:02d}/{now.day:02d}")

    def _get_file_path(self, object_id: str, version: Optional[int] = None, extension: Optional[str] = None) -> Path:
        """Get the full path for a file."""
        # Normalize path separators
        object_id = object_id.replace('\\', '/')
        
        # Extract date path from object_id (if it contains path information)
        parts = object_id.split('/')
        if len(parts) > 1:
            # If object_id contains path, use it
            date_path = '/'.join(parts[:-1])
            object_id = parts[-1]
        else:
            # If no path in object_id, use current date
            date_path = self._get_date_path()

        filename = f"{object_id}"
        if version is not None:
            filename = f"{filename}.{version}"
        if extension:
            filename = f"{filename}.{extension}"
        return self.files_path / date_path / filename

    def _get_metadata_path(self, object_path: str) -> Path:
        """Get the full path for a metadata file."""
        # Normalize path separators
        object_path = object_path.replace('\\', '/').strip('/')
        
        # Extract path and filename
        path_parts = object_path.split('/')
        if len(path_parts) > 1:
            # If path contains directories, use them
            base_name = path_parts[-1]
            dir_path = '/'.join(path_parts[:-1])
        else:
            # If no directories, use current date
            base_name = object_path
            now = datetime.now()
            dir_path = f"{now.year}/{now.month:02d}/{now.day:02d}"

        # Remove extension from base name if it exists
        if '.' in base_name:
            base_name = base_name.rsplit('.', 1)[0]

        # Ensure directory exists
        metadata_dir = self.metadata_path / dir_path
        metadata_dir.mkdir(parents=True, exist_ok=True)

        return metadata_dir / f"{base_name}.json"

    def _calculate_hash(self, data: Union[bytes, BinaryIO]) -> str:
        """Calculate SHA-256 hash of the data."""
        sha256_hash = hashlib.sha256()
        if isinstance(data, bytes):
            sha256_hash.update(data)
        else:
            for chunk in iter(lambda: data.read(4096), b""):
                sha256_hash.update(chunk)
            data.seek(0)
        return f"sha256:{sha256_hash.hexdigest()}"

    async def _save_metadata(self, object_id: str, metadata: Dict) -> None:
        """Save metadata to a JSON file."""
        metadata_path = self._get_metadata_path(object_id)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    async def _load_metadata(self, object_path: str) -> Dict:
        """Load metadata from a JSON file."""
        metadata_path = self._get_metadata_path(object_path)
        if not metadata_path.exists():
            raise ObjectNotFoundError(f"Metadata not found for object: {object_path}")
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            raise ObjectStorageError(f"Invalid metadata file: {metadata_path}")
        except Exception as e:
            raise ObjectStorageError(f"Error reading metadata file: {metadata_path}, error: {str(e)}")

    async def _find_existing_file_by_hash(self, file_hash: str) -> Optional[Dict]:
        """
        在所有 metadata 文件中查找具有相同哈希值的文件。
        
        Args:
            file_hash: 要查找的文件哈希值
            
        Returns:
            Optional[Dict]: 如果找到匹配的文件，返回其 metadata，否则返回 None
        """
        try:
            # 递归遍历所有 metadata 文件
            for metadata_file in self.metadata_path.rglob("*.json"):
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        # 检查所有版本
                        for version in metadata.get("versions", []):
                            if version["hash"] == file_hash:
                                return metadata
                except Exception:
                    continue  # 忽略单个文件的读取错误
            return None
        except Exception:
            return None

    async def _find_metadata_by_original_filename(self, dir_path: str, original_filename: str) -> Optional[Dict]:
        """
        在指定目录中查找具有相同原始文件名的元数据。
        
        Args:
            dir_path: 目录路径
            original_filename: 原始文件名
            
        Returns:
            Optional[Dict]: 如果找到匹配的文件，返回其元数据，否则返回 None
        """
        try:
            metadata_dir = self.metadata_path / dir_path
            if not metadata_dir.exists():
                return None

            # 遍历目录中的所有 json 文件
            for metadata_file in metadata_dir.glob("*.json"):
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                        if metadata.get("original_filename") == original_filename:
                            return metadata
                except Exception:
                    continue
            return None
        except Exception:
            return None

    async def upload(
        self,
        data: Union[bytes, BinaryIO],
        object_path: str,
        content_type: Optional[str] = None,
        visibility: ObjectVisibility = ObjectVisibility.PRIVATE,
        metadata: Optional[Dict] = None,
    ) -> ObjectMetadata:
        """Upload a file to storage with versioning support."""
        # Calculate hash before anything else
        if isinstance(data, bytes):
            file_hash = self._calculate_hash(data)
            file_size = len(data)
        else:
            data.seek(0)
            file_hash = self._calculate_hash(data)
            data.seek(0, os.SEEK_END)
            file_size = data.tell()
            data.seek(0)

        # Check for existing file with same hash globally
        existing_metadata = await self._find_existing_file_by_hash(file_hash)
        if existing_metadata:
            # 找到相同哈希值的文件，返回其最新版本的元数据，并标记为重复文件
            latest_version = existing_metadata["versions"][-1]
            metadata = ObjectMetadata(
                size=latest_version["size"],
                content_type=existing_metadata.get("content_type", "application/octet-stream"),
                last_modified=datetime.fromisoformat(latest_version["timestamp"]),
                etag=latest_version["hash"],
                version_id=str(latest_version["version"]),
                extra={
                    **existing_metadata,
                    "is_duplicate": True,
                    "duplicate_source": existing_metadata["id"]
                }
            )
            return metadata

        # Normalize object path
        object_path = object_path.replace('\\', '/').strip('/')

        # Extract path and filename
        path_parts = object_path.split('/')
        if len(path_parts) > 1:
            dir_path = '/'.join(path_parts[:-1])
            base_name = path_parts[-1]
        else:
            now = datetime.now()
            dir_path = f"{now.year}/{now.month:02d}/{now.day:02d}"
            base_name = object_path

        # Get original filename from metadata
        original_filename = metadata.get("original_filename") if metadata else base_name

        # Try to find existing metadata for the same original filename
        existing_metadata = await self._find_metadata_by_original_filename(dir_path, original_filename)
        if existing_metadata:
            # 使用已存在的元数据，创建新版本
            current_metadata = existing_metadata
            new_version = current_metadata["current_version"] + 1
            object_id = current_metadata["id"]
        else:
            # 创建新的元数据
            new_version = 1
            object_id = f"{dir_path}/{str(uuid.uuid4())}"
            current_metadata = {
                "id": object_id,
                "original_filename": original_filename,
                "content_type": content_type,
                "upload_time": datetime.now().isoformat(),
                "current_version": new_version,
                "versions": []
            }

        # Create file directory
        file_dir = self.files_path / dir_path
        file_dir.mkdir(parents=True, exist_ok=True)

        # Save the file with version number in filename
        file_name = object_id.split('/')[-1]
        extension = os.path.splitext(original_filename)[1]
        versioned_name = f"{file_name}.v{new_version}{extension}"
        file_path = file_dir / versioned_name

        # Save file content
        if isinstance(data, bytes):
            with open(file_path, "wb") as f:
                f.write(data)
        else:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(data, f)

        # Update metadata with normalized path
        version_info = {
            "version": new_version,
            "timestamp": datetime.now().isoformat(),
            "size": file_size,
            "hash": file_hash,
            "path": str(file_path.relative_to(self.files_path)).replace('\\', '/')
        }
        current_metadata["versions"].append(version_info)
        current_metadata["current_version"] = new_version
        current_metadata["size"] = file_size
        current_metadata["is_duplicate"] = False

        # Merge additional metadata if provided
        if metadata:
            current_metadata.update(metadata)

        # Save metadata
        await self._save_metadata(object_id, current_metadata)

        return ObjectMetadata(
            size=file_size,
            content_type=content_type or "application/octet-stream",
            last_modified=datetime.now(),
            etag=file_hash,
            version_id=str(new_version),
            extra=current_metadata
        )

    async def download(self, object_path: str, version_id: Optional[str] = None) -> bytes:
        """Download a specific version of a file.
        
        Args:
            object_path: The path to the file
            version_id: Optional version ID to get a specific version
            
        Returns:
            bytes: The file content
        """
        # Get metadata to find the correct version
        metadata = await self._load_metadata(object_path)
        version = int(version_id) if version_id else metadata["current_version"]

        # Find the version info
        version_info = next(
            (v for v in metadata["versions"] if v["version"] == version),
            None
        )
        if not version_info:
            raise ObjectNotFoundError(f"Version {version} not found for {object_path}")

        # Get the file path from version info and normalize it
        file_path = version_info["path"].replace('\\', '/').replace('/', os.sep)
        full_path = self.files_path / file_path

        if not full_path.exists():
            raise ObjectNotFoundError(f"File not found: {object_path} (version {version})")

        # Verify the file path is within the files directory
        try:
            full_path.relative_to(self.files_path)
        except ValueError:
            raise ObjectStorageError(f"Invalid file path: {full_path}")

        # Read and return the file content
        with open(full_path, "rb") as f:
            return f.read()

    async def delete(self, object_path: str, version_id: Optional[str] = None) -> None:
        """Delete a file or a specific version of a file.
        
        Args:
            object_path: The path to the file
            version_id: Optional version ID to delete a specific version
            
        Raises:
            ObjectNotFoundError: If the file or version does not exist
        """
        # 首先检查元数据文件是否存在
        metadata_path = self._get_metadata_path(object_path)
        if not metadata_path.exists():
            # 提取文件名
            filename = object_path.split('/')[-1]
            if version_id:
                raise ObjectNotFoundError(f"File '{filename}' (version {version_id}) not found at path: {object_path}")
            else:
                raise ObjectNotFoundError(f"File '{filename}' not found at path: {object_path}")

        try:
            metadata = await self._load_metadata(object_path)
        except ObjectNotFoundError:
            # 提取文件名
            filename = object_path.split('/')[-1]
            if version_id:
                raise ObjectNotFoundError(f"Metadata for file '{filename}' (version {version_id}) not found at path: {object_path}")
            else:
                raise ObjectNotFoundError(f"Metadata for file '{filename}' not found at path: {object_path}")
        
        if version_id:
            # 删除指定版本
            try:
                version = int(version_id)
            except ValueError:
                raise ObjectStorageError(f"Invalid version_id: {version_id}, must be a positive integer")
            
            # 找到指定版本
            version_info = next(
                (v for v in metadata["versions"] if v["version"] == version),
                None
            )
            if not version_info:
                # 提取文件名和可用的版本号列表
                filename = object_path.split('/')[-1]
                available_versions = [str(v["version"]) for v in metadata["versions"]]
                raise ObjectNotFoundError(
                    f"Version {version_id} of file '{filename}' not found at path: {object_path}. "
                    f"Available versions: {', '.join(available_versions)}"
                )
            
            # 删除指定版本的文件
            file_path = self.files_path / version_info["path"].replace('/', os.sep)
            if not file_path.exists():
                filename = object_path.split('/')[-1]
                raise ObjectNotFoundError(f"File content for '{filename}' (version {version_id}) not found at path: {file_path}")
            
            file_path.unlink()
            
            # 从元数据中移除该版本
            metadata["versions"] = [v for v in metadata["versions"] if v["version"] != version]
            
            if not metadata["versions"]:
                # 如果没有版本了，删除元数据文件
                metadata_path = self._get_metadata_path(object_path)
                if metadata_path.exists():
                    metadata_path.unlink()
                # 清理空目录
                self._cleanup_empty_dirs(metadata_path.parent)
                self._cleanup_empty_dirs(file_path.parent)
            else:
                # 更新当前版本号为最新版本
                metadata["current_version"] = max(v["version"] for v in metadata["versions"])
                # 保存更新后的元数据
                await self._save_metadata(metadata["id"], metadata)
        else:
            # 删除所有版本
            # 首先检查所有文件是否存在
            missing_files = []
            for version in metadata["versions"]:
                file_path = self.files_path / version["path"].replace('/', os.sep)
                if not file_path.exists():
                    missing_files.append(f"version {version['version']}: {version['path']}")
            
            if missing_files:
                filename = object_path.split('/')[-1]
                raise ObjectNotFoundError(
                    f"Some versions of file '{filename}' not found:\n" + 
                    "\n".join(f"- {f}" for f in missing_files)
                )
            
            # 删除所有版本的文件
            for version in metadata["versions"]:
                file_path = self.files_path / version["path"].replace('/', os.sep)
                file_path.unlink()

            # 删除元数据文件
            metadata_path = self._get_metadata_path(object_path)
            if metadata_path.exists():
                metadata_path.unlink()

            # 清理空目录
            self._cleanup_empty_dirs(metadata_path.parent)
            for version in metadata["versions"]:
                file_path = self.files_path / version["path"].replace('/', os.sep)
                self._cleanup_empty_dirs(file_path.parent)

    def _cleanup_empty_dirs(self, path: Path) -> None:
        """Recursively remove empty directories."""
        try:
            while path != self.base_path:
                if not any(path.iterdir()):
                    path.rmdir()
                    path = path.parent
                else:
                    break
        except Exception:
            pass  # Ignore any errors during cleanup

    async def get_metadata(self, object_path: str, version_id: Optional[str] = None) -> ObjectMetadata:
        """Get metadata for a file.
        
        Args:
            object_path: The path to the file
            version_id: Optional version ID to get metadata for a specific version
            
        Returns:
            ObjectMetadata: The metadata for the file
        """
        metadata = await self._load_metadata(object_path)
        
        # 如果指定了版本号，查找对应版本
        if version_id:
            try:
                version = int(version_id)
                version_info = next(
                    (v for v in metadata["versions"] if v["version"] == version),
                    None
                )
                if not version_info:
                    raise ObjectNotFoundError(f"Version {version} not found for {object_path}")
            except ValueError:
                raise ObjectStorageError(f"Invalid version_id: {version_id}, must be a positive integer")
        else:
            # 否则使用最新版本
            version_info = metadata["versions"][-1]

        return ObjectMetadata(
            size=version_info["size"],
            content_type=metadata.get("content_type", "application/octet-stream"),
            last_modified=datetime.fromisoformat(version_info["timestamp"]),
            etag=version_info["hash"],
            version_id=str(version_info["version"]),
            extra=metadata
        )

    async def exists(self, object_path: str) -> bool:
        """Check if a file exists."""
        try:
            await self._load_metadata(object_path)
            return True
        except ObjectNotFoundError:
            return False

    def _generate_signature(self, path: str, expiration_timestamp: int) -> str:
        """Generate a signature for the URL.
        
        Args:
            path: The file path
            expiration_timestamp: The expiration timestamp
            
        Returns:
            str: The signature
        """
        # 使用一个密钥（在实际应用中应该从配置中获取）
        secret_key = "your-secret-key"  # TODO: 从配置中获取
        # 标准化路径格式
        normalized_path = path.replace('\\', '/').strip('/')
        if normalized_path.startswith('files/'):
            normalized_path = normalized_path[6:]
        message = f"{normalized_path}{expiration_timestamp}"
        signature = hashlib.sha256(f"{message}{secret_key}".encode()).hexdigest()
        return signature

    async def generate_presigned_url(
        self,
        object_path: str,
        expiration: int = 3600,
        version_id: Optional[str] = None
    ) -> str:
        """Generate a pre-signed URL for the object."""
        # 移除路径中的版本号（如果存在）
        if '.v' in object_path:
            # 例如: text/2024/12/26/file.v1.txt -> text/2024/12/26/file.txt
            parts = object_path.split('/')
            filename = parts[-1]
            filename_parts = filename.split('.')
            if len(filename_parts) >= 3 and filename_parts[-2].startswith('v'):
                # 移除版本号部分
                base_name = '.'.join(filename_parts[:-2])
                extension = filename_parts[-1]
                parts[-1] = f"{base_name}.{extension}"
                object_path = '/'.join(parts)

        # 加载元数据
        metadata = await self._load_metadata(object_path)
        
        # 验证并转换版本号
        try:
            if version_id:
                if not version_id.isdigit():
                    raise ValueError(f"Invalid version_id: {version_id}, must be a positive integer")
                version = int(version_id)
                if version <= 0:
                    raise ValueError(f"Invalid version_id: {version_id}, must be a positive integer")
            else:
                version = metadata["current_version"]
        except ValueError as e:
            raise ObjectStorageError(str(e))

        # 查找版本信息
        version_info = next(
            (v for v in metadata["versions"] if v["version"] == version),
            None
        )
        if not version_info:
            raise ObjectNotFoundError(f"Version {version} not found for {object_path}")

        # 生成过期时间戳
        expiration_timestamp = int(datetime.now().timestamp()) + expiration
        
        # 生成签名
        file_path = version_info['path']  # 这个路径已经包含了 "files/" 前缀
        signature = self._generate_signature(file_path, expiration_timestamp)

        # 使用默认的 base_url，并确保使用正确的主机名
        # 如果没有配置 base_url，使用相对路径
        if self.base_url:
            base_url = self.base_url
        else:
            base_url = "http://127.0.0.1:8888/storage/files"
        
        # 生成 URL，确保不重复添加 "files" 目录
        # 由于 file_path 已经包含了 "files/" 前缀，所以需要移除它
        if file_path.startswith("files/"):
            file_path = file_path[6:]
        return f"{base_url}/{file_path}?expires={expiration_timestamp}&signature={signature}"

    def verify_url_signature(self, path: str, expires: int, signature: str) -> bool:
        """Verify if a signed URL is valid.
        
        Args:
            path: The file path
            expires: The expiration timestamp
            signature: The signature to verify
            
        Returns:
            bool: True if the URL is valid and not expired
        """
        # 检查是否已过期
        current_time = int(datetime.now().timestamp())
        if current_time > expires:
            return False

        # 验证签名
        # 标准化路径格式
        normalized_path = path.replace('\\', '/').strip('/')
        if normalized_path.startswith('files/'):
            normalized_path = normalized_path[6:]
        expected_signature = self._generate_signature(normalized_path, expires)
        return signature == expected_signature 