# research_backend

hochoy Deep Research Agent — backend (M1 mock echo service).

> **Spec**: `specs/001-m1-infra/spec.md` (FEATURE-001-m1-infra)
> **Owner**: Dev.cai.1 (Co-Owner for US-1 / 一键起服务栈)
> **Phase**: M1 — 基础设施脚手架

---

## M1 scope

This package owns the M1 mock service — a FastAPI application exposing a
single LangGraph echo node via SSE streaming. It does **not** contain
real Planner/Researcher/Writer/Critic agents (those land in M2+).

What lives here in M1:

| Path | Owner | Description |
|---|---|---|
| `app/main.py` | Dev.cai.1 | FastAPI app + lifespan + CORS + exception handlers |
| `app/config.py` | Dev.cai.1 | pydantic-settings (`.env` loader, constitution I validation) |
| `app/api/deps.py` | Dev.cai.1 | DI factories (`get_settings`, `health_snapshot`) |
| `app/observability/logging.py` | Dev.cai.1 | structlog JSON config (constitution VII fields) |
| `Dockerfile` | Dev.cai.1 | Python 3.12-slim multi-stage + healthcheck |
| `pyproject.toml` | Dev.cai.1 | uv-managed project, dev-deps, pytest/ruff/bandit/coverage |
| `tests/unit/` | Dev.cai.1 + Dev.cai.2 | Unit tests (red→green→refactor) |
| `tests/integration/` | Dev.cai.1 | Stack-wide smoke probes |

What other Co-Owners add in parallel (not modified by Dev.cai.1):

- `app/agents/echo.py`, `app/agents/base.py` — Dev.cai.2 (US-2)
- `app/graph/state.py`, `app/graph/graph.py` — Dev.cai.2 (US-2)
- `app/api/routes.py`, `app/api/schemas.py` — Dev.cai.2 (US-2)
- `app/db/*` — Dev.cai.2 (Phase 2 T019-T021)
- `app/observability/langfuse.py` — Dev.cai.2 (US-2)
- `app/auth/anonymous.py` — Dev.cai.4 (Phase 2 T022)
- `app/ratelimit/limiter.py` — Dev.cai.4 (Phase 2 T023)

---

## Quick start

```bash
# After `task dev:up` (Dev.cai.4 owns Taskfile.yml) brings the stack up:
curl http://localhost:8000/health   # → {"status": "ok"}
```

To run the backend **outside** docker-compose (dev mode):

```bash
cd research_backend
uv sync --dev                       # installs runtime + dev deps
cp .env.example .env                # then edit secrets (constitution I)
uv run uvicorn app.main:app --reload
```

---

## Tests

```bash
# Unit tests only (no docker-compose stack needed)
uv run pytest tests/unit/ -v

# Integration tests — require `task dev:up` first
uv run pytest tests/integration/ -v

# Coverage report (constitution III — key paths ≥ 80%)
uv run pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

Tests are split by critical-path so CI can enforce the 80% gate on the
four paths declared in `specs/001-m1-infra/spec.md §SC-006`:

- `tests/unit/test_main.py` — critical_path_1 (`/health` reachable)
- `tests/integration/test_dev_up.py` — critical_path_1 (`/health` latency)
- `tests/unit/test_config.py` — critical_path_3 (cookie + rate-limit config)
- `tests/unit/test_logging.py` — critical_path_4 (trace writes)

---

## Constitution alignment

| Principle | M1 landing in this package |
|---|---|
| I.  Security-First | `SettingsError` fails closed at startup; weak passwords rejected; CORS allow-list explicit; non-root container user |
| III. Test-First | 16 unit tests, coverage 85% (≥ 80% gate) |
| V.  One-Feature-Owner | `Owner: Dev.cai.1` declared in module docstrings |
| VI. API Contract | OpenAPI auto-published at `/openapi.json` and `/docs`; aligned with `specs/001-m1-infra/contracts/openapi.yaml` |
| VII. Observability | structlog emits JSON with all 8 mandated fields (`ts` / `level` / `service` / `trace_id` / `actor` / `event` / `latency_ms` / `error`); `X-Latency-MS` header on every response |
| VIII. Simplicity | No per-request DI churn (only `get_settings()` is cached); `lru_cache(maxsize=1)` on the health snapshot |

---

## File-by-file map

```
research_backend/
├── pyproject.toml                    # uv-managed project + dev-deps + pytest/coverage/bandit
├── Dockerfile                        # multi-stage Python 3.12-slim, non-root, healthcheck
├── conftest.py                       # pytest bootstrap (anyio backend)
├── app/
│   ├── __init__.py                   # package marker + __version__
│   ├── main.py                       # FastAPI app + lifespan + CORS + exception handlers
│   ├── config.py                     # pydantic-settings, constitution I fail-closed
│   ├── api/
│   │   ├── __init__.py
│   │   └── deps.py                   # DI: get_settings + health_snapshot
│   └── observability/
│       ├── __init__.py
│       └── logging.py                # structlog JSON w/ constitution VII fields
└── tests/
    ├── unit/
    │   ├── test_config.py            # T042 — Settings validation (constitution I)
    │   ├── test_main.py             # FastAPI shell + /health
    │   └── test_logging.py          # T026 — JSON schema compliance
```