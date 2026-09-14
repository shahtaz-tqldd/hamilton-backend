from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import EnvVariable, EnvVariableEntry
from app.dependencies import CurrentUser, DbSession, owned_folder
from app.modules.env_variables.schemas import (
    EnvVariableCreate,
    EnvVariableItem,
    EnvVariableItemResponse,
    EnvVariableResponse,
    EnvVariableReveal,
    EnvVariableUpdate,
)
from app.schemas.common import Message, PaginatedResponse, PaginationMeta
from app.services.encryption import encryption_service

router = APIRouter(prefix="/env-variables", tags=["Environment variables"])


async def owned_variable(db: DbSession, user: CurrentUser, item_id: UUID) -> EnvVariable:
    item = await db.get(EnvVariable, item_id)
    if not item or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    return item


async def save(db: DbSession) -> None:
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The group name must be unique in its folder and its keys must be unique",
        ) from None


def masked_response(item: EnvVariable) -> EnvVariableResponse:
    return EnvVariableResponse(
        id=item.id,
        folder_id=item.folder_id,
        name=item.name,
        variables=[EnvVariableItemResponse(key=entry.key) for entry in item.entries],
        description=item.description,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def encrypted_entries(variables: list[EnvVariableItem]) -> list[EnvVariableEntry]:
    return [
        EnvVariableEntry(
            key=variable.key,
            encrypted_value=encryption_service.encrypt(variable.value),
            position=position,
        )
        for position, variable in enumerate(variables)
    ]


@router.post("", response_model=EnvVariableResponse, status_code=status.HTTP_201_CREATED)
async def create_variable(
    body: EnvVariableCreate, db: DbSession, user: CurrentUser
) -> EnvVariableResponse:
    folder = await owned_folder(db, user, body.folder_id)
    item = EnvVariable(
        user_id=user.id,
        folder_id=folder.id,
        name=body.name,
        description=body.description,
        entries=encrypted_entries(body.variables),
    )
    db.add(item)
    await save(db)
    await db.refresh(item)
    return masked_response(item)


@router.get("", response_model=PaginatedResponse[EnvVariableResponse])
async def list_variables(
    db: DbSession,
    user: CurrentUser,
    folder_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[EnvVariableResponse]:
    query = select(EnvVariable).where(EnvVariable.user_id == user.id)
    if folder_id:
        await owned_folder(db, user, folder_id)
        query = query.where(EnvVariable.folder_id == folder_id)
    count = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = await db.scalars(
        query.order_by(EnvVariable.updated_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return PaginatedResponse[EnvVariableResponse](
        data=[masked_response(item) for item in items],
        meta=PaginationMeta(count=count, current_page=page, page_size=page_size),
    )


@router.get("/{item_id}", response_model=EnvVariableResponse)
async def get_variable(item_id: UUID, db: DbSession, user: CurrentUser) -> EnvVariableResponse:
    return masked_response(await owned_variable(db, user, item_id))


@router.post("/{item_id}/reveal", response_model=EnvVariableReveal)
async def reveal_variable(item_id: UUID, db: DbSession, user: CurrentUser) -> EnvVariableReveal:
    item = await owned_variable(db, user, item_id)
    return EnvVariableReveal(
        id=item.id,
        folder_id=item.folder_id,
        name=item.name,
        variables=[
            EnvVariableItem(
                key=entry.key,
                value=encryption_service.decrypt(entry.encrypted_value),
            )
            for entry in item.entries
        ],
        description=item.description,
    )


@router.patch("/{item_id}", response_model=EnvVariableResponse)
async def update_variable(
    item_id: UUID, body: EnvVariableUpdate, db: DbSession, user: CurrentUser
) -> EnvVariableResponse:
    item = await owned_variable(db, user, item_id)
    values = body.model_dump(exclude_unset=True)
    if "folder_id" in values:
        folder = await owned_folder(db, user, values.pop("folder_id"))
        item.folder_id = folder.id
    if "variables" in values:
        values.pop("variables")
        item.entries.clear()
        await db.flush()
        item.entries = encrypted_entries(body.variables or [])
        item.updated_at = datetime.now(UTC)
    for key, value in values.items():
        setattr(item, key, value)
    await save(db)
    await db.refresh(item)
    return masked_response(item)


@router.delete("/{item_id}", response_model=Message)
async def delete_variable(item_id: UUID, db: DbSession, user: CurrentUser) -> Message:
    item = await owned_variable(db, user, item_id)
    await db.delete(item)
    await db.commit()
    return Message(message="Environment variable group deleted")
