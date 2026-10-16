"""T025 langfuse 单测：get_client / observe_agent / 配置校验。

不连真实 Langfuse 服务（M1 简化）：验证 SDK 可被单例化、装饰器元数据通过、
配置缺失路径可观察。
"""
from __future__ import annotations

import asyncio
import os
from typing import Any

import pytest

from app.observability.langfuse import (
    check_langfuse_configured,
    get_client,
    observe_agent,
    update_observation,
)


class TestGetClient:
    def test_get_client_returns_langfuse_instance(self) -> None:
        c1 = get_client()
        assert c1.__class__.__module__.startswith("langfuse")

    def test_get_client_is_callable_repeatedly(self) -> None:
        """重复调用 get_client() 不抛异常（M1 不强制单例，但保证可调用）。"""
        c1 = get_client()
        c2 = get_client()
        assert c1 is not None
        assert c2 is not None


class TestObserveAgent:
    def test_observe_agent_is_a_decorator(self) -> None:
        @observe_agent(name="echo_agent")
        def sync_fn(x: int) -> int:
            return x + 1

        assert sync_fn(1) == 2

    def test_observe_agent_with_async_func(self) -> None:
        @observe_agent(name="echo_agent")
        async def async_fn(x: int) -> int:
            return x + 2

        out = asyncio.run(async_fn(3))
        assert out == 5


class TestCheckConfigured:
    def test_missing_required_env_returns_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
            monkeypatch.delenv(k, raising=False)
        ok, msg = check_langfuse_configured()
        assert ok is False
        assert "LANGFUSE_PUBLIC_KEY" in msg or "LANGFUSE_HOST" in msg

    def test_all_present_returns_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
        monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
        monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3001")
        ok, msg = check_langfuse_configured()
        assert ok is True
        assert msg == "ok"

    def test_partial_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")
        monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
        monkeypatch.setenv("LANGFUSE_HOST", "http://localhost:3001")
        ok, msg = check_langfuse_configured()
        assert ok is False
        assert "LANGFUSE_SECRET_KEY" in msg


class TestStartAndUpdateObservation:
    def test_start_observation_returns_context_manager(self) -> None:
        from app.observability.langfuse import start_observation

        cm = start_observation(name="unit_test", as_type="span")
        # langfuse start_as_current_observation 返回 context manager
        assert hasattr(cm, "__enter__") and hasattr(cm, "__exit__")

    def test_update_observation_skips_none(self) -> None:
        """output=None / metadata=None 时不调用 .update()。"""
        # mock observation
        class _Obs:
            calls: list[dict] = []

            def update(self, **kwargs: Any) -> None:
                self.calls.append(kwargs)

        obs = _Obs()
        update_observation(obs, output=None, metadata=None)
        assert obs.calls == []

    def test_update_observation_calls_update(self) -> None:
        class _Obs:
            calls: list[dict] = []

            def update(self, **kwargs: Any) -> None:
                self.calls.append(kwargs)

        obs = _Obs()
        update_observation(obs, output="hello", metadata={"k": 1})
        # 应该至少 1 次 update 调用（output + metadata 一次或两次，取决于实现）
        assert len(obs.calls) >= 1
        # 找到 output=hello 那次
        flat = {k: v for c in obs.calls for k, v in c.items()}
        assert flat.get("output") == "hello"
        assert flat.get("metadata") == {"k": 1}
