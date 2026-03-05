from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_context, require_agent_tool
from app.core.security import now_utc
from app.db.models import Task, TaskComment, TaskStatus, User, UserRole
from app.db.session import get_db_session
from app.schemas.tasks import TaskCommentCreateIn, TaskCommentOut, TaskCreateIn, TaskOut, TaskUpdateIn
from app.services.audit import write_audit_log


router = APIRouter(prefix="/tasks", tags=["tasks"])


def _to_out(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        tenant_id=task.tenant_id,
        title=task.title,
        description=task.description,
        status=task.status.value,
        assignee_user_id=task.assignee_user_id,
        created_by_user_id=task.created_by_user_id,
        due_at=task.due_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _comment_out(comment: TaskComment) -> TaskCommentOut:
    return TaskCommentOut(
        id=comment.id,
        tenant_id=comment.tenant_id,
        task_id=comment.task_id,
        author_user_id=comment.author_user_id,
        body=comment.body,
        created_at=comment.created_at,
    )


async def _validate_assignee(db: AsyncSession, tenant_id: str, assignee_user_id: UUID | None) -> None:
    if assignee_user_id is None:
        return
    stmt = select(User).where(and_(User.id == assignee_user_id, User.tenant_id == tenant_id, User.is_active.is_(True)))
    if not (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found")


def _can_manage(task: Task, user_id: UUID, role: UserRole) -> bool:
    if role in {UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.HOD}:
        return True
    return task.created_by_user_id == user_id


def _is_assignee(task: Task, user_id: UUID) -> bool:
    return task.assignee_user_id == user_id


@router.post("", response_model=TaskOut)
async def create_task(
    payload: TaskCreateIn,
    _agent=Depends(require_agent_tool(tool_name="tasks.write")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> TaskOut:
    await _validate_assignee(db, ctx.tenant_id, payload.assignee_user_id)
    task = Task(
        tenant_id=ctx.tenant_id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        status=TaskStatus(payload.status),
        assignee_user_id=payload.assignee_user_id,
        created_by_user_id=ctx.user.id,
        due_at=payload.due_at,
    )
    if task.status == TaskStatus.DONE:
        task.completed_at = now_utc()

    db.add(task)
    await db.commit()
    await db.refresh(task)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_TASK",
        target_type="task",
        target_id=str(task.id),
    )
    return _to_out(task)


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    _agent=Depends(require_agent_tool(tool_name="tasks.read")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(TODO|IN_PROGRESS|DONE|BLOCKED)$"),
    assignee: UUID | None = Query(default=None),
    mine: bool = Query(default=False),
) -> list[TaskOut]:
    stmt = select(Task).where(Task.tenant_id == ctx.tenant_id)
    if status_filter:
        stmt = stmt.where(Task.status == TaskStatus(status_filter))
    if assignee:
        stmt = stmt.where(Task.assignee_user_id == assignee)
    if mine:
        stmt = stmt.where(Task.assignee_user_id == ctx.user.id)

    if ctx.user.role == UserRole.AI_AGENT:
        stmt = stmt.where(Task.assignee_user_id == ctx.user.id)

    rows = (await db.execute(stmt.order_by(Task.created_at.desc()))).scalars().all()
    return [_to_out(row) for row in rows]


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: UUID,
    _agent=Depends(require_agent_tool(tool_name="tasks.read")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> TaskOut:
    stmt = select(Task).where(and_(Task.id == task_id, Task.tenant_id == ctx.tenant_id))
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if ctx.user.role == UserRole.AI_AGENT and task.assignee_user_id != ctx.user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agents can only access own tasks")
    return _to_out(task)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: UUID,
    payload: TaskUpdateIn,
    _agent=Depends(require_agent_tool(tool_name="tasks.write")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> TaskOut:
    stmt = select(Task).where(and_(Task.id == task_id, Task.tenant_id == ctx.tenant_id))
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    can_manage = _can_manage(task, ctx.user.id, ctx.user.role)
    is_assignee = _is_assignee(task, ctx.user.id)
    if not can_manage and not is_assignee:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update task")

    if not can_manage:
        forbidden_fields = {"title", "description", "assignee_user_id", "due_at"}
        attempted = forbidden_fields.intersection(payload.model_fields_set)
        if attempted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Assignee can only update status and add comments",
            )

    if "assignee_user_id" in payload.model_fields_set:
        if not can_manage:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot reassign task")
        await _validate_assignee(db, ctx.tenant_id, payload.assignee_user_id)
        task.assignee_user_id = payload.assignee_user_id
    if payload.title is not None:
        if not can_manage:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change title")
        task.title = payload.title.strip()
    if payload.description is not None:
        if not can_manage:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change description")
        task.description = payload.description.strip()
    if payload.status is not None:
        task.status = TaskStatus(payload.status)
        task.completed_at = now_utc() if task.status == TaskStatus.DONE else None
    if "due_at" in payload.model_fields_set:
        if not can_manage:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot change due date")
        task.due_at = payload.due_at

    await db.commit()
    await db.refresh(task)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="UPDATE_TASK",
        target_type="task",
        target_id=str(task.id),
    )
    return _to_out(task)


@router.delete("/{task_id}")
async def delete_task(
    task_id: UUID,
    _agent=Depends(require_agent_tool(tool_name="tasks.write")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    stmt = select(Task).where(and_(Task.id == task_id, Task.tenant_id == ctx.tenant_id))
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not _can_manage(task, ctx.user.id, ctx.user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete task")
    await db.delete(task)
    await db.commit()
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="DELETE_TASK",
        target_type="task",
        target_id=str(task_id),
    )
    return {"ok": True}


@router.post("/{task_id}/comments", response_model=TaskCommentOut)
async def add_task_comment(
    task_id: UUID,
    payload: TaskCommentCreateIn,
    _agent=Depends(require_agent_tool(tool_name="tasks.write")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> TaskCommentOut:
    stmt = select(Task).where(and_(Task.id == task_id, Task.tenant_id == ctx.tenant_id))
    task = (await db.execute(stmt)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    can_manage = _can_manage(task, ctx.user.id, ctx.user.role)
    is_assignee = _is_assignee(task, ctx.user.id)
    if not can_manage and not is_assignee:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to comment on this task")

    comment = TaskComment(
        tenant_id=ctx.tenant_id,
        task_id=task.id,
        author_user_id=ctx.user.id,
        body=payload.body.strip(),
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="COMMENT_TASK",
        target_type="task",
        target_id=str(task.id),
    )
    return _comment_out(comment)
