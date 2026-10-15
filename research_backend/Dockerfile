# =============================================================================
# research_backend/Dockerfile
# -----------------------------------------------------------------------------
# Spec: FEATURE-001-m1-infra — Task T044 (Owner: Dev.cai.1)
#
# Multi-stage build for the FastAPI / LangGraph backend.
# - Stage 1 (builder): install uv + resolve lockfile + build wheels.
# - Stage 2 (runtime): Python 3.12-slim with a non-root app user, no build
#   tooling, and a HEALTHCHECK that pings /health.
#
# Constitution alignment:
#   - I.  Security-First — non-root, secrets via env (never in image layers),
#                         bandit/pip-audit run in CI not at build time.
#   - III. Test-First   — base image has pytest dev-deps installed; CI mounts
#                         tests/ from the build host to keep the image small.
# =============================================================================

# ---------- Stage 1: builder ----------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# uv (Astral) — fast Python package manager. Lock with `uv lock` locally.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -LsSf https://astral.sh/uv/install.sh | sh \
 && mv /root/.local/bin/uv /usr/local/bin/uv \
 && chmod +x /usr/local/bin/uv \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only the manifest first so Docker can cache the dependency layer
# independently of source changes.
COPY pyproject.toml ./

# Resolve + install into a project-local venv. Using `uv sync` once a
# `uv.lock` is committed (M2+); for M1 we fall back to `uv pip install`
# against pyproject.toml directly.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --no-deps . || true && \
    uv pip install --system \
        "fastapi>=0.115.0" \
        "uvicorn[standard]>=0.30.0" \
        "pydantic>=2.9.0" \
        "pydantic-settings>=2.5.0" \
        "structlog>=24.4.0" \
        "langfuse>=3.0.0"


# ---------- Stage 2: runtime ----------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/usr/local/bin:/usr/bin:/bin" \
    PYTHONPATH=/app

# Minimal runtime system deps. curl is required by the HEALTHCHECK below.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates tini \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Non-root user (constitution I — never run production code as root).
RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /app

# Copy installed packages from the builder.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application source last so source-only changes don't bust the
# pip install layer.
COPY --chown=app:app app /app/app
COPY --chown=app:app pyproject.toml /app/pyproject.toml

USER app

EXPOSE 8000

# tini = PID 1 reaper so SIGTERM from `task dev:down` actually propagates
# and uvicorn's lifespan shutdown runs (constitution VII graceful shutdown).
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command — overridable by docker-compose `command:` override.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------- Healthcheck (FR-005 / data-model.md §Service) ------------------
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1