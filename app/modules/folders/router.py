from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import EnvVariable, Folder, Snippet, StoredFile
from app.dependencies import CurrentUser, DbSession
from app.modules.folders.schemas import FolderCreate, FolderResponse
from app.schemas.common import Message, PaginatedResponse, PaginationMeta
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


@router.get("", response_model=PaginatedResponse[FolderResponse])
async def list_folders(
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[FolderResponse]:
    folder_query = select(Folder).where(Folder.user_id == user.id)
    count = await db.scalar(select(func.count()).select_from(folder_query.subquery())) or 0
    snippet_count = (
        select(func.count(Snippet.id))
        .where(Snippet.folder_id == Folder.id, Snippet.user_id == user.id)
        .correlate(Folder)
        .scalar_subquery()
    )
    variable_count = (
        select(func.count(EnvVariable.id))
        .where(EnvVariable.folder_id == Folder.id, EnvVariable.user_id == user.id)
        .correlate(Folder)
        .scalar_subquery()
    )
    file_count = (
        select(func.count(StoredFile.id))
        .where(StoredFile.folder_id == Folder.id, StoredFile.user_id == user.id)
        .correlate(Folder)
        .scalar_subquery()
    )
    rows = await db.execute(
        select(Folder, (snippet_count + variable_count + file_count).label("total_items"))
        .where(Folder.user_id == user.id)
        .order_by(Folder.is_default.desc(), Folder.name)
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    data = [
        FolderResponse(
            id=folder.id,
            name=folder.name,
            is_default=folder.is_default,
            total_items=total_items,
            created_at=folder.created_at,
        )
        for folder, total_items in rows
    ]
    return PaginatedResponse[FolderResponse](
        data=data,
        meta=PaginationMeta(count=count, current_page=page, page_size=page_size),
    )


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
