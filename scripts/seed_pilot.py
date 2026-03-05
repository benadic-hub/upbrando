from __future__ import annotations

import asyncio
import datetime as dt
import sys
from pathlib import Path

from sqlalchemy import and_, func, select


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings  # noqa: E402
from app.core.email_policy import is_allowed_company_email  # noqa: E402
from app.core.security import now_utc  # noqa: E402
from app.db.models import (  # noqa: E402
    AgentProfile,
    ChatMessage,
    ChatThread,
    ChatThreadParticipant,
    Department,
    EmployeeType,
    Task,
    TaskStatus,
    TimeEntry,
    User,
    UserRole,
)
from app.db.session import SessionLocal  # noqa: E402
from app.services.bootstrap import ensure_root_department, ensure_tenant  # noqa: E402


def _email_domain() -> str:
    if settings.COMPANY_EMAIL_DOMAIN:
        return settings.COMPANY_EMAIL_DOMAIN
    raise RuntimeError("COMPANY_EMAIL_DOMAIN is required for seed_pilot generated users")


async def _get_department(session, tenant_id: str, name: str) -> Department | None:
    stmt = select(Department).where(and_(Department.tenant_id == tenant_id, func.lower(Department.name) == name.lower()))
    return (await session.execute(stmt)).scalar_one_or_none()


async def _get_or_create_department(
    session,
    *,
    tenant_id: str,
    name: str,
    description: str,
    parent_id,
) -> tuple[Department, bool]:
    row = await _get_department(session, tenant_id, name)
    if row:
        if row.description != description:
            row.description = description
        if row.parent_id != parent_id:
            row.parent_id = parent_id
        return row, False
    row = Department(
        tenant_id=tenant_id,
        name=name,
        description=description,
        parent_id=parent_id,
    )
    session.add(row)
    await session.flush()
    return row, True


async def _get_user_by_email(session, tenant_id: str, email: str) -> User | None:
    stmt = select(User).where(and_(User.tenant_id == tenant_id, func.lower(User.email) == email.lower()))
    return (await session.execute(stmt)).scalar_one_or_none()


async def _upsert_user(
    session,
    *,
    tenant_id: str,
    email: str,
    full_name: str,
    role: UserRole,
    department_id,
    employee_type: EmployeeType,
) -> tuple[User, bool]:
    user = await _get_user_by_email(session, tenant_id, email)
    if user:
        user.full_name = full_name
        user.role = role
        user.department_id = department_id
        user.is_active = True
        user.employee_type = employee_type
        return user, False
    user = User(
        tenant_id=tenant_id,
        email=email.lower(),
        full_name=full_name,
        role=role,
        department_id=department_id,
        manager_id=None,
        google_sub=None,
        password_hash=None,
        is_active=True,
        employee_type=employee_type,
    )
    session.add(user)
    await session.flush()
    return user, True


async def _ensure_agent_profile(
    session,
    *,
    tenant_id: str,
    user_id,
    created_by_user_id,
    tools_allowed: list[str],
) -> bool:
    stmt = select(AgentProfile).where(and_(AgentProfile.tenant_id == tenant_id, AgentProfile.user_id == user_id))
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row:
        row.tools_allowed = tools_allowed
        return False
    session.add(
        AgentProfile(
            tenant_id=tenant_id,
            user_id=user_id,
            tools_allowed=tools_allowed,
            created_by_user_id=created_by_user_id,
            last_heartbeat_at=None,
        )
    )
    return True


async def _ensure_task(
    session,
    *,
    tenant_id: str,
    title: str,
    description: str,
    creator_id,
    assignee_id,
) -> bool:
    stmt = select(Task).where(and_(Task.tenant_id == tenant_id, Task.title == title))
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row:
        row.description = description
        row.created_by_user_id = creator_id
        row.assignee_user_id = assignee_id
        if row.status == TaskStatus.DONE:
            row.status = TaskStatus.TODO
            row.completed_at = None
        return False
    session.add(
        Task(
            tenant_id=tenant_id,
            title=title,
            description=description,
            status=TaskStatus.TODO,
            created_by_user_id=creator_id,
            assignee_user_id=assignee_id,
            due_at=None,
            completed_at=None,
        )
    )
    return True


async def _find_dm_thread(session, *, tenant_id: str, user_a, user_b) -> ChatThread | None:
    stmt = select(ChatThread).where(and_(ChatThread.tenant_id == tenant_id, ChatThread.is_dm.is_(True)))
    threads = (await session.execute(stmt)).scalars().all()
    for thread in threads:
        p_stmt = select(ChatThreadParticipant.user_id).where(
            and_(ChatThreadParticipant.tenant_id == tenant_id, ChatThreadParticipant.thread_id == thread.id)
        )
        participants = {row[0] for row in (await session.execute(p_stmt)).all()}
        if participants == {user_a, user_b}:
            return thread
    return None


async def _ensure_dm_thread(session, *, tenant_id: str, creator_id, other_user_id) -> tuple[ChatThread, bool]:
    existing = await _find_dm_thread(session, tenant_id=tenant_id, user_a=creator_id, user_b=other_user_id)
    if existing:
        return existing, False
    thread = ChatThread(
        tenant_id=tenant_id,
        is_dm=True,
        title=None,
        created_by_user_id=creator_id,
    )
    session.add(thread)
    await session.flush()
    joined_at = now_utc()
    session.add(
        ChatThreadParticipant(
            tenant_id=tenant_id,
            thread_id=thread.id,
            user_id=creator_id,
            joined_at=joined_at,
            last_read_at=None,
        )
    )
    session.add(
        ChatThreadParticipant(
            tenant_id=tenant_id,
            thread_id=thread.id,
            user_id=other_user_id,
            joined_at=joined_at,
            last_read_at=None,
        )
    )
    return thread, True


async def _ensure_message(session, *, tenant_id: str, thread_id, sender_id, content: str) -> bool:
    stmt = select(ChatMessage).where(
        and_(
            ChatMessage.tenant_id == tenant_id,
            ChatMessage.thread_id == thread_id,
            ChatMessage.sender_user_id == sender_id,
            ChatMessage.content == content,
        )
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row:
        return False
    session.add(
        ChatMessage(
            tenant_id=tenant_id,
            thread_id=thread_id,
            sender_user_id=sender_id,
            content=content,
        )
    )
    return True


async def _ensure_time_entry(session, *, tenant_id: str, user_id, work_date: dt.date) -> bool:
    stmt = select(TimeEntry).where(
        and_(
            TimeEntry.tenant_id == tenant_id,
            TimeEntry.user_id == user_id,
            TimeEntry.work_date == work_date,
        )
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    check_in = dt.datetime.combine(work_date, dt.time(hour=9, minute=0), tzinfo=dt.timezone.utc)
    check_out = dt.datetime.combine(work_date, dt.time(hour=18, minute=15), tzinfo=dt.timezone.utc)
    if row:
        row.check_in_at = row.check_in_at or check_in
        row.check_out_at = row.check_out_at or check_out
        row.total_worked_minutes = row.total_worked_minutes or 495
        row.break_minutes = row.break_minutes or 15
        row.lunch_minutes = row.lunch_minutes or 60
        row.ot_minutes = row.ot_minutes or 15
        row.source = row.source or "seed_pilot"
        row.notes = row.notes or "Pilot seed entry"
        return False
    session.add(
        TimeEntry(
            tenant_id=tenant_id,
            user_id=user_id,
            work_date=work_date,
            check_in_at=check_in,
            check_out_at=check_out,
            total_worked_minutes=495,
            break_minutes=15,
            lunch_minutes=60,
            ot_minutes=15,
            source="seed_pilot",
            notes="Pilot seed entry",
        )
    )
    return True


async def seed_pilot() -> None:
    tenant_id = settings.DEFAULT_TENANT_ID
    domain = _email_domain()

    async with SessionLocal() as session:
        superadmin_stmt = select(User).where(and_(User.tenant_id == tenant_id, User.role == UserRole.SUPERADMIN))
        superadmin = (await session.execute(superadmin_stmt)).scalars().first()
        if not superadmin:
            raise RuntimeError("SUPERADMIN is required. Run scripts/seed_superadmin.py first.")

        await ensure_tenant(session, tenant_id=tenant_id, tenant_name="Default Tenant")
        root_department = await ensure_root_department(session, tenant_id=tenant_id)

        engineering, dept_eng_created = await _get_or_create_department(
            session,
            tenant_id=tenant_id,
            name="Engineering",
            description="Engineering department",
            parent_id=root_department.id,
        )
        operations, dept_ops_created = await _get_or_create_department(
            session,
            tenant_id=tenant_id,
            name="Operations",
            description="Operations department",
            parent_id=root_department.id,
        )

        pilot_users = [
            {
                "email": f"pilot.admin@{domain}",
                "full_name": "Pilot Admin",
                "role": UserRole.ADMIN,
                "department_id": operations.id,
                "employee_type": EmployeeType.HUMAN,
                "manager_email": superadmin.email,
                "tools_allowed": [],
            },
            {
                "email": f"pilot.hod@{domain}",
                "full_name": "Pilot HOD",
                "role": UserRole.HOD,
                "department_id": engineering.id,
                "employee_type": EmployeeType.HUMAN,
                "manager_email": f"pilot.admin@{domain}",
                "tools_allowed": [],
            },
            {
                "email": f"pilot.employee1@{domain}",
                "full_name": "Pilot Employee One",
                "role": UserRole.EMPLOYEE,
                "department_id": engineering.id,
                "employee_type": EmployeeType.HUMAN,
                "manager_email": f"pilot.hod@{domain}",
                "tools_allowed": [],
            },
            {
                "email": f"pilot.employee2@{domain}",
                "full_name": "Pilot Employee Two",
                "role": UserRole.EMPLOYEE,
                "department_id": operations.id,
                "employee_type": EmployeeType.HUMAN,
                "manager_email": f"pilot.admin@{domain}",
                "tools_allowed": [],
            },
            {
                "email": f"pilot.agent@{domain}",
                "full_name": "Pilot AI Agent",
                "role": UserRole.AI_AGENT,
                "department_id": engineering.id,
                "employee_type": EmployeeType.AGENT,
                "manager_email": f"pilot.hod@{domain}",
                "tools_allowed": ["tasks.read", "tasks.write", "chat.read", "chat.write", "timeclock.read"],
            },
        ]

        user_map: dict[str, User] = {superadmin.email.lower(): superadmin}
        users_created = 0
        profiles_created = 0

        for data in pilot_users:
            if not is_allowed_company_email(data["email"]):
                raise RuntimeError(f"Pilot seed email not allowed by company policy: {data['email']}")
            user, created = await _upsert_user(
                session,
                tenant_id=tenant_id,
                email=data["email"],
                full_name=data["full_name"],
                role=data["role"],
                department_id=data["department_id"],
                employee_type=data["employee_type"],
            )
            users_created += 1 if created else 0
            user_map[user.email.lower()] = user
            if data["role"] == UserRole.AI_AGENT:
                if await _ensure_agent_profile(
                    session,
                    tenant_id=tenant_id,
                    user_id=user.id,
                    created_by_user_id=superadmin.id,
                    tools_allowed=data["tools_allowed"],
                ):
                    profiles_created += 1

        for data in pilot_users:
            user = user_map[data["email"].lower()]
            manager = user_map.get(str(data["manager_email"]).lower())
            if manager and user.manager_id != manager.id:
                user.manager_id = manager.id

        tasks_created = 0
        tasks_created += 1 if await _ensure_task(
            session,
            tenant_id=tenant_id,
            title="Pilot Task: Setup EMS Dashboard",
            description="Create and verify pilot dashboard metrics.",
            creator_id=superadmin.id,
            assignee_id=user_map[f"pilot.admin@{domain}".lower()].id,
        ) else 0
        tasks_created += 1 if await _ensure_task(
            session,
            tenant_id=tenant_id,
            title="Pilot Task: Validate Daily Timeclock",
            description="Validate clock-in and clock-out flow for pilot users.",
            creator_id=superadmin.id,
            assignee_id=user_map[f"pilot.employee1@{domain}".lower()].id,
        ) else 0

        thread, thread_created = await _ensure_dm_thread(
            session,
            tenant_id=tenant_id,
            creator_id=user_map[f"pilot.admin@{domain}".lower()].id,
            other_user_id=user_map[f"pilot.employee1@{domain}".lower()].id,
        )
        messages_created = 0
        messages_created += 1 if await _ensure_message(
            session,
            tenant_id=tenant_id,
            thread_id=thread.id,
            sender_id=user_map[f"pilot.admin@{domain}".lower()].id,
            content="Pilot seed message from admin.",
        ) else 0
        messages_created += 1 if await _ensure_message(
            session,
            tenant_id=tenant_id,
            thread_id=thread.id,
            sender_id=user_map[f"pilot.employee1@{domain}".lower()].id,
            content="Pilot seed reply from employee.",
        ) else 0

        today = now_utc().date()
        entries_created = 0
        entries_created += 1 if await _ensure_time_entry(
            session,
            tenant_id=tenant_id,
            user_id=user_map[f"pilot.employee1@{domain}".lower()].id,
            work_date=today,
        ) else 0
        entries_created += 1 if await _ensure_time_entry(
            session,
            tenant_id=tenant_id,
            user_id=user_map[f"pilot.employee1@{domain}".lower()].id,
            work_date=today - dt.timedelta(days=1),
        ) else 0

        await session.commit()

        print("Pilot seed completed")
        print(
            f"tenant={tenant_id}, "
            f"departments_created={int(dept_eng_created) + int(dept_ops_created)}, "
            f"users_created={users_created}, "
            f"agent_profiles_created={profiles_created}, "
            f"tasks_created={tasks_created}, "
            f"chat_thread_created={int(thread_created)}, "
            f"chat_messages_created={messages_created}, "
            f"time_entries_created={entries_created}"
        )


if __name__ == "__main__":
    asyncio.run(seed_pilot())
