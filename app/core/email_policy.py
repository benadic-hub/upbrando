from __future__ import annotations

from app.core.config import settings


def is_allowed_company_email(email: str) -> bool:
    normalized = email.strip().lower()
    if not normalized:
        return False

    allowlist = settings.company_email_allowlist
    if allowlist and normalized in allowlist:
        return True

    if settings.COMPANY_EMAIL_DOMAIN and normalized.endswith(f"@{settings.COMPANY_EMAIL_DOMAIN}"):
        return True

    return False
