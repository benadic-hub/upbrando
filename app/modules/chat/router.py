from __future__ import annotations

import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import chat_rate_limit_dependency, get_request_context, require_agent_tool
from app.core.security import now_utc
from app.db.models import ChatMessage, ChatThread, ChatThreadParticipant, User
from app.db.session import get_db_session
from app.schemas.chat import (
    ChatMessageCreateIn,
    ChatMessageOut,
    ChatThreadCreateIn,
    ChatThreadOut,
    DmThreadCreateIn,
    MarkReadIn,
    UnreadCounterOut,
)
from app.services.audit import write_audit_log


router = APIRouter(
    prefix="/chat",
    tags=["chat"],
    dependencies=[Depends(chat_rate_limit_dependency)],
)


def _thread_out(thread: ChatThread, participant_ids: list[UUID], unread_count: int) -> ChatThreadOut:
    return ChatThreadOut(
        id=thread.id,
        tenant_id=thread.tenant_id,
        is_dm=thread.is_dm,
        title=thread.title,
        created_by_user_id=thread.created_by_user_id,
        created_at=thread.created_at,
        unread_count=unread_count,
        participant_ids=participant_ids,
    )


def _msg_out(message: ChatMessage) -> ChatMessageOut:
    return ChatMessageOut(
        id=message.id,
        tenant_id=message.tenant_id,
        thread_id=message.thread_id,
        sender_user_id=message.sender_user_id,
        content=message.content,
        created_at=message.created_at,
    )


async def _ensure_user(db: AsyncSession, tenant_id: str, user_id: UUID) -> User:
    stmt = select(User).where(and_(User.id == user_id, User.tenant_id == tenant_id, User.is_active.is_(True)))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def _is_participant(db: AsyncSession, tenant_id: str, thread_id: UUID, user_id: UUID) -> bool:
    stmt = select(ChatThreadParticipant).where(
        and_(
            ChatThreadParticipant.tenant_id == tenant_id,
            ChatThreadParticipant.thread_id == thread_id,
            ChatThreadParticipant.user_id == user_id,
        )
    )
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def _find_dm_thread(db: AsyncSession, tenant_id: str, user_a: UUID, user_b: UUID) -> ChatThread | None:
    stmt = select(ChatThread).where(and_(ChatThread.tenant_id == tenant_id, ChatThread.is_dm.is_(True)))
    threads = (await db.execute(stmt)).scalars().all()
    for thread in threads:
        p_stmt = select(ChatThreadParticipant.user_id).where(
            and_(
                ChatThreadParticipant.tenant_id == tenant_id,
                ChatThreadParticipant.thread_id == thread.id,
            )
        )
        participants = {row[0] for row in (await db.execute(p_stmt)).all()}
        if participants == {user_a, user_b}:
            return thread
    return None


@router.post(
    "/threads/dm",
    response_model=ChatThreadOut,
    dependencies=[Depends(chat_rate_limit_dependency)],
)
async def create_dm_thread(
    payload: DmThreadCreateIn,
    _agent=Depends(require_agent_tool(tool_name="chat.write")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ChatThreadOut:
    if payload.other_user_id == ctx.user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create DM with yourself")
    await _ensure_user(db, ctx.tenant_id, payload.other_user_id)

    existing = await _find_dm_thread(db, ctx.tenant_id, ctx.user.id, payload.other_user_id)
    if existing:
        return _thread_out(existing, [ctx.user.id, payload.other_user_id], unread_count=0)

    thread = ChatThread(
        tenant_id=ctx.tenant_id,
        is_dm=True,
        created_by_user_id=ctx.user.id,
    )
    db.add(thread)
    await db.flush()
    for uid in (ctx.user.id, payload.other_user_id):
        db.add(
            ChatThreadParticipant(
                tenant_id=ctx.tenant_id,
                thread_id=thread.id,
                user_id=uid,
                joined_at=now_utc(),
                last_read_at=None,
            )
        )
    await db.commit()
    await db.refresh(thread)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_DM_THREAD",
        target_type="chat_thread",
        target_id=str(thread.id),
    )
    return _thread_out(thread, [ctx.user.id, payload.other_user_id], unread_count=0)


@router.post(
    "/threads",
    response_model=ChatThreadOut,
    dependencies=[Depends(chat_rate_limit_dependency)],
)
async def create_thread(
    payload: ChatThreadCreateIn,
    _agent=Depends(require_agent_tool(tool_name="chat.write")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ChatThreadOut:
    if payload.is_group:
        participant_ids = set(payload.member_ids)
        participant_ids.add(ctx.user.id)
        if len(participant_ids) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group thread requires at least one other member")
        for uid in participant_ids:
            await _ensure_user(db, ctx.tenant_id, uid)

        thread = ChatThread(
            tenant_id=ctx.tenant_id,
            is_dm=False,
            title=(payload.title or "").strip() or None,
            created_by_user_id=ctx.user.id,
        )
        db.add(thread)
        await db.flush()
        for uid in participant_ids:
            db.add(
                ChatThreadParticipant(
                    tenant_id=ctx.tenant_id,
                    thread_id=thread.id,
                    user_id=uid,
                    joined_at=now_utc(),
                    last_read_at=None,
                )
            )
        await db.commit()
        await db.refresh(thread)
        return _thread_out(thread, list(participant_ids), unread_count=0)

    if payload.user_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id is required for DM thread")
    if payload.user_id == ctx.user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create DM with yourself")
    await _ensure_user(db, ctx.tenant_id, payload.user_id)

    existing = await _find_dm_thread(db, ctx.tenant_id, ctx.user.id, payload.user_id)
    if existing:
        return _thread_out(existing, [ctx.user.id, payload.user_id], unread_count=0)

    thread = ChatThread(
        tenant_id=ctx.tenant_id,
        is_dm=True,
        title=None,
        created_by_user_id=ctx.user.id,
    )
    db.add(thread)
    await db.flush()
    for uid in (ctx.user.id, payload.user_id):
        db.add(
            ChatThreadParticipant(
                tenant_id=ctx.tenant_id,
                thread_id=thread.id,
                user_id=uid,
                joined_at=now_utc(),
                last_read_at=None,
            )
        )
    await db.commit()
    await db.refresh(thread)
    return _thread_out(thread, [ctx.user.id, payload.user_id], unread_count=0)


@router.get("/threads", response_model=list[ChatThreadOut])
async def list_threads(
    _agent=Depends(require_agent_tool(tool_name="chat.read")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[ChatThreadOut]:
    participant_stmt = select(ChatThreadParticipant.thread_id, ChatThreadParticipant.last_read_at).where(
        and_(ChatThreadParticipant.tenant_id == ctx.tenant_id, ChatThreadParticipant.user_id == ctx.user.id)
    )
    participant_rows = (await db.execute(participant_stmt)).all()
    if not participant_rows:
        return []

    out: list[ChatThreadOut] = []
    for thread_id, last_read_at in participant_rows:
        thread_stmt = select(ChatThread).where(and_(ChatThread.id == thread_id, ChatThread.tenant_id == ctx.tenant_id))
        thread = (await db.execute(thread_stmt)).scalar_one_or_none()
        if not thread:
            continue
        ids_stmt = select(ChatThreadParticipant.user_id).where(
            and_(ChatThreadParticipant.tenant_id == ctx.tenant_id, ChatThreadParticipant.thread_id == thread.id)
        )
        participant_ids = [row[0] for row in (await db.execute(ids_stmt)).all()]
        unread_stmt = select(func.count()).select_from(ChatMessage).where(
            and_(
                ChatMessage.tenant_id == ctx.tenant_id,
                ChatMessage.thread_id == thread.id,
                ChatMessage.sender_user_id != ctx.user.id,
                ChatMessage.created_at > (last_read_at or dt_from_epoch()),
            )
        )
        unread_count = (await db.execute(unread_stmt)).scalar_one()
        out.append(_thread_out(thread, participant_ids, unread_count))
    return out


def dt_from_epoch():
    return dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


@router.get("/threads/{thread_id}/messages", response_model=list[ChatMessageOut])
async def list_messages(
    thread_id: UUID,
    _agent=Depends(require_agent_tool(tool_name="chat.read")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
    limit: int = 100,
    before: UUID | None = None,
) -> list[ChatMessageOut]:
    if not await _is_participant(db, ctx.tenant_id, thread_id, ctx.user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this thread")

    where_clause = and_(ChatMessage.tenant_id == ctx.tenant_id, ChatMessage.thread_id == thread_id)
    if before is not None:
        ref_stmt = select(ChatMessage).where(
            and_(ChatMessage.id == before, ChatMessage.tenant_id == ctx.tenant_id, ChatMessage.thread_id == thread_id)
        )
        ref = (await db.execute(ref_stmt)).scalar_one_or_none()
        if not ref:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference message not found")
        where_clause = and_(where_clause, ChatMessage.created_at < ref.created_at)

    stmt = select(ChatMessage).where(where_clause).order_by(ChatMessage.created_at.desc()).limit(min(max(limit, 1), 500))
    rows = list((await db.execute(stmt)).scalars().all())
    rows.reverse()
    return [_msg_out(row) for row in rows]


@router.post(
    "/threads/{thread_id}/messages",
    response_model=ChatMessageOut,
    dependencies=[Depends(chat_rate_limit_dependency)],
)
async def send_message(
    thread_id: UUID,
    payload: ChatMessageCreateIn,
    _agent=Depends(require_agent_tool(tool_name="chat.write")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> ChatMessageOut:
    if not await _is_participant(db, ctx.tenant_id, thread_id, ctx.user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this thread")

    message = ChatMessage(
        tenant_id=ctx.tenant_id,
        thread_id=thread_id,
        sender_user_id=ctx.user.id,
        content=payload.content.strip(),
    )
    db.add(message)

    participant_stmt = select(ChatThreadParticipant).where(
        and_(
            ChatThreadParticipant.tenant_id == ctx.tenant_id,
            ChatThreadParticipant.thread_id == thread_id,
            ChatThreadParticipant.user_id == ctx.user.id,
        )
    )
    me_participant = (await db.execute(participant_stmt)).scalar_one()
    me_participant.last_read_at = now_utc()
    await db.commit()
    await db.refresh(message)
    return _msg_out(message)


@router.post("/threads/{thread_id}/read")
async def mark_read(
    thread_id: UUID,
    payload: MarkReadIn,
    _agent=Depends(require_agent_tool(tool_name="chat.read")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    stmt = select(ChatThreadParticipant).where(
        and_(
            ChatThreadParticipant.tenant_id == ctx.tenant_id,
            ChatThreadParticipant.thread_id == thread_id,
            ChatThreadParticipant.user_id == ctx.user.id,
        )
    )
    participant = (await db.execute(stmt)).scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this thread")

    if payload.up_to_message_id:
        msg_stmt = select(ChatMessage).where(
            and_(
                ChatMessage.id == payload.up_to_message_id,
                ChatMessage.thread_id == thread_id,
                ChatMessage.tenant_id == ctx.tenant_id,
            )
        )
        message = (await db.execute(msg_stmt)).scalar_one_or_none()
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        participant.last_read_at = message.created_at
    else:
        participant.last_read_at = now_utc()

    await db.commit()
    return {"ok": True}


@router.get("/unread", response_model=UnreadCounterOut)
async def unread_counters(
    _agent=Depends(require_agent_tool(tool_name="chat.read")),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> UnreadCounterOut:
    stmt = select(ChatThreadParticipant).where(
        and_(ChatThreadParticipant.tenant_id == ctx.tenant_id, ChatThreadParticipant.user_id == ctx.user.id)
    )
    participants = (await db.execute(stmt)).scalars().all()
    per_thread: dict[UUID, int] = {}
    total = 0
    epoch = dt_from_epoch()
    for participant in participants:
        unread_stmt = select(func.count()).select_from(ChatMessage).where(
            and_(
                ChatMessage.tenant_id == ctx.tenant_id,
                ChatMessage.thread_id == participant.thread_id,
                ChatMessage.sender_user_id != ctx.user.id,
                ChatMessage.created_at > (participant.last_read_at or epoch),
            )
        )
        count = int((await db.execute(unread_stmt)).scalar_one())
        per_thread[participant.thread_id] = count
        total += count
    return UnreadCounterOut(total_unread=total, per_thread=per_thread)
