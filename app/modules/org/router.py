from __future__ import annotations

import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_context, require_admin_role
from app.core.email_policy import is_allowed_company_email
from app.core.security import now_utc
from app.db.models import AgentProfile, Department, EmployeeType, Invite, User, UserRole
from app.db.session import get_db_session
from app.schemas.users import (
    DepartmentCreateIn,
    DepartmentOut,
    DepartmentUpdateIn,
    InviteCreateIn,
    InviteOut,
    OrgNodeOut,
    UserManagerUpdateIn,
    UserOut,
    UserScheduleUpdateIn,
    UserUpdateIn,
)
from app.services.audit import write_audit_log


router = APIRouter(prefix="/org", tags=["org"])


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


def _company_email_only(email: str) -> bool:
    return is_allowed_company_email(email)


def _can_assign_role(actor_role: UserRole, target_role: UserRole) -> bool:
    if actor_role == UserRole.SUPERADMIN:
        return True
    if actor_role == UserRole.ADMIN:
        return target_role in {UserRole.HOD, UserRole.EMPLOYEE, UserRole.AI_AGENT}
    return False


@router.post("/departments", response_model=DepartmentOut)
async def create_department(
    payload: DepartmentCreateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> DepartmentOut:
    exists_stmt = select(Department).where(
        and_(Department.tenant_id == ctx.tenant_id, func.lower(Department.name) == payload.name.lower())
    )
    if (await db.execute(exists_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Department already exists")

    if payload.parent_id:
        parent_stmt = select(Department).where(
            and_(Department.id == payload.parent_id, Department.tenant_id == ctx.tenant_id)
        )
        if not (await db.execute(parent_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent department not found")

    row = Department(
        tenant_id=ctx.tenant_id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        parent_id=payload.parent_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_DEPARTMENT",
        target_type="department",
        target_id=str(row.id),
    )
    return DepartmentOut(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        description=row.description,
        parent_id=row.parent_id,
    )


@router.get("/users", response_model=list[UserOut])
async def list_users(
    search: str | None = Query(default=None, min_length=1),
    department_id: UUID | None = None,
    role: str | None = Query(default=None, pattern="^(SUPERADMIN|ADMIN|HOD|EMPLOYEE|AI_AGENT)$"),
    is_active: bool | None = None,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[UserOut]:
    stmt = select(User).where(User.tenant_id == ctx.tenant_id)
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(User.full_name).like(like),
                func.lower(User.email).like(like),
            )
        )
    if department_id:
        stmt = stmt.where(User.department_id == department_id)
    if role:
        stmt = stmt.where(User.role == UserRole(role))
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))

    users = (await db.execute(stmt.order_by(User.full_name.asc()))).scalars().all()
    return [_to_user_out(u) for u in users]


@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(ctx=Depends(get_request_context), db: AsyncSession = Depends(get_db_session)) -> list[DepartmentOut]:
    stmt = select(Department).where(Department.tenant_id == ctx.tenant_id).order_by(Department.name.asc())
    rows = (await db.execute(stmt)).scalars().all()
    return [
        DepartmentOut(
            id=row.id,
            tenant_id=row.tenant_id,
            name=row.name,
            description=row.description,
            parent_id=row.parent_id,
        )
        for row in rows
    ]


@router.patch("/departments/{department_id}", response_model=DepartmentOut)
async def update_department(
    department_id: UUID,
    payload: DepartmentUpdateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> DepartmentOut:
    stmt = select(Department).where(and_(Department.id == department_id, Department.tenant_id == ctx.tenant_id))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    if payload.name is not None:
        name = payload.name.strip()
        exists_stmt = select(Department).where(
            and_(
                Department.tenant_id == ctx.tenant_id,
                func.lower(Department.name) == name.lower(),
                Department.id != row.id,
            )
        )
        if (await db.execute(exists_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Department already exists")
        row.name = name

    if payload.description is not None:
        row.description = payload.description.strip()

    if "parent_id" in payload.model_fields_set and payload.parent_id == row.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department cannot parent itself")
    if "parent_id" in payload.model_fields_set:
        if payload.parent_id:
            parent_stmt = select(Department).where(
                and_(Department.id == payload.parent_id, Department.tenant_id == ctx.tenant_id)
            )
            if not (await db.execute(parent_stmt)).scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent department not found")
            row.parent_id = payload.parent_id
        else:
            row.parent_id = None

    await db.commit()
    await db.refresh(row)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="UPDATE_DEPARTMENT",
        target_type="department",
        target_id=str(row.id),
    )
    return DepartmentOut(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        description=row.description,
        parent_id=row.parent_id,
    )


@router.post("/users/invite", response_model=InviteOut)
async def create_invite(
    payload: InviteCreateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> InviteOut:
    if not _company_email_only(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only company emails are allowed")

    target_role = UserRole(payload.role)
    if not _can_assign_role(ctx.user.role, target_role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role to invite this user role")

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


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    payload: UserUpdateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> UserOut:
    stmt = select(User).where(and_(User.id == user_id, User.tenant_id == ctx.tenant_id))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.role is not None:
        target_role = UserRole(payload.role)
        if not _can_assign_role(ctx.user.role, target_role):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role to assign this role")
        user.role = target_role

    if "department_id" in payload.model_fields_set:
        if payload.department_id is None:
            user.department_id = None
        else:
            dep_stmt = select(Department).where(
                and_(Department.id == payload.department_id, Department.tenant_id == ctx.tenant_id)
            )
            if not (await db.execute(dep_stmt)).scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
            user.department_id = payload.department_id

    if "manager_id" in payload.model_fields_set:
        if payload.manager_id is None:
            user.manager_id = None
        else:
            if payload.manager_id == user.id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User cannot report to self")
            manager_stmt = select(User).where(and_(User.id == payload.manager_id, User.tenant_id == ctx.tenant_id))
            if not (await db.execute(manager_stmt)).scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")
            user.manager_id = payload.manager_id

    if payload.is_active is not None:
        user.is_active = payload.is_active

    if payload.employee_type is not None:
        user.employee_type = EmployeeType(payload.employee_type)

    profile_stmt = select(AgentProfile).where(
        and_(AgentProfile.user_id == user.id, AgentProfile.tenant_id == ctx.tenant_id)
    )
    profile = (await db.execute(profile_stmt)).scalar_one_or_none()
    if user.role == UserRole.AI_AGENT and not profile:
        db.add(
            AgentProfile(
                tenant_id=ctx.tenant_id,
                user_id=user.id,
                tools_allowed=[],
                created_by_user_id=ctx.user.id,
                last_heartbeat_at=None,
            )
        )
    if user.role != UserRole.AI_AGENT and profile:
        await db.delete(profile)

    await db.commit()
    await db.refresh(user)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="UPDATE_USER",
        target_type="user",
        target_id=str(user.id),
    )
    return _to_user_out(user)


@router.patch("/users/{user_id}/manager", response_model=UserOut)
async def update_manager(
    user_id: UUID,
    payload: UserManagerUpdateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> UserOut:
    user_stmt = select(User).where(and_(User.id == user_id, User.tenant_id == ctx.tenant_id))
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.manager_id:
        mgr_stmt = select(User).where(and_(User.id == payload.manager_id, User.tenant_id == ctx.tenant_id))
        manager = (await db.execute(mgr_stmt)).scalar_one_or_none()
        if not manager:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")
        if manager.id == user.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User cannot report to self")

    user.manager_id = payload.manager_id
    await db.commit()
    await db.refresh(user)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="UPDATE_MANAGER",
        target_type="user",
        target_id=str(user.id),
        metadata={"manager_id": str(payload.manager_id) if payload.manager_id else None},
    )
    return _to_user_out(user)


@router.patch("/users/{user_id}/schedule", response_model=UserOut)
async def update_schedule(
    user_id: UUID,
    payload: UserScheduleUpdateIn,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> UserOut:
    if ctx.user.id != user_id and ctx.user.role.value not in {"SUPERADMIN", "ADMIN"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update another user schedule")

    stmt = select(User).where(and_(User.id == user_id, User.tenant_id == ctx.tenant_id))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.work_start_time is not None:
        user.work_start_time = payload.work_start_time
    if payload.work_end_time is not None:
        user.work_end_time = payload.work_end_time
    if payload.break_minutes is not None:
        user.break_minutes = payload.break_minutes
    if payload.lunch_minutes is not None:
        user.lunch_minutes = payload.lunch_minutes
    await db.commit()
    await db.refresh(user)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="UPDATE_SCHEDULE",
        target_type="user",
        target_id=str(user.id),
    )
    return _to_user_out(user)


@router.get("/chart", response_model=list[OrgNodeOut])
async def get_org_chart(ctx=Depends(get_request_context), db: AsyncSession = Depends(get_db_session)) -> list[OrgNodeOut]:
    stmt = select(User).where(and_(User.tenant_id == ctx.tenant_id, User.is_active.is_(True)))
    users = list((await db.execute(stmt.order_by(User.created_at.asc()))).scalars().all())
    by_id = {u.id: u for u in users}
    children: dict[UUID | None, list[User]] = {}
    for user in users:
        children.setdefault(user.manager_id, []).append(user)

    def build_node(user: User) -> OrgNodeOut:
        return OrgNodeOut(
            user_id=user.id,
            full_name=user.full_name,
            role=user.role.value,
            department_id=user.department_id,
            manager_id=user.manager_id,
            children=[build_node(child) for child in children.get(user.id, [])],
        )

    roots = [u for u in users if u.manager_id not in by_id]
    return [build_node(root) for root in roots]
