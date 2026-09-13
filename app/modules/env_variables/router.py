from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import EnvVariable
from app.dependencies import CurrentUser, DbSession, owned_folder
from app.modules.env_variables.schemas import (
    EnvVariableCreate,
    EnvVariableResponse,
    EnvVariableReveal,
    EnvVariableUpdate,
)
from app.schemas.common import Message
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
            status_code=409, detail="This key already exists in the folder"
        ) from None


@router.post("", response_model=EnvVariableResponse, status_code=status.HTTP_201_CREATED)
async def create_variable(
    body: EnvVariableCreate, db: DbSession, user: CurrentUser
) -> EnvVariableResponse:
    folder = await owned_folder(db, user, body.folder_id)
    item = EnvVariable(
        user_id=user.id,
        folder_id=folder.id,
        key=body.key,
        encrypted_value=encryption_service.encrypt(body.value),
        description=body.description,
    )
    db.add(item)
    await save(db)
    await db.refresh(item)
    return EnvVariableResponse.model_validate(item)


@router.get("", response_model=list[EnvVariableResponse])
async def list_variables(
    db: DbSession,
    user: CurrentUser,
    folder_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[EnvVariableResponse]:
    query = select(EnvVariable).where(EnvVariable.user_id == user.id)
    if folder_id:
        await owned_folder(db, user, folder_id)
        query = query.where(EnvVariable.folder_id == folder_id)
    items = await db.scalars(
        query.order_by(EnvVariable.updated_at.desc()).limit(limit).offset(offset)
    )
    return [EnvVariableResponse.model_validate(item) for item in items]


@router.get("/{item_id}", response_model=EnvVariableResponse)
async def get_variable(item_id: UUID, db: DbSession, user: CurrentUser) -> EnvVariableResponse:
    return EnvVariableResponse.model_validate(await owned_variable(db, user, item_id))


@router.post("/{item_id}/reveal", response_model=EnvVariableReveal)
async def reveal_variable(item_id: UUID, db: DbSession, user: CurrentUser) -> EnvVariableReveal:
    item = await owned_variable(db, user, item_id)
    return EnvVariableReveal(
        id=item.id, key=item.key, value=encryption_service.decrypt(item.encrypted_value)
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
    if "value" in values:
        item.encrypted_value = encryption_service.encrypt(values.pop("value"))
    for key, value in values.items():
        setattr(item, key, value)
    await save(db)
    await db.refresh(item)
    return EnvVariableResponse.model_validate(item)


@router.delete("/{item_id}", response_model=Message)
async def delete_variable(item_id: UUID, db: DbSession, user: CurrentUser) -> Message:
    item = await owned_variable(db, user, item_id)
    await db.delete(item)
    await db.commit()
    return Message(message="Environment variable deleted")
