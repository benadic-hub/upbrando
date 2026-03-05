from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskCreateIn(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    status: str = Field(default="TODO", pattern="^(TODO|IN_PROGRESS|DONE|BLOCKED)$")
    assignee_user_id: UUID | None = None
    due_at: datetime | None = None


class TaskUpdateIn(StrictModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, pattern="^(TODO|IN_PROGRESS|DONE|BLOCKED)$")
    assignee_user_id: UUID | None = None
    due_at: datetime | None = None


class TaskOut(StrictModel):
    id: UUID
    tenant_id: str
    title: str
    description: str
    status: str
    assignee_user_id: UUID | None
    created_by_user_id: UUID | None
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TaskCommentCreateIn(StrictModel):
    body: str = Field(min_length=1, max_length=4000)


class TaskCommentOut(StrictModel):
    id: UUID
    tenant_id: str
    task_id: UUID
    author_user_id: UUID
    body: str
    created_at: datetime
