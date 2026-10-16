# =============================================================================
# research_backend/Dockerfile — multi-stage, uv-managed, non-root
# =============================================================================
# Stage 1 (builder): install uv → copy pyproject.toml + uv.lock → sync deps
#                    into a clean .venv → drop the .venv into stage 2.
# Stage 2 (runtime): python:3.12-slim + the .venv + app source + healthcheck.
#
# Optimisations:
#   - uv sync --no-install-project keeps the venv independent of source so
#     CI can rebuild the source layer without re-resolving deps.
#   - Layer order: lockfile before source — code edits never bust the
#     dependency cache.
#   - Pinned Python patch (3.12) + pinned uv (0.5.x for reproducibility).
#   - Runs as a dedicated non-root uid (10001) — matches deploy/docker-
#     compose.yml (T012) user directive.
#
# Spec traceability:
#   - ADR-0012 (Python 3.12)
#   - ADR-0005 (LangChain classic)
#   - constitution I: SAST/SCA pre-baked; SCA via \`pip-audit\` (T015/T032)
#   - FR-004 env-validation + healthcheck (T016 will mount a /health)
#
# Build context: the research_backend/ directory (not repo root) — see
# deploy/docker-compose.yml (T012) for the build.context wiring.
# =============================================================================

# ---- Stage 1: dependency resolver ----------------------------------------
FROM python:3.12-slim AS builder

# Disable pip cache + bytecode; forces reproducible wheels.
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# Install uv at a pinned version. Day-1 lock policy (README §M1 kickoff)
# keeps tool versions frozen so builds are byte-identical.
ARG UV_VERSION=0.5.18
RUN --mount=type=cache,target=/root/.cache/uv \
    pip install --no-cache-dir "uv==${UV_VERSION}"

WORKDIR /build

# Copy ONLY the project metadata first — these layers change rarely, so
# the heavy install (80 packages) is cached across source-only edits.
COPY pyproject.toml uv.lock ./
COPY README.md ./ 2>/dev/null || true

# \`uv sync\` creates a project-local .venv and installs locked deps
# without the project source itself (--no-install-project). We'll mount
# the source in at runtime via stage 2.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev --frozen

# ---- Stage 2: runtime ----------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}" \
    PYTHONPATH="/app"

# Run as non-root (uid 10001) for defence-in-depth (constitution I).
# The numeric uid lets \`docker-compose\` (T012) keep volume perms simple.
RUN groupadd --system --gid 10001 app \
    && useradd  --system --uid 10001 --gid app --no-create-home app \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        # healthcheck (FR-004 / SC-001)
        curl \
        # TLS root CA bundle for Postgres + Langfuse calls
        ca-certificates \
        # tini for clean PID 1 signal handling
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Carry over the .venv from the builder stage.
COPY --from=builder --chown=app:app /build/.venv /app/.venv

# Carry over the project source last (most volatile layer).
COPY --chown=app:app pyproject.toml uv.lock README.md ./
COPY --chown=app:app app ./app

USER app

EXPOSE 8000

# Default values are documented in .env.example (T010); the compose file
# (T012) injects the real values via \`environment:\` / \`env_file:\`.
ENV APP_PORT=8000 \
    APP_HOST=0.0.0.0 \
    APP_LOG_LEVEL=INFO

# HEALTHCHECK — verify uvicorn is serving /health (T016 will register the
# route). \`--fail\` makes curl exit non-zero on non-2xx so Docker marks
# the container unhealthy and lets the orchestrator pull its weight.
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl --fail --silent --show-error --max-time 3 \
        "http://127.0.0.1:${APP_PORT}/health" \
        || exit 1

# \`tini\` as PID 1 → graceful SIGTERM propagation to uvicorn workers.
# \`uvicorn\` honours the same CLI flags regardless of worker count;
# M1 ships single-worker; scale-out is M4 territory.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--log-level", "info", \
     "--no-access-log"]
