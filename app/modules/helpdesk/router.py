from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_context, require_agent_tool
from app.db.models import HelpdeskTicket, Task, TaskStatus, TicketStatus, User
from app.db.session import get_db_session
from app.schemas.helpdesk import HelpdeskTicketCreateIn, HelpdeskTicketOut, HelpdeskTicketUpdateIn
from app.services.audit import write_audit_log


router = APIRouter(prefix="/helpdesk", tags=["helpdesk"])


def _to_out(ticket: HelpdeskTicket) -> HelpdeskTicketOut:
    return HelpdeskTicketOut(
        id=ticket.id,
        tenant_id=ticket.tenant_id,
        title=ticket.title,
        description=ticket.description,
        status=ticket.status.value,
        requested_by_user_id=ticket.requested_by_user_id,
        assigned_to_user_id=ticket.assigned_to_user_id,
        task_id=ticket.task_id,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


async def _validate_user(db: AsyncSession, tenant_id: str, user_id: UUID | None) -> None:
    if user_id is None:
        return
    stmt = select(User).where(and_(User.id == user_id, User.tenant_id == tenant_id, User.is_active.is_(True)))
    if not (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.post("/tickets", response_model=HelpdeskTicketOut)
async def create_ticket(
    payload: HelpdeskTicketCreateIn,
    _agent=Depends(require_agent_tool(tool_name="helpdesk.write")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> HelpdeskTicketOut:
    await _validate_user(db, ctx.tenant_id, payload.assigned_to_user_id)

    task = Task(
        tenant_id=ctx.tenant_id,
        title=f"[Ticket] {payload.title.strip()}",
        description=payload.description.strip(),
        status=TaskStatus.TODO,
        assignee_user_id=payload.assigned_to_user_id,
        created_by_user_id=ctx.user.id,
    )
    db.add(task)
    await db.flush()

    ticket = HelpdeskTicket(
        tenant_id=ctx.tenant_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        status=TicketStatus.OPEN,
        requested_by_user_id=ctx.user.id,
        assigned_to_user_id=payload.assigned_to_user_id,
        task_id=task.id,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_HELPDESK_TICKET",
        target_type="helpdesk_ticket",
        target_id=str(ticket.id),
        metadata={"task_id": str(task.id)},
    )
    return _to_out(ticket)


@router.get("/tickets", response_model=list[HelpdeskTicketOut])
async def list_tickets(
    status_filter: str | None = Query(default=None, alias="status", pattern="^(OPEN|IN_PROGRESS|RESOLVED|CLOSED)$"),
    _agent=Depends(require_agent_tool(tool_name="helpdesk.read")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[HelpdeskTicketOut]:
    stmt = select(HelpdeskTicket).where(HelpdeskTicket.tenant_id == ctx.tenant_id)
    if status_filter:
        stmt = stmt.where(HelpdeskTicket.status == TicketStatus(status_filter))
    rows = (await db.execute(stmt.order_by(HelpdeskTicket.created_at.desc()))).scalars().all()
    return [_to_out(row) for row in rows]


@router.patch("/tickets/{ticket_id}", response_model=HelpdeskTicketOut)
async def update_ticket(
    ticket_id: UUID,
    payload: HelpdeskTicketUpdateIn,
    _agent=Depends(require_agent_tool(tool_name="helpdesk.write")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> HelpdeskTicketOut:
    stmt = select(HelpdeskTicket).where(and_(HelpdeskTicket.id == ticket_id, HelpdeskTicket.tenant_id == ctx.tenant_id))
    ticket = (await db.execute(stmt)).scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    is_owner = ticket.requested_by_user_id == ctx.user.id
    is_admin = ctx.user.role.value in {"SUPERADMIN", "ADMIN"}
    if not (is_owner or is_admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update ticket")

    if payload.assigned_to_user_id is not None:
        await _validate_user(db, ctx.tenant_id, payload.assigned_to_user_id)
        ticket.assigned_to_user_id = payload.assigned_to_user_id
    if payload.title is not None:
        ticket.title = payload.title.strip()
    if payload.description is not None:
        ticket.description = payload.description.strip()
    if payload.status is not None:
        ticket.status = TicketStatus(payload.status)

    if ticket.task_id:
        task_stmt = select(Task).where(and_(Task.id == ticket.task_id, Task.tenant_id == ctx.tenant_id))
        task = (await db.execute(task_stmt)).scalar_one_or_none()
        if task:
            task.title = f"[Ticket] {ticket.title}"
            task.description = ticket.description
            task.assignee_user_id = ticket.assigned_to_user_id
            if ticket.status in {TicketStatus.RESOLVED, TicketStatus.CLOSED}:
                task.status = TaskStatus.DONE
            elif ticket.status == TicketStatus.IN_PROGRESS:
                task.status = TaskStatus.IN_PROGRESS
            else:
                task.status = TaskStatus.TODO

    await db.commit()
    await db.refresh(ticket)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="UPDATE_HELPDESK_TICKET",
        target_type="helpdesk_ticket",
        target_id=str(ticket.id),
    )
    return _to_out(ticket)
