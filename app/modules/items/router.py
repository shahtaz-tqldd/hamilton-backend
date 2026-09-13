from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import literal, select, union_all

from app.db.models import EnvVariable, Snippet, StoredFile
from app.dependencies import CurrentUser, DbSession, owned_folder
from app.schemas.common import ItemSummary

router = APIRouter(prefix="/items", tags=["All items"])


@router.get("", response_model=list[ItemSummary])
async def list_all_items(
    db: DbSession,
    user: CurrentUser,
    folder_id: UUID | None = None,
    item_type: Literal["snippet", "env_variable", "file"] | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[ItemSummary]:
    if folder_id:
        await owned_folder(db, user, folder_id)

    queries = []
    if item_type in (None, "snippet"):
        query = select(
            Snippet.id,
            Snippet.folder_id,
            Snippet.title.label("name"),
            literal("snippet").label("item_type"),
            Snippet.created_at,
            Snippet.updated_at,
        ).where(Snippet.user_id == user.id)
        queries.append(query.where(Snippet.folder_id == folder_id) if folder_id else query)
    if item_type in (None, "env_variable"):
        query = select(
            EnvVariable.id,
            EnvVariable.folder_id,
            EnvVariable.key.label("name"),
            literal("env_variable").label("item_type"),
            EnvVariable.created_at,
            EnvVariable.updated_at,
        ).where(EnvVariable.user_id == user.id)
        queries.append(query.where(EnvVariable.folder_id == folder_id) if folder_id else query)
    if item_type in (None, "file"):
        query = select(
            StoredFile.id,
            StoredFile.folder_id,
            StoredFile.original_name.label("name"),
            literal("file").label("item_type"),
            StoredFile.created_at,
            StoredFile.updated_at,
        ).where(StoredFile.user_id == user.id)
        queries.append(query.where(StoredFile.folder_id == folder_id) if folder_id else query)

    statement = union_all(*queries).subquery()
    rows = (
        await db.execute(
            select(statement).order_by(statement.c.updated_at.desc()).limit(limit).offset(offset)
        )
    ).mappings()
    return [ItemSummary.model_validate(row) for row in rows]
