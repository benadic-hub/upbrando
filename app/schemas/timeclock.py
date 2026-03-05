from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CheckInOutOut(StrictModel):
    id: UUID
    user_id: UUID
    tenant_id: str
    work_date: date
    check_in_at: datetime | None
    check_out_at: datetime | None
    total_worked_minutes: int
    ot_minutes: int
    break_minutes: int
    lunch_minutes: int
    source: str
    notes: str | None


class ClockInIn(StrictModel):
    source: str = Field(default="api", max_length=40)
    notes: str | None = Field(default=None, max_length=1000)


class ClockOutIn(StrictModel):
    notes: str | None = Field(default=None, max_length=1000)


class BreakStartIn(StrictModel):
    kind: str = Field(pattern="^(BREAK|LUNCH)$")


class BreakEndIn(StrictModel):
    kind: str = Field(pattern="^(BREAK|LUNCH)$")


class TimeEntryListOut(StrictModel):
    entries: list[CheckInOutOut]


class TimeEntryTodayOut(StrictModel):
    entry: CheckInOutOut | None
