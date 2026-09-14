from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str


class PaginationMeta(BaseModel):
    count: int = Field(ge=0)
    current_page: int = Field(ge=1)
    page_size: int = Field(ge=1)


ResponseItem = TypeVar("ResponseItem")


class PaginatedResponse(BaseModel, Generic[ResponseItem]):
    data: list[ResponseItem]
    meta: PaginationMeta


class ItemSummary(ORMModel):
    id: UUID
    folder_id: UUID
    name: str
    item_type: str
    created_at: datetime
    updated_at: datetime
