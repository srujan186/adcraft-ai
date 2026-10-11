"""Object storage behind one interface.

Two backends (settings.storage_backend):
  • "local" (dev default) — files under settings.storage_dir, served by /api/v1/files/{key}.
    No MinIO required (its container images are not anonymously pullable).
  • "s3" — MinIO / S3 via boto3 (presigned URLs), for production.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from app.core.config import settings

BACKEND = settings.storage_backend
BASE = Path(settings.storage_dir).resolve()


# ── s3 client (only constructed when BACKEND == "s3") ──────────────────────────
def _client():
    import boto3
    from botocore.client import Config

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


def _local(key: str) -> Path:
    p = (BASE / key).resolve()
    if not str(p).startswith(str(BASE)):  # path-traversal guard
        raise ValueError("invalid key")
    return p


def ensure_bucket() -> None:
    if BACKEND == "s3":
        from botocore.exceptions import ClientError

        c = _client()
        try:
            c.head_bucket(Bucket=settings.s3_bucket)
        except ClientError:
            c.create_bucket(Bucket=settings.s3_bucket)
    else:
        BASE.mkdir(parents=True, exist_ok=True)


def upload_file(local_path: str, key: str, content_type: str | None = None) -> str:
    if BACKEND == "s3":
        extra = {"ContentType": content_type} if content_type else None
        _client().upload_file(local_path, settings.s3_bucket, key, ExtraArgs=extra)
    else:
        dst = _local(key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_path, dst)
    return key


def download_file(key: str, local_path: str) -> str:
    if BACKEND == "s3":
        _client().download_file(settings.s3_bucket, key, local_path)
    else:
        shutil.copyfile(_local(key), local_path)
    return local_path


def write_bytes(data: bytes, key: str, content_type: str | None = None) -> str:
    if BACKEND == "s3":
        import io

        extra = {"ContentType": content_type} if content_type else None
        _client().upload_fileobj(io.BytesIO(data), settings.s3_bucket, key, ExtraArgs=extra)
    else:
        dst = _local(key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(data)
    return key


def local_path_for(key: str) -> Path:
    return _local(key)


def exists(key: str) -> bool:
    if BACKEND == "s3":
        from botocore.exceptions import ClientError

        try:
            _client().head_object(Bucket=settings.s3_bucket, Key=key)
            return True
        except ClientError:
            return False
    return _local(key).exists()


def presign_get(key: str, expires: int = 3600) -> str:
    if BACKEND == "s3":
        return _client().generate_presigned_url(
            "get_object", Params={"Bucket": settings.s3_bucket, "Key": key}, ExpiresIn=expires
        )
    return f"{settings.public_api_url}/api/v1/files/{key}"


def presign_put(key: str, content_type: str = "application/octet-stream", expires: int = 3600) -> str:
    if BACKEND == "s3":
        return _client().generate_presigned_url(
            "put_object",
            Params={"Bucket": settings.s3_bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expires,
        )
    return f"{settings.public_api_url}/api/v1/files/{key}"
