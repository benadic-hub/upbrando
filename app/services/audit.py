from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.db.models import AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    tenant_id: str,
    actor_user_id: uuid.UUID | None,
    action: str,
    target_type: str = "",
    target_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    record = AuditLog(
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=metadata or {},
        created_at=now_utc(),
    )
    db.add(record)
    await db.commit()

