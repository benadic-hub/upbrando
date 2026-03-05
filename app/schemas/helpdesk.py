from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HelpdeskTicketCreateIn(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    assigned_to_user_id: UUID | None = None


class HelpdeskTicketUpdateIn(StrictModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: str | None = Field(default=None, pattern="^(OPEN|IN_PROGRESS|RESOLVED|CLOSED)$")
    assigned_to_user_id: UUID | None = None


class HelpdeskTicketOut(StrictModel):
    id: UUID
    tenant_id: str
    title: str
    description: str
    status: str
    requested_by_user_id: UUID
    assigned_to_user_id: UUID | None
    task_id: UUID | None
    created_at: datetime
    updated_at: datetime
