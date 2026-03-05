from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionAuthOut(StrictModel):
    ok: bool = True
    expires_in: int
    me: "MeOut"


class GoogleLoginIn(StrictModel):
    id_token: str = Field(min_length=20)


class BootstrapSuperadminIn(StrictModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    full_name: str = Field(min_length=2, max_length=200)


class MeOut(StrictModel):
    id: UUID
    tenant_id: str
    email: EmailStr
    full_name: str
    role: str
    employee_type: str
    permissions: list[str]
    department_id: UUID | None
    manager_id: UUID | None
    is_active: bool
    created_at: datetime


class DevLoginIn(StrictModel):
    email: EmailStr
    full_name: str | None = Field(default=None, min_length=2, max_length=200)


class MeEnvelopeOut(StrictModel):
    me: MeOut


class LogoutOut(StrictModel):
    ok: bool = True


SessionAuthOut.model_rebuild()
