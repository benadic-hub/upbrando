from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FormTemplateCreateIn(StrictModel):
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=2000)
    fields_schema: list[dict] = Field(default_factory=list)


class FormTemplateUpdateIn(StrictModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    fields_schema: list[dict] | None = None


class FormTemplateOut(StrictModel):
    id: UUID
    tenant_id: str
    name: str
    description: str
    fields_schema: list[dict]
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class FormSubmissionCreateIn(StrictModel):
    answers: dict


class FormSubmissionOut(StrictModel):
    id: UUID
    tenant_id: str
    template_id: UUID
    submitted_by_user_id: UUID
    answers: dict
    created_at: datetime
    updated_at: datetime
