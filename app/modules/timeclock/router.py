from __future__ import annotations

import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_context, require_manager_role
from app.db.models import BreakKind, TimeBreakWindow, TimeEntry, User, UserRole
from app.db.session import get_db_session
from app.schemas.timeclock import (
    BreakEndIn,
    BreakStartIn,
    CheckInOutOut,
    ClockInIn,
    ClockOutIn,
    TimeEntryListOut,
    TimeEntryTodayOut,
)
from app.services.audit import write_audit_log
from app.services.timeclock import summarize_entry


router = APIRouter(prefix="/timeclock", tags=["timeclock"])


def _today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def _to_out(entry: TimeEntry) -> CheckInOutOut:
    return CheckInOutOut(
        id=entry.id,
        user_id=entry.user_id,
        tenant_id=entry.tenant_id,
        work_date=entry.work_date,
        check_in_at=entry.check_in_at,
        check_out_at=entry.check_out_at,
        total_worked_minutes=entry.total_worked_minutes,
        ot_minutes=entry.ot_minutes,
        break_minutes=entry.break_minutes,
        lunch_minutes=entry.lunch_minutes,
        source=entry.source,
        notes=entry.notes,
    )


async def _get_or_create_entry(db: AsyncSession, tenant_id: str, user_id: UUID, work_date: dt.date) -> TimeEntry:
    stmt = select(TimeEntry).where(
        and_(TimeEntry.tenant_id == tenant_id, TimeEntry.user_id == user_id, TimeEntry.work_date == work_date)
    )
    entry = (await db.execute(stmt)).scalar_one_or_none()
    if entry:
        return entry
    entry = TimeEntry(tenant_id=tenant_id, user_id=user_id, work_date=work_date)
    db.add(entry)
    await db.flush()
    return entry


async def _get_open_entry(db: AsyncSession, tenant_id: str, user_id: UUID) -> TimeEntry | None:
    stmt = (
        select(TimeEntry)
        .where(
            and_(
                TimeEntry.tenant_id == tenant_id,
                TimeEntry.user_id == user_id,
                TimeEntry.check_in_at.is_not(None),
                TimeEntry.check_out_at.is_(None),
            )
        )
        .order_by(TimeEntry.check_in_at.desc())
    )
    return (await db.execute(stmt)).scalars().first()


@router.post("/check-in", response_model=CheckInOutOut)
@router.post("/clock-in", response_model=CheckInOutOut)
async def check_in(
    payload: ClockInIn | None = None,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> CheckInOutOut:
    if ctx.user.role == UserRole.AI_AGENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI agents use heartbeat, not check-in/out")

    open_entry = await _get_open_entry(db, ctx.tenant_id, ctx.user.id)
    if open_entry is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already checked in")

    entry = await _get_or_create_entry(db, ctx.tenant_id, ctx.user.id, _today())
    if entry.check_in_at is not None and entry.check_out_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Existing closed entry for today")

    source = payload.source if payload else "api"
    notes = payload.notes.strip() if payload and payload.notes else None
    entry.check_in_at = dt.datetime.now(dt.timezone.utc)
    entry.source = source
    entry.notes = notes
    await db.commit()
    await db.refresh(entry)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CHECK_IN",
        target_type="time_entry",
        target_id=str(entry.id),
    )
    return _to_out(entry)


@router.post("/check-out", response_model=CheckInOutOut)
@router.post("/clock-out", response_model=CheckInOutOut)
async def check_out(
    payload: ClockOutIn | None = None,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> CheckInOutOut:
    if ctx.user.role == UserRole.AI_AGENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI agents use heartbeat, not check-in/out")

    entry = await _get_open_entry(db, ctx.tenant_id, ctx.user.id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Check-in is required before check-out")

    entry.check_out_at = dt.datetime.now(dt.timezone.utc)
    if payload and payload.notes is not None:
        entry.notes = payload.notes.strip() if payload.notes else None

    windows_stmt = select(TimeBreakWindow).where(
        and_(TimeBreakWindow.tenant_id == ctx.tenant_id, TimeBreakWindow.time_entry_id == entry.id)
    )
    windows = (await db.execute(windows_stmt)).scalars().all()
    worked, ot, brk, lunch = summarize_entry(user=ctx.user, entry=entry, windows=list(windows))
    entry.total_worked_minutes = worked
    entry.ot_minutes = ot
    entry.break_minutes = brk
    entry.lunch_minutes = lunch

    await db.commit()
    await db.refresh(entry)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CHECK_OUT",
        target_type="time_entry",
        target_id=str(entry.id),
        metadata={"worked_minutes": worked, "ot_minutes": ot},
    )
    return _to_out(entry)


@router.post("/breaks/start", response_model=CheckInOutOut)
@router.post("/break/start", response_model=CheckInOutOut)
async def start_break(
    payload: BreakStartIn,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> CheckInOutOut:
    if ctx.user.role == UserRole.AI_AGENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI agents use heartbeat, not breaks")
    entry = await _get_open_entry(db, ctx.tenant_id, ctx.user.id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Check-in required")

    kind = BreakKind(payload.kind)
    open_stmt = select(TimeBreakWindow).where(
        and_(
            TimeBreakWindow.tenant_id == ctx.tenant_id,
            TimeBreakWindow.time_entry_id == entry.id,
            TimeBreakWindow.kind == kind,
            TimeBreakWindow.end_at.is_(None),
        )
    )
    if (await db.execute(open_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{kind.value} already started")

    db.add(
        TimeBreakWindow(
            tenant_id=ctx.tenant_id,
            time_entry_id=entry.id,
            kind=kind,
            start_at=dt.datetime.now(dt.timezone.utc),
            end_at=None,
        )
    )
    await db.commit()
    await db.refresh(entry)
    return _to_out(entry)


@router.post("/breaks/end", response_model=CheckInOutOut)
@router.post("/break/end", response_model=CheckInOutOut)
async def end_break(
    payload: BreakEndIn,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> CheckInOutOut:
    if ctx.user.role == UserRole.AI_AGENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="AI agents use heartbeat, not breaks")
    entry = await _get_open_entry(db, ctx.tenant_id, ctx.user.id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Check-in required")
    kind = BreakKind(payload.kind)
    open_stmt = (
        select(TimeBreakWindow)
        .where(
            and_(
                TimeBreakWindow.tenant_id == ctx.tenant_id,
                TimeBreakWindow.time_entry_id == entry.id,
                TimeBreakWindow.kind == kind,
                TimeBreakWindow.end_at.is_(None),
            )
        )
        .order_by(TimeBreakWindow.start_at.desc())
    )
    window = (await db.execute(open_stmt)).scalars().first()
    if not window:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{kind.value} is not currently active")
    window.end_at = dt.datetime.now(dt.timezone.utc)
    await db.commit()
    await db.refresh(entry)
    return _to_out(entry)


@router.get("/me/today", response_model=TimeEntryTodayOut)
async def my_today(ctx=Depends(get_request_context), db: AsyncSession = Depends(get_db_session)) -> TimeEntryTodayOut:
    stmt = select(TimeEntry).where(
        and_(
            TimeEntry.tenant_id == ctx.tenant_id,
            TimeEntry.user_id == ctx.user.id,
            TimeEntry.work_date == _today(),
        )
    )
    entry = (await db.execute(stmt)).scalar_one_or_none()
    if not entry:
        return TimeEntryTodayOut(entry=None)
    return TimeEntryTodayOut(entry=_to_out(entry))


@router.get("/user/{user_id}/range", response_model=TimeEntryListOut)
async def user_range(
    user_id: UUID,
    from_date: dt.date | None = Query(default=None, alias="from"),
    to_date: dt.date | None = Query(default=None, alias="to"),
    _manager=Depends(require_manager_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> TimeEntryListOut:
    user_stmt = select(User).where(and_(User.id == user_id, User.tenant_id == ctx.tenant_id))
    if not (await db.execute(user_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    stmt = select(TimeEntry).where(and_(TimeEntry.tenant_id == ctx.tenant_id, TimeEntry.user_id == user_id))
    if from_date:
        stmt = stmt.where(TimeEntry.work_date >= from_date)
    if to_date:
        stmt = stmt.where(TimeEntry.work_date <= to_date)
    rows = (await db.execute(stmt.order_by(TimeEntry.work_date.desc()))).scalars().all()
    return TimeEntryListOut(entries=[_to_out(row) for row in rows])


@router.get("/entries", response_model=TimeEntryListOut)
async def list_entries(
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
    from_date: dt.date | None = Query(default=None),
    to_date: dt.date | None = Query(default=None),
    user_id: UUID | None = None,
) -> TimeEntryListOut:
    target_user_id = user_id or ctx.user.id
    if user_id and user_id != ctx.user.id and ctx.user.role.value not in {"SUPERADMIN", "ADMIN", "HOD"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another user's entries")

    stmt = select(TimeEntry).where(
        and_(TimeEntry.tenant_id == ctx.tenant_id, TimeEntry.user_id == target_user_id)
    )
    if from_date:
        stmt = stmt.where(TimeEntry.work_date >= from_date)
    if to_date:
        stmt = stmt.where(TimeEntry.work_date <= to_date)
    stmt = stmt.order_by(TimeEntry.work_date.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return TimeEntryListOut(entries=[_to_out(row) for row in rows])
