from __future__ import annotations

from dataclasses import dataclass

from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings


@dataclass(slots=True)
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    name: str


def verify_google_identity(token: str) -> GoogleIdentity:
    if not token or not token.strip():
        raise ValueError("Missing id_token")

    info = id_token.verify_oauth2_token(
        token,
        requests.Request(),
        settings.GOOGLE_CLIENT_ID,
    )
    issuer = str(info.get("iss", "")).strip()
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        raise ValueError("Invalid Google token issuer")

    sub = str(info.get("sub", "")).strip()
    email = str(info.get("email", "")).strip().lower()
    if not sub or not email:
        raise ValueError("Google token missing required claims")

    verified = bool(info.get("email_verified"))
    return GoogleIdentity(
        sub=sub,
        email=email,
        email_verified=verified,
        name=str(info.get("name", "")),
    )
