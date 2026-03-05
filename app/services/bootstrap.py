from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.email_policy import is_allowed_company_email
from app.core.security import hash_password
from app.db.models import Department, Tenant, User, UserRole


ROOT_DEPARTMENT_NAME = "ROOT"


@dataclass(slots=True)
class BootstrapStatus:
    tenant_exists: bool
    root_department_exists: bool
    superadmin_exists: bool
    total_users: int


async def ensure_tenant(session: AsyncSession, *, tenant_id: str, tenant_name: str | None = None) -> Tenant:
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    tenant = (await session.execute(stmt)).scalar_one_or_none()
    if tenant:
        return tenant
    tenant = Tenant(id=tenant_id, name=tenant_name or tenant_id)
    session.add(tenant)
    await session.flush()
    return tenant


async def ensure_root_department(session: AsyncSession, *, tenant_id: str) -> Department:
    stmt = select(Department).where(
        and_(
            Department.tenant_id == tenant_id,
            func.lower(Department.name) == ROOT_DEPARTMENT_NAME.lower(),
            Department.parent_id.is_(None),
        )
    )
    department = (await session.execute(stmt)).scalar_one_or_none()
    if department:
        return department
    department = Department(
        tenant_id=tenant_id,
        name=ROOT_DEPARTMENT_NAME,
        description="Root department",
        parent_id=None,
    )
    session.add(department)
    await session.flush()
    return department


async def seed_superadmin_from_settings(session: AsyncSession) -> tuple[bool, User | None]:
    if not settings.SUPERADMIN_EMAIL:
        raise RuntimeError("SUPERADMIN_EMAIL is required")

    email = settings.SUPERADMIN_EMAIL.strip().lower()
    if not is_allowed_company_email(email):
        raise RuntimeError("SUPERADMIN_EMAIL must satisfy company email policy")

    await ensure_tenant(session, tenant_id=settings.DEFAULT_TENANT_ID, tenant_name="Default Tenant")
    root_department = await ensure_root_department(session, tenant_id=settings.DEFAULT_TENANT_ID)

    stmt = select(User).where(
        and_(
            User.tenant_id == settings.DEFAULT_TENANT_ID,
            func.lower(User.email) == email,
        )
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing:
        if existing.role != UserRole.SUPERADMIN:
            existing.role = UserRole.SUPERADMIN
        if not existing.department_id:
            existing.department_id = root_department.id
        await session.commit()
        await session.refresh(existing)
        return False, existing

    password_hash = hash_password(settings.SUPERADMIN_PASSWORD) if settings.SUPERADMIN_PASSWORD else None
    user = User(
        tenant_id=settings.DEFAULT_TENANT_ID,
        email=email,
        full_name="Super Admin",
        role=UserRole.SUPERADMIN,
        password_hash=password_hash,
        google_sub=None,
        is_active=True,
        department_id=root_department.id,
        manager_id=None,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return True, user


async def get_bootstrap_status(session: AsyncSession) -> BootstrapStatus:
    tenant_stmt = select(Tenant).where(Tenant.id == settings.DEFAULT_TENANT_ID)
    tenant = (await session.execute(tenant_stmt)).scalar_one_or_none()

    root_stmt = select(Department).where(
        and_(
            Department.tenant_id == settings.DEFAULT_TENANT_ID,
            func.lower(Department.name) == ROOT_DEPARTMENT_NAME.lower(),
            Department.parent_id.is_(None),
        )
    )
    root = (await session.execute(root_stmt)).scalar_one_or_none()

    sa_stmt = select(User).where(
        and_(
            User.tenant_id == settings.DEFAULT_TENANT_ID,
            User.role == UserRole.SUPERADMIN,
        )
    )
    sa = (await session.execute(sa_stmt)).scalars().first()

    total_users = int((await session.execute(select(func.count()).select_from(User))).scalar_one())
    return BootstrapStatus(
        tenant_exists=tenant is not None,
        root_department_exists=root is not None,
        superadmin_exists=sa is not None,
        total_users=total_users,
    )
