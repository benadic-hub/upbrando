from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnnouncementCreateIn(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=1, max_length=10000)


class AnnouncementOut(StrictModel):
    id: UUID
    tenant_id: str
    title: str
    body: str
    created_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class AnnouncementReadReceiptOut(StrictModel):
    announcement_id: UUID
    user_id: UUID
    read_at: datetime
