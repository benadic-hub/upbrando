from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeCategoryCreateIn(StrictModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)


class KnowledgeCategoryOut(StrictModel):
    id: UUID
    tenant_id: str
    name: str
    description: str


class KnowledgeArticleCreateIn(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=1)
    category_id: UUID | None = None


class KnowledgeArticleUpdateIn(StrictModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    content: str | None = None
    category_id: UUID | None = None


class KnowledgeArticleOut(StrictModel):
    id: UUID
    tenant_id: str
    category_id: UUID | None
    title: str
    content: str
    created_by_user_id: UUID | None
    updated_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
