from __future__ import annotations

try:
    from minio import Minio
except Exception:  # pragma: no cover
    Minio = None  # type: ignore


class MinioStorage:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        assert Minio is not None, "minio library not installed"
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)

    def put_bytes(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ):
        from io import BytesIO

        self.client.put_object(
            bucket, object_name, BytesIO(data), length=len(data), content_type=content_type
        )
