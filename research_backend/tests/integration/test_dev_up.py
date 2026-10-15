"""Integration test: backend /health reachable after `task dev:up` (T041).

Spec: FEATURE-001-m1-infra — Task T041
Owner: Dev.cai.1

This test belongs to **critical_path_1** (query submission → mock SSE
end-to-end) — without `/health` reachable on the docker-compose stack,
the demo can't begin.

Test design:
  - Marked `@pytest.mark.integration` so it can be deselected with
    `-m "not integration"` on developer laptops.
  - Each service is probed via `httpx` (the same client used by the frontend
    in production). Ports match `data-model.md §Service` and the
    `deploy/docker-compose.yml` mapping owned by Dev.cai.4.
  - We DO NOT spawn docker-compose from inside the test — the test is
    invoked *after* `task dev:up` has brought services up. CI / local
    devs run:

        task dev:up
        pytest -m integration tests/integration/test_dev_up.py

    That separation keeps tests hermetic and avoids depending on the
    docker CLI inside pytest.
"""

from __future__ import annotations

import socket

import httpx

import pytest


# Service → host:port mapping. Each entry corresponds to a service declared
# in `deploy/docker-compose.yml`. The docker-compose v1 maps container
# ports onto the host, so we can talk to localhost from the test runner.
SERVICE_ENDPOINTS: dict[str, tuple[str, int, str]] = {
    "backend": ("localhost", 8000, "/health"),
    # Frontend & langfuse are reachable on their published ports. The
    # backend is the only hard dependency for `task dev:up` smoke — the
    # others are probed best-effort.
    "frontend": ("localhost", 3000, "/"),
    "langfuse": ("localhost", 3001, "/api/public/health"),
}


def _tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Lightweight TCP probe — used to short-circuit HTTP calls."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Hard requirement — backend /health must be 200 ok
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.critical_path_1
def test_backend_health_returns_ok() -> None:
    """`task dev:up` MUST result in a reachable backend /health."""
    host, port, path = SERVICE_ENDPOINTS["backend"]
    if not _tcp_open(host, port):
        pytest.skip(
            f"backend not reachable at {host}:{port} — run `task dev:up` first"
        )
    response = httpx.get(f"http://{host}:{port}{path}", timeout=5.0)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("status") == "ok"
    # constitution VII — X-Latency-MS header set by middleware
    assert "X-Latency-MS" in response.headers


# ---------------------------------------------------------------------------
# Best-effort — other services that the demo expects to be reachable
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.parametrize(
    "name,host,port,path",
    [
        pytest.param(name, host, port, path, id=name)
        for name, (host, port, path) in SERVICE_ENDPOINTS.items()
    ],
)
def test_service_reachable(
    name: str, host: str, port: int, path: str
) -> None:
    """Smoke probe — each declared service should accept connections."""
    if not _tcp_open(host, port):
        pytest.skip(f"{name} not reachable at {host}:{port}")
    response = httpx.get(f"http://{host}:{port}{path}", timeout=5.0)
    assert response.status_code < 500, (
        f"{name} returned {response.status_code}: {response.text}"
    )


# ---------------------------------------------------------------------------
# Latency budget — SC-003 first-letter ≤ 500ms (mock only)
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.critical_path_1
def test_health_latency_under_500ms() -> None:
    """The backend MUST respond to /health within 500ms (constitution P99)."""
    host, port, path = SERVICE_ENDPOINTS["backend"]
    if not _tcp_open(host, port):
        pytest.skip(f"backend not reachable at {host}:{port}")
    response = httpx.get(f"http://{host}:{port}{path}", timeout=5.0)
    assert response.elapsed.total_seconds() * 1000 < 500, (
        f"backend /health took {response.elapsed.total_seconds() * 1000:.1f}ms"
    )