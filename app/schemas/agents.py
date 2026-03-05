from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AgentCreateIn(StrictModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    department_id: UUID | None = None
    manager_id: UUID | None = None
    tools_allowed: list[str] = Field(default_factory=list)


class AgentUpdateIn(StrictModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    department_id: UUID | None = None
    manager_id: UUID | None = None
    tools_allowed: list[str] | None = None
    is_active: bool | None = None


class AgentOut(StrictModel):
    user_id: UUID
    tenant_id: str
    email: EmailStr
    full_name: str
    role: str
    department_id: UUID | None
    manager_id: UUID | None
    tools_allowed: list[str]
    last_heartbeat_at: datetime | None
    is_active: bool


class AgentHeartbeatIn(StrictModel):
    activity: str = Field(default="", max_length=500)


class AgentHeartbeatOut(StrictModel):
    id: UUID
    agent_user_id: UUID
    activity: str
    created_at: datetime


class AgentPermissionCheckIn(StrictModel):
    tool_name: str = Field(min_length=1, max_length=120)
    department_id: UUID | None = None


class AgentPermissionCheckOut(StrictModel):
    allowed: bool
    reason: str
