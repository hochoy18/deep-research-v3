"""FastAPI dependency injection (T018 — Dev.cai.1).

Spec: FEATURE-001-m1-infra — Task T018
Owner: Dev.cai.1

M1 keeps dependency wiring intentionally thin: only `/health` and the
config + settings singletons are exposed today. Future Co-Owners
(Dev.cai.2 for graph / DB, Dev.cai.4 for auth / ratelimit) will append
their own `Depends(...)` factories here without breaking existing ones.

Each provider is `@lru_cache`ed at the module level so request handlers
get the same instance across the lifetime of the process — important
for the Redis client pool and Langfuse singleton (constitution VIII:
simplicity, no per-request object churn).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings

# Re-export so routes can `from app.api.deps import get_settings` for symmetry.
__all__ = [
    "get_settings",
    "SettingsDep",
    "health_snapshot",
]


# ---------------------------------------------------------------------------
# Settings dependency
# ---------------------------------------------------------------------------

# `Annotated[Symbol, Depends(callable)]` is the FastAPI-idiomatic way to
# declare a request-scoped dependency. Routes do:
#
#     async def handler(settings: SettingsDep):
#         ...
#
SettingsDep = Annotated[Settings, Depends(get_settings)]


# ---------------------------------------------------------------------------
# Health snapshot (T016 wires this into /health)
# ---------------------------------------------------------------------------

# Placeholder for the M1 mock service — `/health` returns a hard-coded
# `ok` because the backend itself does not yet depend on Postgres /
# Redis / Langfuse (those are wired by T061-T067 in US2 and T019-T025
# in Phase 2 by Dev.cai.2/4).
#
# When real deps land, replace this with a per-component liveness dict:
#   {"postgres": "up", "redis": "up", "langfuse": "up"}
@lru_cache(maxsize=1)
def health_snapshot() -> dict[str, str]:
    """Return the current health snapshot.

    The snapshot is computed once per process (cached) because the
    underlying deps change at most on container restart. If liveness
    must be evaluated per-request, swap to an async function and drop
    the cache.
    """
    return {"status": "ok", "dependencies": "{}"}


def reset_health_cache() -> None:
    """Test hook — let unit tests force a fresh snapshot."""
    health_snapshot.cache_clear()