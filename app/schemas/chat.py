from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DmThreadCreateIn(StrictModel):
    other_user_id: UUID


class ChatThreadCreateIn(StrictModel):
    is_group: bool = False
    user_id: UUID | None = None
    member_ids: list[UUID] = Field(default_factory=list)
    title: str | None = Field(default=None, max_length=200)


class ChatThreadOut(StrictModel):
    id: UUID
    tenant_id: str
    is_dm: bool
    title: str | None
    created_by_user_id: UUID
    created_at: datetime
    unread_count: int = 0
    participant_ids: list[UUID]


class ChatMessageCreateIn(StrictModel):
    content: str = Field(min_length=1, max_length=8000)


class ChatMessageOut(StrictModel):
    id: UUID
    tenant_id: str
    thread_id: UUID
    sender_user_id: UUID
    content: str
    created_at: datetime


class MarkReadIn(StrictModel):
    up_to_message_id: UUID | None = None


class UnreadCounterOut(StrictModel):
    total_unread: int
    per_thread: dict[UUID, int]
