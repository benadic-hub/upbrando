from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_context, require_admin_role
from app.core.email_policy import is_allowed_company_email
from app.core.security import now_utc
from app.db.models import AgentHeartbeat, AgentProfile, Department, User, UserRole
from app.db.session import get_db_session
from app.schemas.agents import (
    AgentCreateIn,
    AgentHeartbeatIn,
    AgentHeartbeatOut,
    AgentOut,
    AgentPermissionCheckIn,
    AgentPermissionCheckOut,
    AgentUpdateIn,
)
from app.services.agents import check_agent_run_permission
from app.services.audit import write_audit_log


router = APIRouter(prefix="/agents", tags=["agents"])


def _valid_company_email(email: str) -> bool:
    return is_allowed_company_email(email)


def _to_agent_out(user: User, profile: AgentProfile) -> AgentOut:
    return AgentOut(
        user_id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        department_id=user.department_id,
        manager_id=user.manager_id,
        tools_allowed=profile.tools_allowed or [],
        last_heartbeat_at=profile.last_heartbeat_at,
        is_active=user.is_active,
    )


@router.post("", response_model=AgentOut)
async def create_agent(
    payload: AgentCreateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AgentOut:
    if not _valid_company_email(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent email must be company domain")

    exists_stmt = select(User).where(and_(User.tenant_id == ctx.tenant_id, func.lower(User.email) == payload.email.lower()))
    if (await db.execute(exists_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    if payload.department_id:
        dep_stmt = select(Department).where(and_(Department.id == payload.department_id, Department.tenant_id == ctx.tenant_id))
        if not (await db.execute(dep_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    if payload.manager_id:
        mgr_stmt = select(User).where(and_(User.id == payload.manager_id, User.tenant_id == ctx.tenant_id))
        if not (await db.execute(mgr_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")

    user = User(
        tenant_id=ctx.tenant_id,
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        role=UserRole.AI_AGENT,
        department_id=payload.department_id,
        manager_id=payload.manager_id,
        google_sub=None,
        password_hash=None,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    profile = AgentProfile(
        tenant_id=ctx.tenant_id,
        user_id=user.id,
        tools_allowed=payload.tools_allowed,
        created_by_user_id=ctx.user.id,
        last_heartbeat_at=None,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(user)
    await db.refresh(profile)

    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_AGENT",
        target_type="user",
        target_id=str(user.id),
        metadata={"tools_allowed": payload.tools_allowed},
    )
    return _to_agent_out(user, profile)


@router.get("", response_model=list[AgentOut])
async def list_agents(
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[AgentOut]:
    users_stmt = select(User).where(and_(User.tenant_id == ctx.tenant_id, User.role == UserRole.AI_AGENT))
    users = list((await db.execute(users_stmt)).scalars().all())
    if not users:
        return []

    profiles_stmt = select(AgentProfile).where(AgentProfile.tenant_id == ctx.tenant_id)
    profiles = {row.user_id: row for row in (await db.execute(profiles_stmt)).scalars().all()}
    return [_to_agent_out(user, profiles[user.id]) for user in users if user.id in profiles]


@router.patch("/{agent_user_id}", response_model=AgentOut)
async def update_agent(
    agent_user_id: UUID,
    payload: AgentUpdateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AgentOut:
    user_stmt = select(User).where(
        and_(User.id == agent_user_id, User.tenant_id == ctx.tenant_id, User.role == UserRole.AI_AGENT)
    )
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    profile_stmt = select(AgentProfile).where(and_(AgentProfile.user_id == user.id, AgentProfile.tenant_id == ctx.tenant_id))
    profile = (await db.execute(profile_stmt)).scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent profile missing")

    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.department_id is not None:
        dep_stmt = select(Department).where(and_(Department.id == payload.department_id, Department.tenant_id == ctx.tenant_id))
        if not (await db.execute(dep_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        user.department_id = payload.department_id
    if payload.manager_id is not None:
        mgr_stmt = select(User).where(and_(User.id == payload.manager_id, User.tenant_id == ctx.tenant_id))
        if not (await db.execute(mgr_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")
        user.manager_id = payload.manager_id
    if payload.tools_allowed is not None:
        profile.tools_allowed = payload.tools_allowed
    if payload.is_active is not None:
        user.is_active = payload.is_active

    await db.commit()
    await db.refresh(user)
    await db.refresh(profile)

    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="UPDATE_AGENT",
        target_type="user",
        target_id=str(user.id),
    )
    return _to_agent_out(user, profile)


@router.post("/heartbeat", response_model=AgentHeartbeatOut)
async def heartbeat(
    payload: AgentHeartbeatIn,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AgentHeartbeatOut:
    if ctx.user.role != UserRole.AI_AGENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only AI agents can send heartbeat")
    if not ctx.agent_profile:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent profile missing")

    beat = AgentHeartbeat(
        tenant_id=ctx.tenant_id,
        agent_user_id=ctx.user.id,
        activity=payload.activity.strip(),
    )
    db.add(beat)
    ctx.agent_profile.last_heartbeat_at = now_utc()
    await db.commit()
    await db.refresh(beat)
    return AgentHeartbeatOut(
        id=beat.id,
        agent_user_id=beat.agent_user_id,
        activity=beat.activity,
        created_at=beat.created_at,
    )


@router.get("/{agent_user_id}/heartbeats", response_model=list[AgentHeartbeatOut])
async def list_heartbeats(
    agent_user_id: UUID,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 100,
) -> list[AgentHeartbeatOut]:
    stmt = (
        select(AgentHeartbeat)
        .where(and_(AgentHeartbeat.tenant_id == ctx.tenant_id, AgentHeartbeat.agent_user_id == agent_user_id))
        .order_by(AgentHeartbeat.created_at.desc())
        .limit(min(max(limit, 1), 500))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        AgentHeartbeatOut(
            id=row.id,
            agent_user_id=row.agent_user_id,
            activity=row.activity,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/permission-check", response_model=AgentPermissionCheckOut)
async def permission_check(payload: AgentPermissionCheckIn, ctx=Depends(get_request_context)) -> AgentPermissionCheckOut:
    allowed, reason = check_agent_run_permission(
        user=ctx.user,
        agent_profile=ctx.agent_profile,
        tool_name=payload.tool_name,
        department_id=str(payload.department_id) if payload.department_id else None,
    )
    return AgentPermissionCheckOut(allowed=allowed, reason=reason)
