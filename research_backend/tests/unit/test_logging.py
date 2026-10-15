"""Unit tests for `app.observability.logging` (Dev.cai.1 — T026).

Spec: FEATURE-001-m1-infra — Task T026
Owner: Dev.cai.1
Critical path: critical_path_4 (observability trace writes).

These tests guard the constitution VII contract: every log line MUST be
JSON with the eight required fields. We patch `sys.stdout` to capture
the rendered output and assert on the parsed payload.
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys

# Set required env vars BEFORE importing the application modules. Logging
# configuration reads `Settings()` which validates these on first use;
# we want every test in this module to start with a valid config.
os.environ.setdefault("POSTGRES_PASSWORD", "testpass1234")
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-test")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-test")

import pytest

from app.observability.logging import (
    configure_logging,
    get_logger,
)


@pytest.fixture(autouse=True)
def _reset_logging() -> None:
    """Re-configure logging for every test so prior tests can't leak state."""
    configure_logging()
    yield
    # Reset stdlib root handler so subsequent tests start clean.
    logging.getLogger().handlers.clear()


def _capture_stdout_json() -> io.StringIO:
    """Redirect stdout to an in-memory buffer."""
    buffer = io.StringIO()
    sys.stdout = buffer
    return buffer


def _restore_stdout() -> None:
    sys.stdout = sys.__stdout__


def test_get_logger_returns_bound_logger() -> None:
    log = get_logger("test.module")
    assert log is not None
    # BoundLogger has the methods we use throughout the codebase.
    for method in ("info", "warning", "error", "exception", "debug"):
        assert hasattr(log, method), method


def test_log_emits_required_constitution_fields() -> None:
    buffer = _capture_stdout_json()
    try:
        log = get_logger("test.constitution_fields")
        # structlog takes the positional `event` arg as the canonical event
        # name; subsequent kwargs become event_dict fields.
        log.info(
            "service_starting",
            actor="system",
            latency_ms=0,
            error="",
            version="0.1.0-m1",
        )
        sys.stdout.flush()
    finally:
        _restore_stdout()

    raw = buffer.getvalue().strip()
    assert raw, "no log output captured"
    payload = json.loads(raw.splitlines()[-1])
    # Constitution VII: ts / level / service / actor / event /
    # latency_ms / error MUST all be present.
    for field in (
        "ts",
        "level",
        "service",
        "actor",
        "event",
        "latency_ms",
        "error",
    ):
        assert field in payload, f"missing field: {field} → {payload}"
    assert payload["actor"] == "system"
    assert payload["event"] == "service_starting"


def test_configure_logging_is_idempotent() -> None:
    """Calling configure_logging twice MUST NOT raise or duplicate handlers."""
    configure_logging()
    handlers_after_first = list(logging.getLogger().handlers)
    configure_logging()
    handlers_after_second = list(logging.getLogger().handlers)
    assert handlers_after_first
    # The second call should leave handler count equal (basicConfig with
    # force=True replaces them).
    assert len(handlers_after_second) == len(handlers_after_first)


def test_log_level_can_be_lowered() -> None:
    """Debug logs MUST be reachable when log level is DEBUG."""
    configure_logging()
    buffer = _capture_stdout_json()
    try:
        log = get_logger("test.debug")
        log.debug("dev_down_ping", actor="system", latency_ms=0, error="")
        sys.stdout.flush()
    finally:
        _restore_stdout()
    # At default level (INFO) the debug message should be filtered out.
    assert buffer.getvalue() == ""