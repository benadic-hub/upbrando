from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import auth_rate_limit_dependency, get_request_context
from app.core.config import settings
from app.core.email_policy import is_allowed_company_email
from app.core.security import (
    TokenType,
    build_token,
    decode_token,
    hash_password,
    hash_token,
    now_utc,
)
from app.core.tenancy import enforce_admin_ip_allowlist
from app.db.models import AgentProfile, Invite, RefreshToken, User, UserRole
from app.db.session import get_db_session
from app.schemas.auth import (
    BootstrapSuperadminIn,
    DevLoginIn,
    GoogleLoginIn,
    LogoutOut,
    MeEnvelopeOut,
    MeOut,
    SessionAuthOut,
)
from app.services.google_oauth import verify_google_identity


router = APIRouter(tags=["auth"])


@dataclass(slots=True)
class IssuedSession:
    access_token: str
    refresh_token: str
    expires_in: int
    me: MeOut


def _role_permissions(role: UserRole) -> list[str]:
    if role == UserRole.SUPERADMIN:
        return ["*"]
    if role == UserRole.ADMIN:
        return [
            "org.manage",
            "users.manage",
            "tasks.manage",
            "timeclock.manage",
            "chat.manage",
            "announcements.manage",
        ]
    if role == UserRole.HOD:
        return [
            "org.view",
            "tasks.manage",
            "timeclock.manage",
            "chat.manage",
        ]
    if role == UserRole.AI_AGENT:
        return ["tasks.read", "tasks.write", "chat.read", "chat.write", "timeclock.read"]
    return ["tasks.read", "chat.read", "timeclock.read"]


def _to_me_out(user: User) -> MeOut:
    return MeOut(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        employee_type=user.employee_type.value,
        permissions=_role_permissions(user.role),
        department_id=user.department_id,
        manager_id=user.manager_id,
        is_active=user.is_active,
        created_at=user.created_at,
    )


def _cookie_base_params() -> dict[str, object]:
    params: dict[str, object] = {
        "httponly": True,
        "secure": settings.auth_cookie_secure,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "path": "/",
    }
    if settings.AUTH_COOKIE_DOMAIN:
        params["domain"] = settings.AUTH_COOKIE_DOMAIN
    return params


def _set_auth_cookies(response: Response, *, access_token: str, refresh_token: str) -> None:
    base = _cookie_base_params()
    access_max_age = settings.ACCESS_TOKEN_MINUTES * 60
    refresh_max_age = settings.REFRESH_TOKEN_DAYS * 24 * 60 * 60
    response.set_cookie(
        key=settings.AUTH_ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=access_max_age,
        expires=access_max_age,
        **base,
    )
    response.set_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=refresh_max_age,
        expires=refresh_max_age,
        **base,
    )


def _clear_auth_cookies(response: Response) -> None:
    base = _cookie_base_params()
    response.set_cookie(
        key=settings.AUTH_ACCESS_COOKIE_NAME,
        value="",
        max_age=0,
        expires=0,
        **base,
    )
    response.set_cookie(
        key=settings.AUTH_REFRESH_COOKIE_NAME,
        value="",
        max_age=0,
        expires=0,
        **base,
    )


def _extract_bearer_token(request: Request) -> str | None:
    if not settings.is_dev:
        return None
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    value = auth_header[7:].strip()
    return value or None


def _extract_refresh_token(request: Request) -> str | None:
    cookie_value = request.cookies.get(settings.AUTH_REFRESH_COOKIE_NAME)
    if cookie_value:
        return cookie_value
    return _extract_bearer_token(request)


async def _issue_token_pair(db: AsyncSession, user: User) -> IssuedSession:
    access_token, _ = build_token(
        sub=str(user.id),
        role=user.role.value,
        tenant_id=user.tenant_id,
        token_type=TokenType.ACCESS,
    )
    refresh_token, _ = build_token(
        sub=str(user.id),
        role=user.role.value,
        tenant_id=user.tenant_id,
        token_type=TokenType.REFRESH,
    )
    refresh_payload = decode_token(refresh_token)
    access_payload = decode_token(access_token)
    expires_at = dt.datetime.fromtimestamp(refresh_payload.exp, tz=dt.timezone.utc)
    db.add(
        RefreshToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=expires_at,
            revoked_at=None,
        )
    )
    await db.commit()
    expires_in = max(0, int(access_payload.exp - int(now_utc().timestamp())))
    return IssuedSession(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        me=_to_me_out(user),
    )


@router.post(
    "/auth/google/login",
    response_model=SessionAuthOut,
    dependencies=[Depends(auth_rate_limit_dependency)],
)
async def google_login(
    payload: GoogleLoginIn,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> SessionAuthOut:
    try:
        identity = verify_google_identity(payload.id_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid Google token: {exc}") from exc
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

    if not identity.email_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google email is not verified")
    if not is_allowed_company_email(identity.email):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google account email is not allowed")

    tenant_id = settings.DEFAULT_TENANT_ID
    user_stmt = select(User).where(
        and_(User.tenant_id == tenant_id, func.lower(User.email) == identity.email.lower())
    )
    user = (await db.execute(user_stmt)).scalar_one_or_none()

    if user is None:
        invite = None
        invite_stmt = (
            select(Invite)
            .where(
                and_(
                    Invite.tenant_id == tenant_id,
                    func.lower(Invite.email) == identity.email.lower(),
                    Invite.accepted_at.is_(None),
                    Invite.expires_at >= now_utc(),
                )
            )
            .order_by(Invite.created_at.desc())
        )
        invite = (await db.execute(invite_stmt)).scalars().first()

        if settings.SUPERADMIN_EMAIL and identity.email.lower() == settings.SUPERADMIN_EMAIL.lower():
            role = UserRole.SUPERADMIN
        else:
            if not invite:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invite required for onboarding")
            role = invite.role

        user = User(
            tenant_id=tenant_id,
            email=identity.email.lower(),
            full_name=(invite.full_name if invite else "") or identity.name or identity.email.split("@")[0],
            role=role,
            google_sub=identity.sub,
            password_hash=None,
            department_id=invite.department_id if invite else None,
            manager_id=invite.manager_id if invite else None,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        if role == UserRole.AI_AGENT:
            db.add(
                AgentProfile(
                    tenant_id=tenant_id,
                    user_id=user.id,
                    tools_allowed=(invite.tools_allowed if invite else None) or [],
                    created_by_user_id=invite.invited_by_user_id if invite else None,
                    last_heartbeat_at=None,
                )
            )

        if invite:
            invite.accepted_at = now_utc()
            invite.accepted_user_id = user.id
        await db.commit()
        await db.refresh(user)
    else:
        if user.google_sub and user.google_sub != identity.sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Google identity mismatch")
        if not user.google_sub:
            user.google_sub = identity.sub
            await db.commit()

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    issued = await _issue_token_pair(db, user)
    _set_auth_cookies(response, access_token=issued.access_token, refresh_token=issued.refresh_token)
    return SessionAuthOut(expires_in=issued.expires_in, me=issued.me)


@router.post(
    "/auth/refresh",
    response_model=SessionAuthOut,
    dependencies=[Depends(auth_rate_limit_dependency)],
)
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> SessionAuthOut:
    refresh_token_value = _extract_refresh_token(request)
    if not refresh_token_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")

    try:
        token_payload = decode_token(refresh_token_value)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if token_payload.token_type != TokenType.REFRESH:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token required")

    token_hash_value = hash_token(refresh_token_value)
    refresh_stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash_value)
    refresh_record = (await db.execute(refresh_stmt)).scalar_one_or_none()
    if not refresh_record or refresh_record.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")

    if refresh_record.expires_at < now_utc():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user_stmt = select(User).where(
        and_(User.id == refresh_record.user_id, User.tenant_id == refresh_record.tenant_id)
    )
    user = (await db.execute(user_stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

    refresh_record.revoked_at = now_utc()
    await db.commit()
    issued = await _issue_token_pair(db, user)
    _set_auth_cookies(response, access_token=issued.access_token, refresh_token=issued.refresh_token)
    return SessionAuthOut(expires_in=issued.expires_in, me=issued.me)


@router.post("/auth/logout", response_model=LogoutOut, dependencies=[Depends(auth_rate_limit_dependency)])
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> LogoutOut:
    refresh_token_value = _extract_refresh_token(request)
    if refresh_token_value:
        token_hash_value = hash_token(refresh_token_value)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash_value)
        token = (await db.execute(stmt)).scalar_one_or_none()
        if token and token.revoked_at is None:
            token.revoked_at = now_utc()
            await db.commit()
    _clear_auth_cookies(response)
    return LogoutOut(ok=True)


@router.get("/auth/me", response_model=MeEnvelopeOut)
async def me(ctx=Depends(get_request_context)) -> MeEnvelopeOut:
    return MeEnvelopeOut(me=_to_me_out(ctx.user))


@router.get("/me", response_model=MeOut)
async def me_alias(ctx=Depends(get_request_context)) -> MeOut:
    return _to_me_out(ctx.user)


@router.post("/auth/dev/login", response_model=SessionAuthOut, dependencies=[Depends(auth_rate_limit_dependency)])
@router.post("/auth/dev-login", response_model=SessionAuthOut, dependencies=[Depends(auth_rate_limit_dependency)])
async def dev_login(
    payload: DevLoginIn,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> SessionAuthOut:
    if settings.ENV != "dev":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not settings.DEV_AUTH_BYPASS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not is_allowed_company_email(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only company emails are allowed")

    tenant_id = settings.DEFAULT_TENANT_ID
    email = payload.email.lower().strip()
    stmt = select(User).where(and_(User.tenant_id == tenant_id, func.lower(User.email) == email))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        role = (
            UserRole.SUPERADMIN
            if settings.SUPERADMIN_EMAIL and email == settings.SUPERADMIN_EMAIL.lower()
            else UserRole.EMPLOYEE
        )
        user = User(
            tenant_id=tenant_id,
            email=email,
            full_name=(payload.full_name or email.split("@")[0]).strip(),
            role=role,
            google_sub=None,
            password_hash=None,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")

    issued = await _issue_token_pair(db, user)
    _set_auth_cookies(response, access_token=issued.access_token, refresh_token=issued.refresh_token)
    return SessionAuthOut(expires_in=issued.expires_in, me=issued.me)


@router.post(
    "/bootstrap/superadmin",
    dependencies=[Depends(auth_rate_limit_dependency)],
)
async def bootstrap_superadmin(
    payload: BootstrapSuperadminIn,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    enforce_admin_ip_allowlist(request)

    total_users = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    if total_users > 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bootstrap already disabled")

    if not settings.SUPERADMIN_EMAIL or not settings.SUPERADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SUPERADMIN_EMAIL and SUPERADMIN_PASSWORD must be configured",
        )

    if payload.email.lower() != settings.SUPERADMIN_EMAIL.lower():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bootstrap credentials")
    if payload.password != settings.SUPERADMIN_PASSWORD:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bootstrap credentials")

    if not is_allowed_company_email(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Superadmin email must be company email")

    user = User(
        tenant_id=settings.DEFAULT_TENANT_ID,
        email=payload.email.lower(),
        full_name=payload.full_name,
        role=UserRole.SUPERADMIN,
        password_hash=hash_password(payload.password),
        google_sub=None,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    return {"status": "created"}
