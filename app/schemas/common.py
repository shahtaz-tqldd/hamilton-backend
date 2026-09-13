from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str


class Pagination(BaseModel):
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class ItemSummary(ORMModel):
    id: UUID
    folder_id: UUID
    name: str
    item_type: str
    created_at: datetime
    updated_at: datetime
