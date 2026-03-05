from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any

from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.core.config import settings


password_hasher = PasswordHasher()
fernet = Fernet(settings.FERNET_KEY.encode("utf-8"))


class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(slots=True)
class TokenPayload:
    sub: str
    tenant_id: str
    role: str
    token_type: str
    jti: str
    exp: int
    iat: int


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return password_hasher.verify(hashed, password)
    except Exception:
        return False


def build_token(*, sub: str, role: str, tenant_id: str, token_type: str) -> tuple[str, str]:
    issued = now_utc()
    if token_type == TokenType.ACCESS:
        expires = issued + dt.timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    elif token_type == TokenType.REFRESH:
        expires = issued + dt.timedelta(days=settings.REFRESH_TOKEN_DAYS)
    else:
        raise ValueError("Unsupported token type")

    jti = str(uuid.uuid4())
    payload = {
        "sub": sub,
        "role": role,
        "tenant_id": tenant_id,
        "type": token_type,
        "jti": jti,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }
    encoded = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded, jti


def decode_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

    required = {"sub", "tenant_id", "role", "type", "jti", "iat", "exp"}
    if not required.issubset(payload):
        raise ValueError("Token payload missing required claims")

    return TokenPayload(
        sub=str(payload["sub"]),
        tenant_id=str(payload["tenant_id"]),
        role=str(payload["role"]),
        token_type=str(payload["type"]),
        jti=str(payload["jti"]),
        exp=int(payload["exp"]),
        iat=int(payload["iat"]),
    )


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def encrypt_json(data: dict[str, Any]) -> str:
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return fernet.encrypt(raw).decode("utf-8")


def decrypt_json(value: str) -> dict[str, Any]:
    decrypted = fernet.decrypt(value.encode("utf-8"))
    payload = json.loads(decrypted.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Decrypted payload must be an object")
    return payload

