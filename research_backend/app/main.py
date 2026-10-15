"""FastAPI application entrypoint (T016 — Dev.cai.1).

Spec: FEATURE-001-m1-infra — Task T016
Owner: Dev.cai.1

Responsibilities (M1):
  - Construct the FastAPI instance.
  - Run startup / shutdown hooks via the `lifespan` context manager.
  - Configure CORS for the local frontend (`http://localhost:3000`).
  - Register a global exception handler that maps domain errors to the
    HTTP shapes defined in `contracts/openapi.yaml`.
  - Print a single banner on boot with service / version / port so an
    operator can confirm the container is alive (constitution VII).

Anything that wires real LangGraph / Postgres / Langfuse lives in
`app/api/routes.py` (T031, Dev.cai.2) and is mounted via
`app.include_router(...)`. Dev.cai.1 only scaffolds the shell.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.deps import health_snapshot
from app.config import Settings, SettingsError, get_settings
from app.observability.logging import configure_logging, get_logger

_LOG = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — boot banner + structured log on shutdown."""
    settings = get_settings()
    configure_logging()
    _LOG.info(
        "service_starting",
        event="service_starting",
        actor="system",
        latency_ms=0,
        error="",
        version=__version__,
        environment=settings.environment,
        http_port=settings.http_port,
    )
    try:
        yield
    finally:
        _LOG.info(
            "service_stopping",
            event="service_stopping",
            actor="system",
            latency_ms=0,
            error="",
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory.

    Factories keep tests independent — each test can construct a fresh
    `FastAPI` instance with overridden dependencies. Production code uses
    the module-level singleton below (`app = create_app()`).
    """
    settings = settings or get_settings()

    app = FastAPI(
        title="hochoy Deep Research Agent — backend",
        version=__version__,
        description=(
            "M1 mock echo service. See "
            "`specs/001-m1-infra/spec.md` and "
            "`specs/001-m1-infra/contracts/openapi.yaml`."
        ),
        lifespan=lifespan,
    )

    # ---- CORS (constitution I: explicit allow-list) ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        max_age=60 * 10,
    )

    # ---- Global exception handlers ----
    @app.exception_handler(SettingsError)
    async def _settings_error_handler(_: Request, exc: SettingsError) -> JSONResponse:
        # Misconfiguration at request time = P0. Constitution I says fail closed.
        _LOG.error(
            "config_error",
            event="config_error",
            latency_ms=0,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "config_error", "message": str(exc)},
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Last-resort net — log with elapsed latency, never leak stack frames.
        started = getattr(request.state, "_started_at", time.monotonic())
        elapsed_ms = int((time.monotonic() - started) * 1000)
        _LOG.exception(
            "unhandled_exception",
            event="unhandled_exception",
            actor="system",
            latency_ms=elapsed_ms,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "internal_error", "message": "internal server error"},
        )

    # ---- Health route (contracts/openapi.yaml §paths/health) ----
    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        # health_snapshot() is the DI seam for Dev.cai.2 / Dev.cai.4
        # when real Postgres / Redis / Langfuse wiring lands.
        snapshot = health_snapshot()
        # Defensive: never expose cached deps blob in the response body —
        # return a minimal {"status": "ok"} shape per openapi.yaml.
        return {"status": snapshot.get("status", "ok")}

    # ---- Request timing middleware (constitution VII latency_ms) ----
    @app.middleware("http")
    async def _request_timing(request: Request, call_next):
        request.state.started_at = time.monotonic()
        response = await call_next(request)
        elapsed_ms = int((time.monotonic() - request.state.started_at) * 1000)
        # Decorate the response header so devtools / browser extensions can
        # spot the backend's own latency number.
        response.headers["X-Latency-MS"] = str(elapsed_ms)
        return response

    # ---- Mount routers ----
    # Dev.cai.2 will add `app.include_router(threads_router)` here once
    # routes.py (T031) ships. Leaving the seam explicit so future
    # Co-Owners know where to plug in.

    return app


# Module-level singleton — uvicorn entrypoint reads `app:app`.
#
# We defer construction via a PEP 562 module `__getattr__` so that simply
# importing `app.main` does NOT eagerly validate configuration. Tests
# (and any tooling that imports the module) won't crash just because
# `POSTGRES_PASSWORD` isn't set yet; the app only validates the first
# time `app.main:app` is actually resolved (i.e. when uvicorn loads it
# in production, or when a test fixture references it).
_app_singleton: FastAPI | None = None


def __getattr__(name: str):
    """PEP 562 — `from app.main import app` triggers this only when accessed."""
    global _app_singleton
    if name == "app":
        if _app_singleton is None:
            _app_singleton = create_app()
        return _app_singleton
    raise AttributeError(f"module 'app.main' has no attribute {name!r}")


def main() -> None:
    """Console-script entrypoint for `python -m app.main`."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.http_host,
        port=settings.http_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()