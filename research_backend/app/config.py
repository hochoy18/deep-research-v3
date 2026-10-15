"""Application configuration (constitution I: launch-time validation).

Spec: FEATURE-001-m1-infra — Task T017
Owner: Dev.cai.1

Loads `.env` via pydantic-settings and validates all required variables at
process startup. Missing or invalid values raise `SettingsError` so the
container exits cleanly with an actionable error message — never boots
half-configured (constitution I: fail closed).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SettingsError(RuntimeError):
    """Raised when environment configuration is missing or invalid.

    Constitution I requires that security-relevant misconfiguration MUST
    fail closed at startup, not silently degrade.
    """


class Settings(BaseSettings):
    """Strongly-typed runtime configuration.

    Values are populated from environment variables (and `.env` when
    present). Names match `.env.example` so an operator can copy the
    template without renaming anything.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Service identity ----
    service_name: str = Field(default="research-backend")
    environment: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ---- HTTP ----
    http_host: str = "0.0.0.0"
    http_port: int = 8000
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins. Production MUST be set explicitly.",
    )

    # ---- Postgres (data-model.md: entity Thread + Message) ----
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "research"
    postgres_user: str = "research"
    postgres_password: str = Field(..., min_length=8)

    @field_validator("postgres_password")
    @classmethod
    def _no_weak_passwords(cls, v: str) -> str:
        # Constitution I: reject the obvious dev-only password in non-dev envs
        forbidden = {"changeme", "postgres", "password", "12345678"}
        if v.lower() in forbidden:
            raise SettingsError(
                f"postgres_password={v!r} is a forbidden default; "
                "set a strong secret (constitution I)."
            )
        return v

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ---- Redis (data-model.md: rate-limit + LangGraph checkpoint) ----
    redis_url: str = "redis://redis:6379/0"

    # ---- Langfuse (ADR-0006 OTel API; spec FR-009 trace writes) ----
    langfuse_public_key: str = Field(..., min_length=2)
    langfuse_secret_key: str = Field(..., min_length=2)
    langfuse_host: str = "http://langfuse-server:3001"
    langfuse_otel_endpoint: str = "http://langfuse-server:3001/api/public/otel"
    langfuse_enabled: bool = True

    # ---- Anonymous cookie (spec FR-011a) ----
    user_id_cookie_name: str = "user_id"
    user_id_cookie_max_age_seconds: int = 60 * 60 * 24 * 30  # 30 days

    # ---- Rate limit (spec FR-011b) ----
    rate_limit_per_minute: int = 10
    rate_limit_per_hour: int = 100

    # ---- Startup healthcheck ----
    startup_timeout_seconds: int = 120

    # ---- Validators ----
    @field_validator("http_port", "postgres_port")
    @classmethod
    def _port_in_range(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise SettingsError(f"port {v} out of range")
        return v

    @field_validator("rate_limit_per_minute", "rate_limit_per_hour")
    @classmethod
    def _positive_int(cls, v: int) -> int:
        if v <= 0:
            raise SettingsError(f"rate limit must be > 0, got {v}")
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton accessor.

    `lru_cache` gives us process-level caching — `get_settings()` is cheap
    and re-validation only happens once per process. The first call will
    raise `SettingsError` if `.env` is missing required keys.
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as exc:  # pydantic ValidationError or our SettingsError
        # Re-wrap so the operator sees a single, well-named type
        raise SettingsError(f"invalid configuration: {exc}") from exc


__all__ = ["Settings", "SettingsError", "get_settings"]