from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_context
from app.core.config import settings
from app.db.models import Attachment
from app.db.session import get_db_session
from app.schemas.attachments import (
    AttachmentOut,
    AttachmentPresignDownloadOut,
    AttachmentPresignUploadIn,
    AttachmentPresignUploadOut,
)
from app.services.audit import write_audit_log
from app.services.s3 import build_s3_key, presign_download, presign_upload


router = APIRouter(prefix="/attachments", tags=["attachments"])


def _to_out(row: Attachment) -> AttachmentOut:
    return AttachmentOut(
        id=row.id,
        tenant_id=row.tenant_id,
        owner_type=row.owner_type,
        owner_id=row.owner_id,
        filename=row.filename,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        s3_key=row.s3_key,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at,
    )


@router.post("/presign-upload", response_model=AttachmentPresignUploadOut)
async def create_presigned_upload(
    payload: AttachmentPresignUploadIn,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AttachmentPresignUploadOut:
    if payload.size_bytes > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds MAX_UPLOAD_BYTES")
    if payload.content_type.lower() not in settings.allowed_attachment_content_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported content_type")

    attachment_id = uuid.uuid4()
    key = build_s3_key(tenant_id=ctx.tenant_id, attachment_id=attachment_id, filename=payload.filename)
    upload_url = presign_upload(key=key, content_type=payload.content_type)

    row = Attachment(
        id=attachment_id,
        tenant_id=ctx.tenant_id,
        owner_type=payload.owner_type,
        owner_id=payload.owner_id,
        filename=payload.filename,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        s3_key=key,
        created_by_user_id=ctx.user.id,
    )
    db.add(row)
    await db.commit()
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_ATTACHMENT_UPLOAD",
        target_type="attachment",
        target_id=str(row.id),
    )
    return AttachmentPresignUploadOut(attachment_id=attachment_id, s3_key=key, upload_url=upload_url)


@router.get("/{attachment_id}", response_model=AttachmentOut)
async def get_attachment(
    attachment_id: UUID,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AttachmentOut:
    stmt = select(Attachment).where(and_(Attachment.id == attachment_id, Attachment.tenant_id == ctx.tenant_id))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return _to_out(row)


@router.get("/{attachment_id}/presign-download", response_model=AttachmentPresignDownloadOut)
async def create_presigned_download(
    attachment_id: UUID,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> AttachmentPresignDownloadOut:
    stmt = select(Attachment).where(and_(Attachment.id == attachment_id, Attachment.tenant_id == ctx.tenant_id))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    return AttachmentPresignDownloadOut(download_url=presign_download(key=row.s3_key))
