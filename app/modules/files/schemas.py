from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import ORMModel


class FileResponse(ORMModel):
    id: UUID
    folder_id: UUID
    original_name: str
    content_type: str
    size: int
    checksum_sha256: str
    created_at: datetime
    updated_at: datetime


class FileDownloadResponse(FileResponse):
    download_url: str
    expires_in: int | None


class FileMoveRequest(BaseModel):
    folder_id: UUID
