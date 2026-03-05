from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.rate_limit import InMemoryRateLimiter, RateLimiter
from app.core.security import TokenType, decode_token
from app.core.tenancy import enforce_admin_ip_allowlist, get_tenant_id
from app.db.models import AgentProfile, User, UserRole
from app.db.session import get_db_session


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/google/login", auto_error=False)

_rate_limiter = RateLimiter(InMemoryRateLimiter())

auth_rate_limit_dependency = _rate_limiter.dependency(
    scope="auth",
    limit=settings.RATE_LIMIT_AUTH_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)
chat_rate_limit_dependency = _rate_limiter.dependency(
    scope="chat",
    limit=settings.RATE_LIMIT_CHAT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


@dataclass(slots=True)
class RequestContext:
    user: User
    tenant_id: str
    agent_profile: AgentProfile | None = None


def get_access_token(request: Request, bearer_token: str | None = Depends(oauth2_scheme)) -> str:
    cookie_token = request.cookies.get(settings.AUTH_ACCESS_COOKIE_NAME)
    if cookie_token:
        return cookie_token
    if bearer_token and settings.is_dev:
        return bearer_token
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def get_request_context(
    token: str = Depends(get_access_token),
    tenant_id: str = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db_session),
) -> RequestContext:
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if payload.token_type != TokenType.ACCESS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token required")

    if payload.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token tenant mismatch")

    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject") from exc

    user_stmt = select(User).where(and_(User.id == user_id, User.tenant_id == tenant_id))
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    if user.role.value != payload.role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Role claim mismatch")

    agent_profile = None
    if user.role == UserRole.AI_AGENT:
        profile_stmt = select(AgentProfile).where(
            and_(AgentProfile.user_id == user.id, AgentProfile.tenant_id == tenant_id)
        )
        agent_profile = (await db.execute(profile_stmt)).scalar_one_or_none()

    return RequestContext(user=user, tenant_id=tenant_id, agent_profile=agent_profile)


def require_roles(*roles: UserRole) -> Callable[[RequestContext], RequestContext]:
    allowed = {role.value for role in roles}

    def _dependency(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        if ctx.user.role.value not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return ctx

    return _dependency


def require_admin_role(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
    if ctx.user.role not in {UserRole.SUPERADMIN, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return ctx


def require_manager_role(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
    if ctx.user.role not in {UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.HOD}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager role required")
    return ctx


def require_admin_ip(request: Request) -> None:
    enforce_admin_ip_allowlist(request)


def require_agent_tool(*, tool_name: str, department_id: uuid.UUID | None = None):
    def _dependency(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        if ctx.user.role != UserRole.AI_AGENT:
            return ctx
        if not ctx.agent_profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing agent profile")
        tools = set(ctx.agent_profile.tools_allowed or [])
        if tool_name not in tools:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tool not allowed for this agent")
        if department_id and ctx.user.department_id != department_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent department mismatch")
        return ctx

    return _dependency
