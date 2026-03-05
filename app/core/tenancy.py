from __future__ import annotations

from fastapi import Header, HTTPException, Request, status

from app.core.config import settings
from app.core.rate_limit import client_ip


def get_tenant_id(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> str:
    tenant_id = (x_tenant_id or settings.DEFAULT_TENANT_ID).strip()
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID cannot be blank",
        )
    return tenant_id


def enforce_admin_ip_allowlist(request: Request) -> None:
    allowlist = settings.office_ip_allowlist
    if not allowlist:
        return
    source_ip = client_ip(request)
    if source_ip not in allowlist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin endpoint is restricted by office IP allowlist",
        )

