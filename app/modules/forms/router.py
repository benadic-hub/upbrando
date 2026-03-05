from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_context, require_admin_role
from app.core.security import decrypt_json, encrypt_json
from app.db.models import FormSubmission, FormTemplate
from app.db.session import get_db_session
from app.schemas.forms import (
    FormSubmissionCreateIn,
    FormSubmissionOut,
    FormTemplateCreateIn,
    FormTemplateOut,
    FormTemplateUpdateIn,
)
from app.services.audit import write_audit_log


router = APIRouter(prefix="/forms", tags=["forms"])


def _template_out(row: FormTemplate) -> FormTemplateOut:
    return FormTemplateOut(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        description=row.description,
        fields_schema=row.fields_schema or [],
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _submission_out(row: FormSubmission) -> FormSubmissionOut:
    return FormSubmissionOut(
        id=row.id,
        tenant_id=row.tenant_id,
        template_id=row.template_id,
        submitted_by_user_id=row.submitted_by_user_id,
        answers=decrypt_json(row.answers_encrypted),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/templates", response_model=FormTemplateOut)
async def create_template(
    payload: FormTemplateCreateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> FormTemplateOut:
    row = FormTemplate(
        tenant_id=ctx.tenant_id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        fields_schema=payload.fields_schema,
        created_by_user_id=ctx.user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_FORM_TEMPLATE",
        target_type="form_template",
        target_id=str(row.id),
    )
    return _template_out(row)


@router.get("/templates", response_model=list[FormTemplateOut])
async def list_templates(ctx=Depends(get_request_context), db: AsyncSession = Depends(get_db_session)) -> list[FormTemplateOut]:
    stmt = select(FormTemplate).where(FormTemplate.tenant_id == ctx.tenant_id).order_by(FormTemplate.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [_template_out(row) for row in rows]


@router.patch("/templates/{template_id}", response_model=FormTemplateOut)
async def update_template(
    template_id: UUID,
    payload: FormTemplateUpdateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> FormTemplateOut:
    stmt = select(FormTemplate).where(and_(FormTemplate.id == template_id, FormTemplate.tenant_id == ctx.tenant_id))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.description is not None:
        row.description = payload.description.strip()
    if payload.fields_schema is not None:
        row.fields_schema = payload.fields_schema

    await db.commit()
    await db.refresh(row)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="UPDATE_FORM_TEMPLATE",
        target_type="form_template",
        target_id=str(row.id),
    )
    return _template_out(row)


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: UUID,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    stmt = select(FormTemplate).where(and_(FormTemplate.id == template_id, FormTemplate.tenant_id == ctx.tenant_id))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    await db.delete(row)
    await db.commit()
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="DELETE_FORM_TEMPLATE",
        target_type="form_template",
        target_id=str(template_id),
    )
    return {"ok": True}


@router.post("/templates/{template_id}/responses", response_model=FormSubmissionOut)
async def submit_response(
    template_id: UUID,
    payload: FormSubmissionCreateIn,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> FormSubmissionOut:
    template_stmt = select(FormTemplate).where(and_(FormTemplate.id == template_id, FormTemplate.tenant_id == ctx.tenant_id))
    template = (await db.execute(template_stmt)).scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    row = FormSubmission(
        tenant_id=ctx.tenant_id,
        template_id=template_id,
        submitted_by_user_id=ctx.user.id,
        answers_encrypted=encrypt_json(payload.answers),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _submission_out(row)


@router.get("/templates/{template_id}/responses", response_model=list[FormSubmissionOut])
async def list_responses_for_template(
    template_id: UUID,
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[FormSubmissionOut]:
    is_admin = ctx.user.role.value in {"SUPERADMIN", "ADMIN"}
    stmt = select(FormSubmission).where(
        and_(FormSubmission.tenant_id == ctx.tenant_id, FormSubmission.template_id == template_id)
    )
    if not is_admin:
        stmt = stmt.where(FormSubmission.submitted_by_user_id == ctx.user.id)
    rows = (await db.execute(stmt.order_by(FormSubmission.created_at.desc()))).scalars().all()
    return [_submission_out(row) for row in rows]

