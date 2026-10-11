"""Serve / accept local-backend storage objects (dev). Keys are uuid-based and
unguessable, mirroring presigned-URL access. In prod (s3 backend) these are unused —
the browser talks to MinIO/S3 directly via presigned URLs.
"""
from __future__ import annotations

import mimetypes

from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse

from app.core import storage
from app.core.config import settings
from app.core.errors import AppError

router = APIRouter(prefix="/files", tags=["files"])


def _guard_local():
    if settings.storage_backend != "local":
        raise AppError("NOT_FOUND", "Not found", 404)


@router.get("/{key:path}")
async def get_file(key: str):
    _guard_local()
    if not storage.exists(key):
        raise AppError("NOT_FOUND", "File not found", 404)
    path = storage.local_path_for(key)
    media, _ = mimetypes.guess_type(str(path))
    return FileResponse(str(path), media_type=media or "application/octet-stream")


@router.put("/{key:path}")
async def put_file(key: str, request: Request) -> Response:
    _guard_local()
    body = await request.body()
    storage.write_bytes(body, key, request.headers.get("content-type"))
    return Response(status_code=200)
