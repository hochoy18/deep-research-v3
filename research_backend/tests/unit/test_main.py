"""Unit tests for `app.main` — FastAPI app shell (Dev.cai.1).

Spec: FEATURE-001-m1-infra — Task T016
Owner: Dev.cai.1
Critical path: critical_path_1 (query → SSE end-to-end); the /health
endpoint is the first link in the chain, so it MUST be reachable in
every CI run.

These tests live next to the config tests because they share the same
environment bootstrap pattern. They do NOT spin up uvicorn — we drive
the FastAPI app directly via FastAPI's TestClient (built on starlette
+ anyio) which manages the lifespan context for us.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sure each test has a minimal but valid env."""
    for key in list(os.environ):
        if key.startswith(("POSTGRES_", "LANGFUSE_", "REDIS_", "HTTP_", "USER_ID_", "RATE_")):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("POSTGRES_PASSWORD", "testpass1234")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    get_settings.cache_clear()


@pytest.fixture()
def client() -> TestClient:
    """Yield a TestClient with the lifespan context active."""
    app = create_app()
    return TestClient(app)


@pytest.mark.critical_path_1
def test_health_endpoint_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    # constitution VII latency header is mandatory
    assert "X-Latency-MS" in response.headers


@pytest.mark.critical_path_1
def test_health_latency_header_is_integer(client: TestClient) -> None:
    response = client.get("/health")
    latency = response.headers["X-Latency-MS"]
    # The header MUST be parseable as an integer (ms).
    assert int(latency) >= 0


def test_openapi_metadata_is_set(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "hochoy Deep Research Agent — backend"
    assert "0.1.0" in schema["info"]["version"]
    # /health must be declared in the schema
    assert "/health" in schema["paths"]


def test_cors_preflight_allows_localhost(client: TestClient) -> None:
    """Constitution I — CORS allow-list MUST be set explicitly for localhost."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    # 200/204 are both acceptable preflight outcomes
    assert response.status_code in (200, 204)
    assert "access-control-allow-origin" in {k.lower() for k in response.headers}
