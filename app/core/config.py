from __future__ import annotations

from typing import Any

from cryptography.fernet import Fernet
from email_validator import EmailNotValidError, validate_email
from pydantic import Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=True,
    )

    APP_NAME: str = "Upbrando EMS Backend"
    APP_VERSION: str = "1.0.0"
    ENV: str = "dev"
    PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    DEFAULT_TENANT_ID: str = "default"

    DATABASE_URL: str = Field(
        description="Async SQLAlchemy URL. Example: postgresql+asyncpg://user:pass@host:5432/db"
    )

    JWT_SECRET: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 30
    REFRESH_TOKEN_DAYS: int = 14

    GOOGLE_CLIENT_ID: str = Field(
        description="Google OAuth Web client id used to verify id_token audience."
    )
    COMPANY_EMAIL_DOMAIN: str | None = "cossmicrings.com"
    COMPANY_EMAIL_ALLOWLIST: str | None = None

    FERNET_KEY: str = Field(
        description="Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )

    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_AUTH_REQUESTS: int = 10
    RATE_LIMIT_CHAT_REQUESTS: int = 60

    AUTH_ACCESS_COOKIE_NAME: str = "ems_access_token"
    AUTH_REFRESH_COOKIE_NAME: str = "ems_refresh_token"
    AUTH_COOKIE_SAMESITE: str = "lax"
    AUTH_COOKIE_SECURE: bool | None = None
    AUTH_COOKIE_DOMAIN: str | None = None

    SUPERADMIN_EMAIL: str | None = None
    SUPERADMIN_PASSWORD: str | None = None

    OFFICE_IP_ALLOWLIST: str | None = None
    DEV_AUTH_BYPASS: bool = False
    MIGRATE_ON_START: bool = False

    S3_BUCKET: str
    S3_REGION: str = "ap-south-1"
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_FORCE_PATH_STYLE: bool = False
    PRESIGNED_URL_EXPIRES_SECONDS: int = 900
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024
    ATTACHMENTS_ALLOWED_CONTENT_TYPES: str = "image/png,image/jpeg,application/pdf,text/plain"

    @field_validator("ENV")
    @classmethod
    def validate_env(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"dev", "prod"}:
            raise ValueError("ENV must be one of: dev, prod")
        return cleaned

    @field_validator("COMPANY_EMAIL_DOMAIN")
    @classmethod
    def validate_company_domain(cls, value: str | None) -> str | None:
        if not value:
            return None
        cleaned = value.strip().lower().lstrip("@")
        if not cleaned:
            return None
        if "." not in cleaned:
            raise ValueError("COMPANY_EMAIL_DOMAIN must be a valid domain")
        return cleaned

    @field_validator("COMPANY_EMAIL_ALLOWLIST")
    @classmethod
    def validate_company_email_allowlist(cls, value: str | None) -> str | None:
        if not value:
            return None
        emails = [item.strip().lower() for item in value.split(",") if item.strip()]
        if not emails:
            return None
        for email in emails:
            try:
                validate_email(email, check_deliverability=False)
            except EmailNotValidError as exc:
                raise ValueError(f"Invalid COMPANY_EMAIL_ALLOWLIST entry: {email}") from exc
        return ",".join(emails)

    @field_validator("FERNET_KEY")
    @classmethod
    def validate_fernet_key(cls, value: str) -> str:
        try:
            Fernet(value.encode("utf-8"))
        except Exception as exc:
            raise ValueError("FERNET_KEY is invalid") from exc
        return value

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        entries = [x.strip() for x in value.split(",") if x.strip()]
        if not entries:
            raise ValueError("CORS_ALLOWED_ORIGINS cannot be empty")
        return ",".join(entries)

    @field_validator("ATTACHMENTS_ALLOWED_CONTENT_TYPES")
    @classmethod
    def validate_attachment_content_types(cls, value: str) -> str:
        entries = [item.strip().lower() for item in value.split(",") if item.strip()]
        if not entries:
            raise ValueError("ATTACHMENTS_ALLOWED_CONTENT_TYPES cannot be empty")
        return ",".join(entries)

    @field_validator("AUTH_COOKIE_SAMESITE")
    @classmethod
    def validate_cookie_samesite(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"lax", "strict", "none"}:
            raise ValueError("AUTH_COOKIE_SAMESITE must be one of: lax, strict, none")
        return cleaned

    @model_validator(mode="after")
    def validate_runtime_safety(self) -> "Settings":
        if not self.COMPANY_EMAIL_DOMAIN and not self.company_email_allowlist:
            raise ValueError("Set COMPANY_EMAIL_DOMAIN or COMPANY_EMAIL_ALLOWLIST")

        if self.DEV_AUTH_BYPASS and self.ENV != "dev":
            raise ValueError("DEV_AUTH_BYPASS is allowed only when ENV=dev")

        if self.ENV == "prod":
            if len(self.JWT_SECRET.strip()) < 32:
                raise ValueError("JWT_SECRET must be at least 32 characters in prod")
            weak_markers = ("replace_with", "change_this", "dev_only", "example")
            if any(marker in self.JWT_SECRET.lower() for marker in weak_markers):
                raise ValueError("JWT_SECRET appears to be a placeholder in prod")

            if self.S3_ENDPOINT_URL:
                raise ValueError("S3_ENDPOINT_URL must be empty in prod when using AWS S3")

            origins = self.cors_allowed_origins
            if any(origin == "*" for origin in origins):
                raise ValueError("CORS_ALLOWED_ORIGINS cannot contain '*' in prod")
            if any("localhost" in origin or "127.0.0.1" in origin for origin in origins):
                raise ValueError("CORS_ALLOWED_ORIGINS cannot include localhost/127.0.0.1 in prod")

            db_url = self.DATABASE_URL.lower()
            if "@db:" in db_url or "localhost" in db_url or "127.0.0.1" in db_url:
                raise ValueError("DATABASE_URL must target managed Postgres (RDS) in prod")

            if not self.auth_cookie_secure:
                raise ValueError("AUTH_COOKIE_SECURE must be true in prod")
            if not self.AUTH_COOKIE_DOMAIN:
                raise ValueError("AUTH_COOKIE_DOMAIN must be set in prod")
            if not self.AUTH_COOKIE_DOMAIN.startswith("."):
                raise ValueError("AUTH_COOKIE_DOMAIN should start with '.' (example: .upbrando.com)")
            if self.AUTH_COOKIE_DOMAIN != ".upbrando.com":
                raise ValueError("AUTH_COOKIE_DOMAIN must be .upbrando.com in prod")

        if self.AUTH_COOKIE_SAMESITE == "none" and not self.auth_cookie_secure:
            raise ValueError("AUTH_COOKIE_SAMESITE=none requires AUTH_COOKIE_SECURE=true")

        return self

    @property
    def is_prod(self) -> bool:
        return self.ENV == "prod"

    @property
    def is_dev(self) -> bool:
        return self.ENV == "dev"

    @property
    def cors_allowed_origins(self) -> list[str]:
        return [x.strip() for x in self.CORS_ALLOWED_ORIGINS.split(",") if x.strip()]

    @property
    def company_email_allowlist(self) -> set[str]:
        if not self.COMPANY_EMAIL_ALLOWLIST:
            return set()
        return {x.strip().lower() for x in self.COMPANY_EMAIL_ALLOWLIST.split(",") if x.strip()}

    @property
    def office_ip_allowlist(self) -> set[str]:
        if not self.OFFICE_IP_ALLOWLIST:
            return set()
        return {x.strip() for x in self.OFFICE_IP_ALLOWLIST.split(",") if x.strip()}

    @property
    def allowed_attachment_content_types(self) -> set[str]:
        return {
            x.strip().lower() for x in self.ATTACHMENTS_ALLOWED_CONTENT_TYPES.split(",") if x.strip()
        }

    @property
    def s3_addressing_style(self) -> str:
        if self.is_prod and not self.S3_ENDPOINT_URL:
            return "virtual"
        return "path" if self.S3_FORCE_PATH_STYLE else "auto"

    @property
    def auth_cookie_secure(self) -> bool:
        if self.AUTH_COOKIE_SECURE is None:
            return self.is_prod
        return self.AUTH_COOKIE_SECURE


def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:  # pragma: no cover
        raise RuntimeError(f"Invalid environment configuration: {exc}") from exc


settings: Settings = load_settings()
