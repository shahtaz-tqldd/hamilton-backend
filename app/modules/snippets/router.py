from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.db.models import Snippet
from app.dependencies import CurrentUser, DbSession, owned_folder
from app.modules.snippets.schemas import SnippetCreate, SnippetResponse, SnippetUpdate
from app.schemas.common import Message, PaginatedResponse, PaginationMeta

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


@router.get("", response_model=PaginatedResponse[SnippetResponse])
async def list_snippets(
    db: DbSession,
    user: CurrentUser,
    folder_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[SnippetResponse]:
    query = select(Snippet).where(Snippet.user_id == user.id)
    if folder_id:
        await owned_folder(db, user, folder_id)
        query = query.where(Snippet.folder_id == folder_id)
    count = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    result = await db.scalars(
        query.order_by(Snippet.updated_at.desc()).limit(page_size).offset((page - 1) * page_size)
    )
    return PaginatedResponse[SnippetResponse](
        data=[SnippetResponse.model_validate(item) for item in result],
        meta=PaginationMeta(count=count, current_page=page, page_size=page_size),
    )


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
