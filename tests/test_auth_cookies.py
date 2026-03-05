from __future__ import annotations

import uuid

import asyncio
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.session import engine
from app.main import app
from app.modules.auth import router as auth_router
from app.services.google_oauth import GoogleIdentity


def _mock_identity(email: str) -> GoogleIdentity:
    return GoogleIdentity(
        sub=f"google-sub-{uuid.uuid4().hex}",
        email=email,
        email_verified=True,
        name="Cookie User",
    )


@pytest.fixture(autouse=True)
def _reset_async_engine_pool():
    asyncio.run(engine.dispose())
    yield
    asyncio.run(engine.dispose())


def test_google_login_sets_auth_cookies(monkeypatch) -> None:
    email = f"cookie.login.{uuid.uuid4().hex[:10]}@cossmicrings.com"
    monkeypatch.setattr(settings, "SUPERADMIN_EMAIL", email)
    monkeypatch.setattr(auth_router, "verify_google_identity", lambda _token: _mock_identity(email))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/google/login",
            headers={"X-Tenant-ID": settings.DEFAULT_TENANT_ID},
            json={"id_token": "x" * 32},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["me"]["email"] == email
    assert "access_token" not in payload
    assert "refresh_token" not in payload
    assert settings.AUTH_ACCESS_COOKIE_NAME in response.cookies
    assert settings.AUTH_REFRESH_COOKIE_NAME in response.cookies
    assert "httponly" in response.headers.get("set-cookie", "").lower()


def test_auth_me_requires_auth() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me", headers={"X-Tenant-ID": settings.DEFAULT_TENANT_ID})
    assert response.status_code == 401


def test_auth_me_returns_user_with_cookie(monkeypatch) -> None:
    email = f"cookie.me.{uuid.uuid4().hex[:10]}@cossmicrings.com"
    monkeypatch.setattr(settings, "SUPERADMIN_EMAIL", email)
    monkeypatch.setattr(auth_router, "verify_google_identity", lambda _token: _mock_identity(email))

    with TestClient(app) as client:
        login_response = client.post(
            "/api/v1/auth/google/login",
            headers={"X-Tenant-ID": settings.DEFAULT_TENANT_ID},
            json={"id_token": "y" * 32},
        )
        assert login_response.status_code == 200

        me_response = client.get("/api/v1/auth/me", headers={"X-Tenant-ID": settings.DEFAULT_TENANT_ID})

    assert me_response.status_code == 200
    assert me_response.json()["me"]["email"] == email


def test_dev_login_blocked_in_prod(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ENV", "prod")
    monkeypatch.setattr(settings, "DEV_AUTH_BYPASS", True)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/dev/login",
            headers={"X-Tenant-ID": settings.DEFAULT_TENANT_ID},
            json={"email": "superadmin@cossmicrings.com", "full_name": "Super Admin"},
        )

    assert response.status_code == 404


def test_google_login_requires_invite_for_new_user(monkeypatch) -> None:
    email = f"new.no.invite.{uuid.uuid4().hex[:10]}@cossmicrings.com"
    monkeypatch.setattr(auth_router, "verify_google_identity", lambda _token: _mock_identity(email))

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/google/login",
            headers={"X-Tenant-ID": settings.DEFAULT_TENANT_ID},
            json={"id_token": "z" * 32},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invite required for onboarding"
