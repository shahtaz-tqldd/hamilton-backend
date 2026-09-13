import hashlib
from pathlib import PurePath
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select

from app.core.config import settings
from app.db.models import StoredFile
from app.dependencies import CurrentUser, DbSession, owned_folder
from app.modules.files.schemas import FileDownloadResponse, FileMoveRequest, FileResponse
from app.schemas.common import Message
from app.services.storage import storage_service

router = APIRouter(prefix="/files", tags=["Files"])
CHUNK_SIZE = 1024 * 1024


async def owned_file(db: DbSession, user: CurrentUser, item_id: UUID) -> StoredFile:
    item = await db.get(StoredFile, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="File not found")
    return item


async def inspect_upload(upload: UploadFile) -> tuple[int, str]:
    size = 0
    digest = hashlib.sha256()
    while chunk := await upload.read(CHUNK_SIZE):
        size += len(chunk)
        if size > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {settings.max_upload_size_mb} MB upload limit",
            )
        digest.update(chunk)
    await upload.seek(0)
    return size, digest.hexdigest()


@router.post("/upload", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    db: DbSession,
    user: CurrentUser,
    upload: Annotated[UploadFile, File()],
    folder_id: Annotated[UUID | None, Form()] = None,
) -> StoredFile:
    folder = await owned_folder(db, user, folder_id)
    raw_name = upload.filename or "upload"
    safe_name = PurePath(raw_name.replace("\\", "/")).name
    if safe_name in {"", ".", ".."} or len(safe_name) > 255:
        raise HTTPException(status_code=400, detail="Invalid filename")
    size, checksum = await inspect_upload(upload)
    object_key = f"users/{user.id}/{uuid4().hex}/{safe_name}"
    content_type = upload.content_type or "application/octet-stream"

    try:
        await storage_service.upload(upload.file, object_key, content_type)
        item = StoredFile(
            user_id=user.id,
            folder_id=folder.id,
            original_name=safe_name,
            object_key=object_key,
            content_type=content_type,
            size=size,
            checksum_sha256=checksum,
        )
        db.add(item)
        await db.commit()
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        try:
            await storage_service.delete(object_key)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail="Unable to store file") from None
    finally:
        await upload.close()
    await db.refresh(item)
    return item


@router.get("", response_model=list[FileResponse])
async def list_files(
    db: DbSession,
    user: CurrentUser,
    folder_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[StoredFile]:
    query = select(StoredFile).where(StoredFile.user_id == user.id)
    if folder_id:
        await owned_folder(db, user, folder_id)
        query = query.where(StoredFile.folder_id == folder_id)
    result = await db.scalars(
        query.order_by(StoredFile.updated_at.desc()).limit(limit).offset(offset)
    )
    return list(result)


@router.get("/{item_id}", response_model=FileDownloadResponse)
async def get_file(item_id: UUID, db: DbSession, user: CurrentUser) -> FileDownloadResponse:
    item = await owned_file(db, user, item_id)
    try:
        url = await storage_service.get_url(item.object_key)
    except Exception:
        raise HTTPException(status_code=502, detail="Unable to create download URL") from None
    response = FileDownloadResponse(
        **FileResponse.model_validate(item).model_dump(),
        download_url=url,
        expires_in=None
        if settings.r2_public_base_url
        else settings.r2_presigned_url_expire_seconds,
    )
    return response


@router.patch("/{item_id}/folder", response_model=FileResponse)
async def move_file(
    item_id: UUID, body: FileMoveRequest, db: DbSession, user: CurrentUser
) -> StoredFile:
    item = await owned_file(db, user, item_id)
    folder = await owned_folder(db, user, body.folder_id)
    item.folder_id = folder.id
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", response_model=Message)
async def delete_file(item_id: UUID, db: DbSession, user: CurrentUser) -> Message:
    item = await owned_file(db, user, item_id)
    try:
        await storage_service.delete(item.object_key)
    except Exception:
        raise HTTPException(status_code=502, detail="Unable to delete file from storage") from None
    await db.delete(item)
    await db.commit()
    return Message(message="File deleted")
