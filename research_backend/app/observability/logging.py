"""Structured logging (Constitution VII: Observability by Default).

Spec: FEATURE-001-m1-infra — Task T026
Owner: Dev.cai.1

Required JSON fields per constitution VII:
    ts, level, service, trace_id, actor, event, latency_ms, error

M1 simplification: write JSON to stdout (no remote sink yet). Langfuse
remains the source of truth for trace_id; this module is the source of
truth for everything else.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.config import get_settings

# Field names mandated by constitution VII. Keep in sync with observability.md.
REQUIRED_FIELDS: tuple[str, ...] = (
    "ts",
    "level",
    "service",
    "trace_id",
    "actor",
    "event",
    "latency_ms",
    "error",
)


def _add_service(service_name: str) -> Any:
    """Injector that stamps the service name once at configure time."""

    def _injector(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        event_dict.setdefault("service", service_name)
        # Constitution VII mandates `trace_id`; absent until Langfuse wires it.
        event_dict.setdefault("trace_id", "")
        return event_dict

    return _injector


def configure_logging() -> None:
    """Initialise structlog + stdlib logging to emit JSON to stdout.

    Idempotent — calling twice has no effect. Safe to invoke from both
    `main.py` lifespan and from unit tests.
    """
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Reset stdlib so re-configuration in tests takes effect cleanly.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            # Pin the timestamp key to ``ts`` to match the constitution's
            # required field name (structlog >= 24 default is "timestamp").
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            _add_service(settings.service_name),
            structlog.processors.StackInfoRenderer(),  # instance!
            structlog.processors.format_exc_info,  # already an instance
            structlog.processors.JSONRenderer(sort_keys=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger.

    Usage::

        log = get_logger(__name__)
        log.info("user_message_received", actor=user_id, latency_ms=elapsed)
    """
    return structlog.get_logger(name)  # type: ignore[return-value]


def assert_required_fields(payload: dict[str, Any]) -> None:
    """Development-time assertion that a log payload covers all constitution VII fields.

    Raises AssertionError if any required key is missing. Intended for use
    inside tests that capture log output (see tests/unit/test_logging.py
    added by Dev.cai.1 in US4).
    """
    missing = [f for f in REQUIRED_FIELDS if f not in payload]
    # `assert` is the right primitive here — this helper is a debug-only
    # contract check; the B101 bandit finding is a false positive.
    assert not missing, f"missing constitution VII fields: {missing}"  # nosec B101


__all__ = [
    "configure_logging",
    "get_logger",
    "assert_required_fields",
    "REQUIRED_FIELDS",
]
