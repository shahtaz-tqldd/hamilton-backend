from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class EnvVariableCreate(BaseModel):
    folder_id: UUID | None = None
    key: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    value: str
    description: str | None = None


class EnvVariableUpdate(BaseModel):
    folder_id: UUID | None = None
    key: str | None = Field(None, min_length=1, max_length=255, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    value: str | None = None
    description: str | None = None


class EnvVariableResponse(ORMModel):
    id: UUID
    folder_id: UUID
    key: str
    value: str = "********"
    description: str | None
    created_at: datetime
    updated_at: datetime


class EnvVariableReveal(BaseModel):
    id: UUID
    key: str
    value: str
