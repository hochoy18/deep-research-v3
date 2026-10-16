"""T031 routes 单测：路径 / 白名单 / 越权 / SSE 切片 / health。

不连真实 DB：用 fake_session 替换 get_session（覆盖整个 async ctx）。
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Any

import pytest
from app.api.schemas import SSEEventType

# === Fake DB session === #
# routes.py 中的 get_session 是 async ctx manager；用 stub 替换，
# 让 stream_echo_response 的 ORM 调用不抛异常。


class _FakeScalarResult:
    """``session.execute(stmt).scalar_one_or_none()`` 链的最小 stub。"""

    def __init__(self, value: Any = None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> Any:
        return self._value

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._value)


class _FakeScalars:
    def __init__(self, value: Any) -> None:
        # value 可为 None / 单个 ORM / list
        self._value = value

    def all(self) -> list[Any]:
        if self._value is None:
            return []
        if isinstance(self._value, list):
            return self._value
        return [self._value]


class _FakeSession:
    def __init__(self, row: Any = None) -> None:
        self._row = row
        self.added: list[Any] = []

    async def execute(self, stmt: Any) -> _FakeScalarResult:
        return _FakeScalarResult(self._row)

    def add(self, instance: Any) -> None:
        self.added.append(instance)

    async def flush(self) -> None: ...
    async def refresh(self, instance: Any) -> None: ...

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> Any:
        return False


def _fake_session_ctx_factory(row: Any = None):
    """直接返回 async ctx manager（不是 coroutine wrapping ctx）。"""

    @asynccontextmanager
    async def _ctx():
        sess = _FakeSession(row=row)
        yield sess

    return _ctx


@pytest.fixture
def fake_db(monkeypatch: pytest.MonkeyPatch):
    """替换 routes.get_session 为 fake。row 参数可控。"""

    def make_get_session(row: Any = None):
        return _fake_session_ctx_factory(row=row)

    # 默认：所有 session 调用返回 None row（即 thread 不存在 / message 不存在）
    monkeypatch.setattr("app.api.routes.get_session", make_get_session(row=None))
    return make_get_session


# === Uuid 校验 === #


class TestUuidValidation:
    def test_uuid_v4_helper_accepts_valid(self) -> None:
        from app.api.schemas import is_uuid_v4

        assert is_uuid_v4("550e8400-e29b-41d4-a716-446655440000") is True

    def test_uuid_v4_helper_rejects_invalid(self) -> None:
        from app.api.schemas import is_uuid_v4

        assert is_uuid_v4("not-a-uuid") is False


# === _stream_echo_response 行为契约 === #


class TestStreamEchoResponse:
    @pytest.mark.asyncio
    async def test_emits_state_update_message_done_sequence(
        self, fake_db: Any
    ) -> None:
        from app.api.routes import _stream_echo_response

        events = []
        async for ev in _stream_echo_response(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            user_id="550e8400-e29b-41d4-a716-446655440001",
            user_query="hi there",
            assistant_message_id=str(uuid.uuid4()),
        ):
            events.append(ev)

        event_types = [e["event"] for e in events]
        # 第一条必须 state_update (streaming)
        assert event_types[0] == SSEEventType.STATE_UPDATE.value
        # 中间至少有 1 个 message
        assert SSEEventType.MESSAGE.value in event_types
        # 倒数第二是 state_update complete
        assert event_types[-2] == SSEEventType.STATE_UPDATE.value
        # 最后一条 must be done
        assert event_types[-1] == SSEEventType.DONE.value

    @pytest.mark.asyncio
    async def test_message_count_matches_chunk_count(
        self, fake_db: Any
    ) -> None:
        from app.api.routes import _stream_echo_response

        query = "hello world"
        events = []
        async for ev in _stream_echo_response(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            user_id="550e8400-e29b-41d4-a716-446655440001",
            user_query=query,
            assistant_message_id=str(uuid.uuid4()),
        ):
            events.append(ev)

        message_events = [e for e in events if e["event"] == SSEEventType.MESSAGE.value]
        done_event = next(e for e in events if e["event"] == SSEEventType.DONE.value)

        assert done_event["data"]["total_chunks"] == len(message_events)
        rebuilt = "".join(e["data"]["chunk"] for e in message_events)
        assert rebuilt == query

    @pytest.mark.asyncio
    async def test_done_event_has_latency_ms_positive_int(
        self, fake_db: Any
    ) -> None:
        from app.api.routes import _stream_echo_response

        events = []
        async for ev in _stream_echo_response(
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            user_id="550e8400-e29b-41d4-a716-446655440001",
            user_query="x",
            assistant_message_id=str(uuid.uuid4()),
        ):
            events.append(ev)
        done = next(e for e in events if e["event"] == SSEEventType.DONE.value)
        assert isinstance(done["data"]["latency_ms"], int)
        assert done["data"]["latency_ms"] >= 0


# === /health route === #


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_returns_dict(self) -> None:
        from app.api.routes import health

        result = await health()
        assert result["status"] in {"ok", "degraded"}
        assert "langfuse" in result["dependencies"]
        assert "postgres" in result["dependencies"]
        assert "redis" in result["dependencies"]


# === Module-level 导出 === #


class TestRoutesModuleContract:
    def test_router_is_api_router(self) -> None:
        from app.api.routes import router
        from fastapi import APIRouter

        assert isinstance(router, APIRouter)

    def test_exports_get_compiled_graph(self) -> None:
        """dev.cai.1 的 deps.py 可从此导入；仅验证属性存在。"""
        from app.api import routes

        assert "get_compiled_graph" in routes.__all__
