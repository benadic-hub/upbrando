from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_context, require_admin_role
from app.core.config import settings
from app.db.models import ChatMessage, ChatThread, Department, Task, TimeEntry, User
from app.db.session import get_db_session


router = APIRouter(tags=["ops"])


@router.get("/health")
@router.get("/api/v1/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@router.get("/db-test")
@router.get("/api/v1/db-test")
async def db_test(db: AsyncSession = Depends(get_db_session)) -> dict[str, bool]:
    await db.execute(text("SELECT 1"))
    return {"db_ok": True}


@router.get("/version")
@router.get("/api/v1/version")
async def version() -> dict[str, str]:
    return {"name": settings.APP_NAME, "version": settings.APP_VERSION}


@router.get("/ops/pilot-status", dependencies=[Depends(require_admin_role)])
async def pilot_status(
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, int]:
    users = int((await db.execute(select(func.count()).select_from(User).where(User.tenant_id == ctx.tenant_id))).scalar_one())
    departments = int(
        (await db.execute(select(func.count()).select_from(Department).where(Department.tenant_id == ctx.tenant_id))).scalar_one()
    )
    tasks = int((await db.execute(select(func.count()).select_from(Task).where(Task.tenant_id == ctx.tenant_id))).scalar_one())
    threads = int(
        (await db.execute(select(func.count()).select_from(ChatThread).where(ChatThread.tenant_id == ctx.tenant_id))).scalar_one()
    )
    messages = int(
        (await db.execute(select(func.count()).select_from(ChatMessage).where(ChatMessage.tenant_id == ctx.tenant_id))).scalar_one()
    )
    entries = int(
        (await db.execute(select(func.count()).select_from(TimeEntry).where(TimeEntry.tenant_id == ctx.tenant_id))).scalar_one()
    )
    active_today = int(
        (
            await db.execute(
                select(func.count(func.distinct(TimeEntry.user_id))).where(
                    and_(TimeEntry.tenant_id == ctx.tenant_id, TimeEntry.work_date == func.current_date())
                )
            )
        ).scalar_one()
    )
    return {
        "users": users,
        "departments": departments,
        "tasks": tasks,
        "chat_threads": threads,
        "chat_messages": messages,
        "time_entries": entries,
        "active_today": active_today,
    }
