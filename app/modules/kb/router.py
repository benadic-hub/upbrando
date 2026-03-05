from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_request_context, require_admin_role
from app.db.models import KnowledgeArticle, KnowledgeCategory
from app.db.session import get_db_session
from app.schemas.kb import (
    KnowledgeArticleCreateIn,
    KnowledgeArticleOut,
    KnowledgeArticleUpdateIn,
    KnowledgeCategoryCreateIn,
    KnowledgeCategoryOut,
)
from app.services.audit import write_audit_log


router = APIRouter(prefix="/kb", tags=["knowledge-base"])


def _category_out(row: KnowledgeCategory) -> KnowledgeCategoryOut:
    return KnowledgeCategoryOut(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        description=row.description,
    )


def _article_out(row: KnowledgeArticle) -> KnowledgeArticleOut:
    return KnowledgeArticleOut(
        id=row.id,
        tenant_id=row.tenant_id,
        category_id=row.category_id,
        title=row.title,
        content=row.content,
        created_by_user_id=row.created_by_user_id,
        updated_by_user_id=row.updated_by_user_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/categories", response_model=KnowledgeCategoryOut)
async def create_category(
    payload: KnowledgeCategoryCreateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeCategoryOut:
    exists_stmt = select(KnowledgeCategory).where(
        and_(
            KnowledgeCategory.tenant_id == ctx.tenant_id,
            func.lower(KnowledgeCategory.name) == payload.name.lower(),
        )
    )
    if (await db.execute(exists_stmt)).scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists")

    row = KnowledgeCategory(
        tenant_id=ctx.tenant_id,
        name=payload.name.strip(),
        description=payload.description.strip(),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _category_out(row)


@router.get("/categories", response_model=list[KnowledgeCategoryOut])
async def list_categories(ctx=Depends(get_request_context), db: AsyncSession = Depends(get_db_session)) -> list[KnowledgeCategoryOut]:
    stmt = select(KnowledgeCategory).where(KnowledgeCategory.tenant_id == ctx.tenant_id).order_by(KnowledgeCategory.name.asc())
    rows = (await db.execute(stmt)).scalars().all()
    return [_category_out(row) for row in rows]


@router.post("/articles", response_model=KnowledgeArticleOut)
async def create_article(
    payload: KnowledgeArticleCreateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeArticleOut:
    if payload.category_id:
        category_stmt = select(KnowledgeCategory).where(
            and_(KnowledgeCategory.id == payload.category_id, KnowledgeCategory.tenant_id == ctx.tenant_id)
        )
        if not (await db.execute(category_stmt)).scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    row = KnowledgeArticle(
        tenant_id=ctx.tenant_id,
        category_id=payload.category_id,
        title=payload.title.strip(),
        content=payload.content.strip(),
        created_by_user_id=ctx.user.id,
        updated_by_user_id=ctx.user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="CREATE_KB_ARTICLE",
        target_type="kb_article",
        target_id=str(row.id),
    )
    return _article_out(row)


@router.get("/articles", response_model=list[KnowledgeArticleOut])
async def list_articles(
    title: str | None = Query(default=None, min_length=1),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[KnowledgeArticleOut]:
    stmt = select(KnowledgeArticle).where(KnowledgeArticle.tenant_id == ctx.tenant_id)
    if title:
        stmt = stmt.where(func.lower(KnowledgeArticle.title).like(f"%{title.lower()}%"))
    rows = (await db.execute(stmt.order_by(KnowledgeArticle.updated_at.desc()))).scalars().all()
    return [_article_out(row) for row in rows]


@router.get("/articles/{article_id}", response_model=KnowledgeArticleOut)
async def get_article(article_id: UUID, ctx=Depends(get_request_context), db: AsyncSession = Depends(get_db_session)) -> KnowledgeArticleOut:
    stmt = select(KnowledgeArticle).where(and_(KnowledgeArticle.id == article_id, KnowledgeArticle.tenant_id == ctx.tenant_id))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return _article_out(row)


@router.patch("/articles/{article_id}", response_model=KnowledgeArticleOut)
async def update_article(
    article_id: UUID,
    payload: KnowledgeArticleUpdateIn,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> KnowledgeArticleOut:
    stmt = select(KnowledgeArticle).where(and_(KnowledgeArticle.id == article_id, KnowledgeArticle.tenant_id == ctx.tenant_id))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    if payload.category_id is not None:
        if payload.category_id:
            category_stmt = select(KnowledgeCategory).where(
                and_(KnowledgeCategory.id == payload.category_id, KnowledgeCategory.tenant_id == ctx.tenant_id)
            )
            if not (await db.execute(category_stmt)).scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        row.category_id = payload.category_id
    if payload.title is not None:
        row.title = payload.title.strip()
    if payload.content is not None:
        row.content = payload.content.strip()
    row.updated_by_user_id = ctx.user.id

    await db.commit()
    await db.refresh(row)
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="UPDATE_KB_ARTICLE",
        target_type="kb_article",
        target_id=str(row.id),
    )
    return _article_out(row)


@router.delete("/articles/{article_id}")
async def delete_article(
    article_id: UUID,
    _admin=Depends(require_admin_role),
    ctx=Depends(get_request_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    stmt = select(KnowledgeArticle).where(and_(KnowledgeArticle.id == article_id, KnowledgeArticle.tenant_id == ctx.tenant_id))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    await db.delete(row)
    await db.commit()
    await write_audit_log(
        db,
        tenant_id=ctx.tenant_id,
        actor_user_id=ctx.user.id,
        action="DELETE_KB_ARTICLE",
        target_type="kb_article",
        target_id=str(article_id),
    )
    return {"ok": True}

