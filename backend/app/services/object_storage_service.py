from __future__ import annotations

import hashlib
import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


@dataclass(frozen=True)
class StoredObject:
    storage_key: str
    storage_backend: str
    byte_size: int
    sha256: str
    media_type: str
    file_name: str
    local_path: Path | None = None


class ObjectStorageService:
    async def store_bytes(
        self,
        *,
        org_id: str,
        incident_id: str,
        file_name: str,
        media_type: str | None,
        payload: bytes,
        object_scope: str = 'incidents',
    ) -> StoredObject:
        raise NotImplementedError

    def resolve_local_path(self, storage_key: str) -> Path | None:
        return None

    async def read_bytes(self, storage_key: str) -> bytes | None:
        path = self.resolve_local_path(storage_key)
        if path is None:
            return None
        return path.read_bytes()


class LocalObjectStorageService(ObjectStorageService):
    def __init__(self, root_dir: str) -> None:
        self.root_dir = Path(root_dir)

    async def store_bytes(
        self,
        *,
        org_id: str,
        incident_id: str,
        file_name: str,
        media_type: str | None,
        payload: bytes,
        object_scope: str = 'incidents',
    ) -> StoredObject:
        safe_name = _safe_file_name(file_name)
        storage_key = f"{object_scope.strip('/')}/{org_id}/{incident_id}/{uuid.uuid4()}-{safe_name}"
        target_path = self.root_dir / storage_key
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(payload)
        resolved_media_type = media_type or mimetypes.guess_type(safe_name)[0] or 'application/octet-stream'
        return StoredObject(
            storage_key=storage_key,
            storage_backend='local',
            byte_size=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            media_type=resolved_media_type,
            file_name=safe_name,
            local_path=target_path,
        )

    def resolve_local_path(self, storage_key: str) -> Path | None:
        path = (self.root_dir / storage_key).resolve()
        try:
            path.relative_to(self.root_dir.resolve())
        except ValueError:
            return None
        return path if path.exists() else None


class S3CompatibleObjectStorageService(ObjectStorageService):
    def __init__(self) -> None:
        self.bucket = settings.object_storage_s3_bucket

    async def store_bytes(
        self,
        *,
        org_id: str,
        incident_id: str,
        file_name: str,
        media_type: str | None,
        payload: bytes,
        object_scope: str = 'incidents',
    ) -> StoredObject:
        try:
            import boto3  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError('boto3 is required for S3 object storage backends.') from exc

        if not self.bucket:
            raise RuntimeError('OBJECT_STORAGE_S3_BUCKET must be configured for S3 object storage.')

        safe_name = _safe_file_name(file_name)
        storage_prefix = settings.object_storage_s3_prefix.strip('/')
        scoped_prefix = object_scope.strip('/')
        storage_key = f"{storage_prefix}/{scoped_prefix}/{org_id}/{incident_id}/{uuid.uuid4()}-{safe_name}".strip('/')
        client = boto3.client(
            's3',
            region_name=settings.object_storage_s3_region,
            endpoint_url=settings.object_storage_s3_endpoint,
            aws_access_key_id=settings.object_storage_s3_access_key,
            aws_secret_access_key=settings.object_storage_s3_secret_key,
        )
        resolved_media_type = media_type or mimetypes.guess_type(safe_name)[0] or 'application/octet-stream'
        client.put_object(
            Bucket=self.bucket,
            Key=storage_key,
            Body=payload,
            ContentType=resolved_media_type,
        )
        return StoredObject(
            storage_key=storage_key,
            storage_backend='s3',
            byte_size=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
            media_type=resolved_media_type,
            file_name=safe_name,
            local_path=None,
        )

    async def read_bytes(self, storage_key: str) -> bytes | None:
        try:
            import boto3  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError('boto3 is required for S3 object storage backends.') from exc

        if not self.bucket:
            return None

        client = boto3.client(
            's3',
            region_name=settings.object_storage_s3_region,
            endpoint_url=settings.object_storage_s3_endpoint,
            aws_access_key_id=settings.object_storage_s3_access_key,
            aws_secret_access_key=settings.object_storage_s3_secret_key,
        )
        response = client.get_object(Bucket=self.bucket, Key=storage_key)
        body = response.get('Body')
        if body is None:
            return None
        return body.read()


def build_object_storage_service() -> ObjectStorageService:
    backend = settings.object_storage_backend
    if backend == 's3':
        return S3CompatibleObjectStorageService()
    return LocalObjectStorageService(settings.object_storage_local_dir)


def _safe_file_name(value: str) -> str:
    return ''.join(ch if ch.isalnum() or ch in {'.', '-', '_'} else '_' for ch in value).strip('._') or 'attachment.bin'
