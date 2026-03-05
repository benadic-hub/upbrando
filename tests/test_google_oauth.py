import pytest

from app.services import google_oauth


def test_verify_google_identity_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_verify(token: str, _request, audience: str):
        assert token == "token-123"
        assert audience
        return {
            "iss": "https://accounts.google.com",
            "sub": "google-sub-1",
            "email": "pilot.admin@cossmicrings.com",
            "email_verified": True,
            "name": "Pilot Admin",
        }

    monkeypatch.setattr(google_oauth.id_token, "verify_oauth2_token", fake_verify)
    identity = google_oauth.verify_google_identity("token-123")
    assert identity.sub == "google-sub-1"
    assert identity.email == "pilot.admin@cossmicrings.com"
    assert identity.email_verified is True
    assert identity.name == "Pilot Admin"


def test_verify_google_identity_rejects_invalid_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_verify(_token: str, _request, _audience: str):
        return {
            "iss": "https://malicious.example",
            "sub": "google-sub-2",
            "email": "pilot.admin@cossmicrings.com",
            "email_verified": True,
            "name": "Pilot Admin",
        }

    monkeypatch.setattr(google_oauth.id_token, "verify_oauth2_token", fake_verify)
    with pytest.raises(ValueError, match="Invalid Google token issuer"):
        google_oauth.verify_google_identity("token-123")


def test_verify_google_identity_requires_email_and_sub(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_verify(_token: str, _request, _audience: str):
        return {
            "iss": "accounts.google.com",
            "sub": "",
            "email": "",
            "email_verified": True,
        }

    monkeypatch.setattr(google_oauth.id_token, "verify_oauth2_token", fake_verify)
    with pytest.raises(ValueError, match="Google token missing required claims"):
        google_oauth.verify_google_identity("token-123")
