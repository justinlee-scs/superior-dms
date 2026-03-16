from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import os
from typing import Protocol


@dataclass(frozen=True)
class StoredObjectRef:
    """Reference to an object in remote storage."""

    bucket: str
    key: str
    etag: str | None = None
    size_bytes: int | None = None


class ObjectStorage(Protocol):
    """Interface for object storage backends."""

    def put_bytes(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> StoredObjectRef:
        ...

    def get_bytes(self, *, bucket: str, key: str) -> bytes:
        ...

    def delete(self, *, bucket: str, key: str) -> None:
        ...

    def exists(self, *, bucket: str, key: str) -> bool:
        ...

    def presign_download_url(
        self,
        *,
        bucket: str,
        key: str,
        expires_in: timedelta = timedelta(minutes=10),
    ) -> str:
        ...


class S3ObjectStorage:
    """S3 backend using boto3."""

    def __init__(
        self,
        *,
        region_name: str | None,
        endpoint_url: str | None,
        access_key_id: str,
        secret_access_key: str,
        session_token: str | None = None,
    ):
        import boto3

        self._client = boto3.client(
            "s3",
            region_name=region_name,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            aws_session_token=session_token,
        )

    def put_bytes(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> StoredObjectRef:
        extra: dict[str, str] = {}
        if content_type:
            extra["ContentType"] = content_type
        response = self._client.put_object(Bucket=bucket, Key=key, Body=data, **extra)
        return StoredObjectRef(
            bucket=bucket,
            key=key,
            etag=(response.get("ETag") or "").replace('"', "") or None,
            size_bytes=len(data),
        )

    def get_bytes(self, *, bucket: str, key: str) -> bytes:
        response = self._client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    def delete(self, *, bucket: str, key: str) -> None:
        self._client.delete_object(Bucket=bucket, Key=key)

    def exists(self, *, bucket: str, key: str) -> bool:
        import botocore.exceptions

        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except botocore.exceptions.ClientError as exc:
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise

    def presign_download_url(
        self,
        *,
        bucket: str,
        key: str,
        expires_in: timedelta = timedelta(minutes=10),
    ) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=int(expires_in.total_seconds()),
        )


class MinioObjectStorage:
    """MinIO backend using minio client library."""

    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool,
    ):
        from minio import Minio

        self._client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    def put_bytes(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str | None = None,
    ) -> StoredObjectRef:
        from io import BytesIO

        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

        stream = BytesIO(data)
        response = self._client.put_object(
            bucket_name=bucket,
            object_name=key,
            data=stream,
            length=len(data),
            content_type=content_type or "application/octet-stream",
        )
        return StoredObjectRef(
            bucket=bucket,
            key=key,
            etag=response.etag,
            size_bytes=len(data),
        )

    def get_bytes(self, *, bucket: str, key: str) -> bytes:
        response = self._client.get_object(bucket_name=bucket, object_name=key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, *, bucket: str, key: str) -> None:
        self._client.remove_object(bucket_name=bucket, object_name=key)

    def exists(self, *, bucket: str, key: str) -> bool:
        from minio.error import S3Error

        try:
            self._client.stat_object(bucket_name=bucket, object_name=key)
            return True
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject", "NotFound"}:
                return False
            raise

    def presign_download_url(
        self,
        *,
        bucket: str,
        key: str,
        expires_in: timedelta = timedelta(minutes=10),
    ) -> str:
        return self._client.presigned_get_object(
            bucket_name=bucket,
            object_name=key,
            expires=expires_in,
        )


def build_object_storage_from_env() -> ObjectStorage:
    """Build an object-storage backend from environment variables."""
    backend = os.getenv("OBJECT_STORAGE_BACKEND", "minio").strip().lower()

    if backend == "s3":
        return S3ObjectStorage(
            region_name=os.getenv("AWS_REGION"),
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
            secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            session_token=os.getenv("AWS_SESSION_TOKEN"),
        )

    if backend == "minio":
        endpoint = os.getenv("MINIO_ENDPOINT", "127.0.0.1:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "")
        secret_key = os.getenv("MINIO_SECRET_KEY", "")
        secure = os.getenv("MINIO_SECURE", "false").strip().lower() in {"1", "true", "yes"}
        return MinioObjectStorage(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    raise ValueError(f"Unsupported OBJECT_STORAGE_BACKEND '{backend}'.")
