"""Pytest bootstrap for the research_backend package.

`pytest.ini_options` (in pyproject.toml) already wires asyncio, testpaths,
and the critical-path markers. This file exists for fixtures that span
multiple test modules.

Note: We do NOT mutate environment variables here — tests should patch
env per-test via `monkeypatch.setenv(...)` so failures are reproducible.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Force anyio/pytest-asyncio to use asyncio only (no trio)."""
    return "asyncio"
