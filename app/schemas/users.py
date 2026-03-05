from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DepartmentCreateIn(StrictModel):
    name: str = Field(min_length=2, max_length=128)
    description: str = Field(default="", max_length=500)
    parent_id: UUID | None = None


class DepartmentOut(StrictModel):
    id: UUID
    tenant_id: str
    name: str
    description: str
    parent_id: UUID | None


class DepartmentUpdateIn(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=128)
    description: str | None = Field(default=None, max_length=500)
    parent_id: UUID | None = None


class InviteCreateIn(StrictModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    role: str = Field(pattern="^(ADMIN|HOD|EMPLOYEE|AI_AGENT)$")
    department_id: UUID | None = None
    manager_id: UUID | None = None
    tools_allowed: list[str] = Field(default_factory=list)
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InviteOut(StrictModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str
    department_id: UUID | None
    manager_id: UUID | None
    tools_allowed: list[str]
    expires_at: datetime
    accepted_at: datetime | None


class UserCreateIn(StrictModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    role: str = Field(pattern="^(SUPERADMIN|ADMIN|HOD|EMPLOYEE|AI_AGENT)$")
    department_id: UUID | None = None
    manager_id: UUID | None = None
    tools_allowed: list[str] = Field(default_factory=list)
    is_active: bool = True
    employee_type: str = Field(default="HUMAN", pattern="^(HUMAN|AGENT)$")


class UserRoleUpdateIn(StrictModel):
    role: str = Field(pattern="^(SUPERADMIN|ADMIN|HOD|EMPLOYEE|AI_AGENT)$")


class UserManagerUpdateIn(StrictModel):
    manager_id: UUID | None = None


class UserScheduleUpdateIn(StrictModel):
    work_start_time: time | None = None
    work_end_time: time | None = None
    break_minutes: int | None = Field(default=None, ge=0, le=120)
    lunch_minutes: int | None = Field(default=None, ge=0, le=180)


class UserOut(StrictModel):
    id: UUID
    tenant_id: str
    email: EmailStr
    full_name: str
    role: str
    department_id: UUID | None
    manager_id: UUID | None
    is_active: bool
    employee_type: str
    work_start_time: time
    work_end_time: time
    break_minutes: int
    lunch_minutes: int
    created_at: datetime
    updated_at: datetime


class OrgNodeOut(StrictModel):
    user_id: UUID
    full_name: str
    role: str
    department_id: UUID | None
    manager_id: UUID | None
    children: list["OrgNodeOut"] = Field(default_factory=list)


OrgNodeOut.model_rebuild()


class UserUpdateIn(StrictModel):
    role: str | None = Field(default=None, pattern="^(SUPERADMIN|ADMIN|HOD|EMPLOYEE|AI_AGENT)$")
    department_id: UUID | None = None
    manager_id: UUID | None = None
    is_active: bool | None = None
    employee_type: str | None = Field(default=None, pattern="^(HUMAN|AGENT)$")
