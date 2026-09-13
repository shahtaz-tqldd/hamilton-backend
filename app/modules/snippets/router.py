from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.db.models import Snippet
from app.dependencies import CurrentUser, DbSession, owned_folder
from app.modules.snippets.schemas import SnippetCreate, SnippetResponse, SnippetUpdate
from app.schemas.common import Message

router = APIRouter(prefix="/snippets", tags=["Code snippets"])


async def owned_snippet(db: DbSession, user: CurrentUser, item_id: UUID) -> Snippet:
    item = await db.get(Snippet, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return item


@router.post("", response_model=SnippetResponse, status_code=status.HTTP_201_CREATED)
async def create_snippet(body: SnippetCreate, db: DbSession, user: CurrentUser) -> Snippet:
    folder = await owned_folder(db, user, body.folder_id)
    item = Snippet(user_id=user.id, folder_id=folder.id, **body.model_dump(exclude={"folder_id"}))
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("", response_model=list[SnippetResponse])
async def list_snippets(
    db: DbSession,
    user: CurrentUser,
    folder_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[Snippet]:
    query = select(Snippet).where(Snippet.user_id == user.id)
    if folder_id:
        await owned_folder(db, user, folder_id)
        query = query.where(Snippet.folder_id == folder_id)
    result = await db.scalars(query.order_by(Snippet.updated_at.desc()).limit(limit).offset(offset))
    return list(result)


@router.get("/{item_id}", response_model=SnippetResponse)
async def get_snippet(item_id: UUID, db: DbSession, user: CurrentUser) -> Snippet:
    return await owned_snippet(db, user, item_id)


@router.patch("/{item_id}", response_model=SnippetResponse)
async def update_snippet(
    item_id: UUID, body: SnippetUpdate, db: DbSession, user: CurrentUser
) -> Snippet:
    item = await owned_snippet(db, user, item_id)
    values = body.model_dump(exclude_unset=True)
    if "folder_id" in values:
        folder = await owned_folder(db, user, values.pop("folder_id"))
        item.folder_id = folder.id
    for key, value in values.items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", response_model=Message)
async def delete_snippet(item_id: UUID, db: DbSession, user: CurrentUser) -> Message:
    item = await owned_snippet(db, user, item_id)
    await db.delete(item)
    await db.commit()
    return Message(message="Snippet deleted")
