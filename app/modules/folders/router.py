from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import Folder, StoredFile
from app.dependencies import CurrentUser, DbSession
from app.modules.folders.schemas import FolderCreate, FolderResponse
from app.schemas.common import Message
from app.services.storage import storage_service

router = APIRouter(prefix="/folders", tags=["Folders"])


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(body: FolderCreate, db: DbSession, user: CurrentUser) -> Folder:
    folder = Folder(user_id=user.id, name=body.name.strip(), is_default=False)
    db.add(folder)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="A folder with this name already exists"
        ) from None
    await db.refresh(folder)
    return folder


@router.get("", response_model=list[FolderResponse])
async def list_folders(db: DbSession, user: CurrentUser) -> list[Folder]:
    result = await db.scalars(
        select(Folder)
        .where(Folder.user_id == user.id)
        .order_by(Folder.is_default.desc(), Folder.name)
    )
    return list(result)


@router.delete("/{folder_id}", response_model=Message)
async def delete_folder(folder_id: UUID, db: DbSession, user: CurrentUser) -> Message:
    folder = await db.get(Folder, folder_id)
    if not folder or folder.user_id != user.id:
        raise HTTPException(status_code=404, detail="Folder not found")
    if folder.is_default:
        raise HTTPException(status_code=400, detail="The default folder cannot be deleted")
    object_keys = list(
        await db.scalars(select(StoredFile.object_key).where(StoredFile.folder_id == folder.id))
    )
    for object_key in object_keys:
        try:
            await storage_service.delete(object_key)
        except Exception:
            raise HTTPException(
                status_code=502, detail="Unable to remove all folder files from storage"
            ) from None
    await db.delete(folder)
    await db.commit()
    return Message(message="Folder deleted")
