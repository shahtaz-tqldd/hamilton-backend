from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class SnippetCreate(BaseModel):
    folder_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    language: str | None = Field(None, max_length=60)
    content: str = Field(min_length=1)
    description: str | None = None


class SnippetUpdate(BaseModel):
    folder_id: UUID | None = None
    title: str | None = Field(None, min_length=1, max_length=200)
    language: str | None = Field(None, max_length=60)
    content: str | None = Field(None, min_length=1)
    description: str | None = None


class SnippetResponse(ORMModel):
    id: UUID
    folder_id: UUID
    title: str
    language: str | None
    content: str
    description: str | None
    created_at: datetime
    updated_at: datetime
