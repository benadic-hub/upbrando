from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_context, require_admin_role
from app.core.security import now_utc
from app.db.models import Announcement, AnnouncementRead
from app.db.session import get_db_session
from app.schemas.announcements import AnnouncementCreateIn, AnnouncementOut, AnnouncementReadReceiptOut
from app.services.audit import write_audit_log


router = APIRouter(prefix="/announcements", tags=["announcements"])


def _to_out(row: Announcement) -> AnnouncementOut:
    return AnnouncementOut(
        id=row.id,
        tenant_id=row.tenant_id,
        title=row.title,
        body=row.body,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("", response_model=AnnouncementOut)
async def create_announcement(
    payload: AnnouncementCreateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AnnouncementOut:
    row = Announcement(
        tenant_id=ctx.tenant_id,
        title=payload.title.strip(),
        body=payload.body.strip(),
        created_by_user_id=ctx.user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_ANNOUNCEMENT",
        target_type="announcement",
        target_id=str(row.id),
    )
    return _to_out(row)


@router.get("", response_model=list[AnnouncementOut])
async def list_announcements(ctx=Depends(get_request_context), db: AsyncSession = Depends(get_db_session)) -> list[AnnouncementOut]:
    stmt = select(Announcement).where(Announcement.tenant_id == ctx.tenant_id).order_by(Announcement.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [_to_out(row) for row in rows]


@router.post("/{announcement_id}/read")
async def mark_read(
    announcement_id: UUID,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    announcement_stmt = select(Announcement).where(
        and_(Announcement.id == announcement_id, Announcement.tenant_id == ctx.tenant_id)
    )
    if not (await db.execute(announcement_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    read_stmt = select(AnnouncementRead).where(
        and_(
            AnnouncementRead.tenant_id == ctx.tenant_id,
            AnnouncementRead.announcement_id == announcement_id,
            AnnouncementRead.user_id == ctx.user.id,
        )
    )
    read = (await db.execute(read_stmt)).scalar_one_or_none()
    if read:
        read.read_at = now_utc()
    else:
        db.add(
            AnnouncementRead(
                tenant_id=ctx.tenant_id,
                announcement_id=announcement_id,
                user_id=ctx.user.id,
                read_at=now_utc(),
            )
        )
    await db.commit()
    return {"ok": True}


@router.get("/{announcement_id}/receipts", response_model=list[AnnouncementReadReceiptOut])
async def read_receipts(
    announcement_id: UUID,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[AnnouncementReadReceiptOut]:
    stmt = select(AnnouncementRead).where(
        and_(AnnouncementRead.tenant_id == ctx.tenant_id, AnnouncementRead.announcement_id == announcement_id)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        AnnouncementReadReceiptOut(
            announcement_id=row.announcement_id,
            user_id=row.user_id,
            read_at=row.read_at,
        )
        for row in rows
    ]

