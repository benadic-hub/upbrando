from __future__ import annotations

import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_context, require_admin_ip, require_admin_role
from app.core.email_policy import is_allowed_company_email
from app.core.security import now_utc
from app.db.models import (
    AgentProfile,
    Announcement,
    AuditLog,
    Department,
    EmployeeType,
    HelpdeskTicket,
    Invite,
    Task,
    TaskStatus,
    TicketStatus,
    TimeEntry,
    User,
    UserRole,
)
from app.db.session import get_db_session
from app.schemas.announcements import AnnouncementCreateIn, AnnouncementOut
from app.schemas.users import (
    DepartmentCreateIn,
    DepartmentOut,
    InviteCreateIn,
    InviteOut,
    UserCreateIn,
    UserOut,
    UserRoleUpdateIn,
)
from app.services.bootstrap import get_bootstrap_status, seed_superadmin_from_settings
from app.services.audit import write_audit_log


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_ip), Depends(require_admin_role)])


def _company_email_only(email: str) -> bool:
    return is_allowed_company_email(email)


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        department_id=user.department_id,
        manager_id=user.manager_id,
        is_active=user.is_active,
        employee_type=user.employee_type.value,
        work_start_time=user.work_start_time,
        work_end_time=user.work_end_time,
        break_minutes=user.break_minutes,
        lunch_minutes=user.lunch_minutes,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _can_assign_role(actor_role: UserRole, target_role: UserRole) -> bool:
    if actor_role == UserRole.SUPERADMIN:
        return True
    if actor_role == UserRole.ADMIN:
        return target_role in {UserRole.HOD, UserRole.EMPLOYEE, UserRole.AI_AGENT}
    return False


def _to_invite_out(invite: Invite) -> InviteOut:
    return InviteOut(
        id=invite.id,
        email=invite.email,
        full_name=invite.full_name,
        role=invite.role.value,
        department_id=invite.department_id,
        manager_id=invite.manager_id,
        tools_allowed=invite.tools_allowed or [],
        expires_at=invite.expires_at,
        accepted_at=invite.accepted_at,
    )


@router.post("/departments", response_model=DepartmentOut)
async def create_department(
    payload: DepartmentCreateIn,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> DepartmentOut:
    exists_stmt = select(Department).where(
        and_(Department.tenant_id == ctx.tenant_id, func.lower(Department.name) == payload.name.lower())
    )
    if (await db.execute(exists_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Department already exists")

    department = Department(
        tenant_id=ctx.tenant_id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        parent_id=payload.parent_id,
    )
    db.add(department)
    await db.commit()
    await db.refresh(department)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_DEPARTMENT",
        target_type="department",
        target_id=str(department.id),
    )
    return DepartmentOut(
        id=department.id,
        tenant_id=department.tenant_id,
        name=department.name,
        description=department.description,
        parent_id=department.parent_id,
    )


@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(ctx=Depends(get_request_context), db: AsyncSession = Depends(get_db_session)) -> list[DepartmentOut]:
    stmt = select(Department).where(Department.tenant_id == ctx.tenant_id).order_by(Department.name.asc())
    departments = (await db.execute(stmt)).scalars().all()
    return [
        DepartmentOut(id=d.id, tenant_id=d.tenant_id, name=d.name, description=d.description, parent_id=d.parent_id)
        for d in departments
    ]


@router.post("/invites", response_model=InviteOut)
async def create_invite(
    payload: InviteCreateIn,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> InviteOut:
    target_role = UserRole(payload.role)
    if not _can_assign_role(ctx.user.role, target_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role to invite this user role")
    if not _company_email_only(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only company emails are allowed")

    if payload.department_id:
        dep_stmt = select(Department).where(
            and_(Department.id == payload.department_id, Department.tenant_id == ctx.tenant_id)
        )
        if not (await db.execute(dep_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    if payload.manager_id:
        manager_stmt = select(User).where(and_(User.id == payload.manager_id, User.tenant_id == ctx.tenant_id))
        if not (await db.execute(manager_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")

    existing_user_stmt = select(User).where(
        and_(User.tenant_id == ctx.tenant_id, func.lower(User.email) == payload.email.lower())
    )
    if (await db.execute(existing_user_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    pending_invite_stmt = select(Invite).where(
        and_(
            Invite.tenant_id == ctx.tenant_id,
            func.lower(Invite.email) == payload.email.lower(),
            Invite.accepted_at.is_(None),
            Invite.expires_at >= now_utc(),
        )
    )
    if (await db.execute(pending_invite_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active invite already exists")

    invite = Invite(
        tenant_id=ctx.tenant_id,
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        role=target_role,
        department_id=payload.department_id,
        manager_id=payload.manager_id,
        tools_allowed=payload.tools_allowed if target_role == UserRole.AI_AGENT else [],
        invited_by_user_id=ctx.user.id,
        expires_at=now_utc() + dt.timedelta(days=payload.expires_in_days),
        accepted_at=None,
        accepted_user_id=None,
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_INVITE",
        target_type="invite",
        target_id=str(invite.id),
        metadata={"email": invite.email, "role": invite.role.value},
    )
    return _to_invite_out(invite)


@router.get("/invites", response_model=list[InviteOut])
async def list_invites(ctx=Depends(get_request_context), db: AsyncSession = Depends(get_db_session)) -> list[InviteOut]:
    stmt = select(Invite).where(Invite.tenant_id == ctx.tenant_id).order_by(Invite.created_at.desc())
    invites = (await db.execute(stmt)).scalars().all()
    return [_to_invite_out(inv) for inv in invites]


@router.post("/users", response_model=UserOut)
async def create_user_direct(
    payload: UserCreateIn,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> UserOut:
    target_role = UserRole(payload.role)
    if not _can_assign_role(ctx.user.role, target_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role to create this user role")
    if not _company_email_only(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only company emails are allowed")

    existing_stmt = select(User).where(
        and_(User.tenant_id == ctx.tenant_id, func.lower(User.email) == payload.email.lower())
    )
    if (await db.execute(existing_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    if payload.department_id:
        dep_stmt = select(Department).where(
            and_(Department.id == payload.department_id, Department.tenant_id == ctx.tenant_id)
        )
        if not (await db.execute(dep_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    if payload.manager_id:
        manager_stmt = select(User).where(and_(User.id == payload.manager_id, User.tenant_id == ctx.tenant_id))
        if not (await db.execute(manager_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")

    user = User(
        tenant_id=ctx.tenant_id,
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        role=target_role,
        google_sub=None,
        password_hash=None,
        department_id=payload.department_id,
        manager_id=payload.manager_id,
        is_active=payload.is_active,
        employee_type=EmployeeType(payload.employee_type),
    )
    db.add(user)
    await db.flush()
    if target_role == UserRole.AI_AGENT:
        db.add(
            AgentProfile(
                tenant_id=ctx.tenant_id,
                user_id=user.id,
                tools_allowed=payload.tools_allowed,
                created_by_user_id=ctx.user.id,
                last_heartbeat_at=None,
            )
        )

    await db.commit()
    await db.refresh(user)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_USER",
        target_type="user",
        target_id=str(user.id),
        metadata={"email": user.email, "role": user.role.value},
    )
    return _to_user_out(user)


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: UUID,
    payload: UserRoleUpdateIn,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> UserOut:
    user_stmt = select(User).where(and_(User.id == user_id, User.tenant_id == ctx.tenant_id))
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_role = UserRole(payload.role)
    if not _can_assign_role(ctx.user.role, new_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role to assign this role")

    user.role = new_role
    await db.flush()

    profile_stmt = select(AgentProfile).where(
        and_(AgentProfile.user_id == user.id, AgentProfile.tenant_id == ctx.tenant_id)
    )
    profile = (await db.execute(profile_stmt)).scalar_one_or_none()
    if new_role == UserRole.AI_AGENT and not profile:
        db.add(
            AgentProfile(
                tenant_id=ctx.tenant_id,
                user_id=user.id,
                tools_allowed=[],
                created_by_user_id=ctx.user.id,
                last_heartbeat_at=None,
            )
        )
    if new_role != UserRole.AI_AGENT and profile:
        await db.delete(profile)

    await db.commit()
    await db.refresh(user)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CHANGE_USER_ROLE",
        target_type="user",
        target_id=str(user.id),
        metadata={"new_role": new_role.value},
    )
    return _to_user_out(user)


@router.get("/bootstrap/status")
async def bootstrap_status(
    _ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    status_info = await get_bootstrap_status(db)
    return {
        "tenant_exists": status_info.tenant_exists,
        "root_department_exists": status_info.root_department_exists,
        "superadmin_exists": status_info.superadmin_exists,
        "total_users": status_info.total_users,
    }


@router.post("/bootstrap/seed")
async def bootstrap_seed(
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    if ctx.user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="SUPERADMIN role required")
    created, user = await seed_superadmin_from_settings(db)
    return {"created": created, "email": user.email if user else None}


@router.get("/overview")
async def admin_overview(
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    today = now_utc().date()
    users_count = int(
        (await db.execute(select(func.count()).select_from(User).where(User.tenant_id == ctx.tenant_id))).scalar_one()
    )
    active_today = int(
        (
            await db.execute(
                select(func.count(func.distinct(TimeEntry.user_id))).where(
                    and_(TimeEntry.tenant_id == ctx.tenant_id, TimeEntry.work_date == today, TimeEntry.check_in_at.is_not(None))
                )
            )
        ).scalar_one()
    )
    open_tasks = int(
        (
            await db.execute(
                select(func.count()).select_from(Task).where(
                    and_(
                        Task.tenant_id == ctx.tenant_id,
                        Task.status.in_([TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]),
                    )
                )
            )
        ).scalar_one()
    )
    open_helpdesk = int(
        (
            await db.execute(
                select(func.count()).select_from(HelpdeskTicket).where(
                    and_(
                        HelpdeskTicket.tenant_id == ctx.tenant_id,
                        HelpdeskTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]),
                    )
                )
            )
        ).scalar_one()
    )
    return {
        "users": users_count,
        "active_today": active_today,
        "open_tasks": open_tasks,
        "open_helpdesk": open_helpdesk,
    }


@router.get("/audit/recent")
async def admin_audit_recent(
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 50,
) -> list[dict]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == ctx.tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(min(max(limit, 1), 200))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "actor": row.actor_user_id,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "at": row.created_at,
        }
        for row in rows
    ]


@router.post("/announcements", response_model=AnnouncementOut)
async def admin_create_announcement(
    payload: AnnouncementCreateIn,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AnnouncementOut:
    title = payload.title.strip()
    body = payload.body.strip()
    row = Announcement(
        tenant_id=ctx.tenant_id,
        title=title,
        body=body,
        created_by_user_id=ctx.user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return AnnouncementOut(
        id=row.id,
        tenant_id=row.tenant_id,
        title=row.title,
        body=row.body,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/audit-logs")
async def list_audit_logs(
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 100,
) -> list[dict]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == ctx.tenant_id)
        .order_by(AuditLog.created_at.desc())
        .limit(min(max(limit, 1), 500))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": row.id,
            "tenant_id": row.tenant_id,
            "actor_user_id": row.actor_user_id,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "metadata": row.metadata_json,
            "created_at": row.created_at,
        }
        for row in rows
    ]
