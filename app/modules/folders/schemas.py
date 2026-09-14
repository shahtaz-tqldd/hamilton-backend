from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class FolderResponse(ORMModel):
    id: UUID
    name: str
    is_default: bool
    total_items: int = Field(default=0, ge=0)
    created_at: datetime
