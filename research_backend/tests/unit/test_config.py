"""Unit tests for `app.config` (T042 — Dev.cai.1).

Spec: FEATURE-001-m1-infra — Task T042
Owner: Dev.cai.1
Critical path: indirectly covered via critical_path_3 (cookie + rate-limit
config surfaced here) and critical_path_4 (Langfuse keys).

Tests:
  - happy-path: all required env vars present → Settings() returns valid object.
  - missing required var → SettingsError raised (constitution I fail closed).
  - weak password rejected.
  - port range validation.
  - rate-limit positive int validation.
  - DSN builder produces correct postgres connection string.

We patch `os.environ` rather than mutating process state, so the
`@lru_cache` on `get_settings()` does not leak between tests.
"""

from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from app.config import Settings, SettingsError, get_settings

REQUIRED_ENV = {
    "POSTGRES_PASSWORD": "supersecret",
    "LANGFUSE_PUBLIC_KEY": "pk-test",
    "LANGFUSE_SECRET_KEY": "sk-test",
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset environment + settings cache between tests."""
    for key in list(os.environ):
        if key.startswith(("POSTGRES_", "LANGFUSE_", "REDIS_", "HTTP_", "USER_ID_", "RATE_")):
            monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()


def _set_required(monkeypatch: pytest.MonkeyPatch, **overrides: object) -> None:
    env = {**REQUIRED_ENV, **overrides}
    for k, v in env.items():
        monkeypatch.setenv(k, str(v))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_happy_path_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(monkeypatch)
    settings = Settings()
    assert settings.postgres_port == 5432
    assert settings.langfuse_enabled is True
    assert settings.user_id_cookie_max_age_seconds == 60 * 60 * 24 * 30
    assert settings.rate_limit_per_minute == 10
    assert settings.rate_limit_per_hour == 100


def test_postgres_dsn_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(
        monkeypatch,
        POSTGRES_HOST="db.local",
        POSTGRES_PORT=5433,
        POSTGRES_DB="deep",
        POSTGRES_USER="alice",
        POSTGRES_PASSWORD="hunter22hunter22",
    )
    settings = Settings()
    assert (
        settings.postgres_dsn
        == "postgresql://alice:hunter22hunter22@db.local:5433/deep"
    )


# ---------------------------------------------------------------------------
# Failure paths — Constitution I fail-closed
# ---------------------------------------------------------------------------


def test_missing_required_var_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(monkeypatch)
    monkeypatch.delenv("POSTGRES_PASSWORD")
    with pytest.raises(ValidationError):
        Settings()


def test_weak_postgres_password_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(monkeypatch, POSTGRES_PASSWORD="postgres")
    with pytest.raises((ValidationError, SettingsError)):
        Settings()


def test_out_of_range_port_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(monkeypatch, HTTP_PORT="70000")
    # Pydantic v2 lets our custom `SettingsError` propagate verbatim — accept
    # either the wrapped or unwrapped form so the contract is clear.
    with pytest.raises((ValidationError, SettingsError)):
        Settings()


def test_zero_rate_limit_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(monkeypatch, RATE_LIMIT_PER_MINUTE="0")
    with pytest.raises((ValidationError, SettingsError)):
        Settings()


# ---------------------------------------------------------------------------
# Cached accessor
# ---------------------------------------------------------------------------


def test_get_settings_returns_cached_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(monkeypatch)
    a = get_settings()
    b = get_settings()
    assert a is b


def test_get_settings_wraps_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_required(monkeypatch)
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY")
    with pytest.raises(SettingsError):
        get_settings()