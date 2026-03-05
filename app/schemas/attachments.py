from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AttachmentPresignUploadIn(StrictModel):
    filename: str = Field(min_length=1, max_length=500)
    content_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(gt=0)
    owner_type: str = Field(default="", max_length=80)
    owner_id: UUID | None = None


class AttachmentPresignUploadOut(StrictModel):
    attachment_id: UUID
    s3_key: str
    upload_url: str


class AttachmentPresignDownloadOut(StrictModel):
    download_url: str


class AttachmentOut(StrictModel):
    id: UUID
    tenant_id: str
    owner_type: str
    owner_id: UUID | None
    filename: str
    content_type: str
    size_bytes: int
    s3_key: str
    created_by_user_id: UUID | None
    created_at: datetime
