"""T027 BaseAgent 抽象类单测：M1 占位契约。

覆盖：
- 不能直接实例化
- 子类必须实现 run() 否则仍是 abstract
- 默认 name 是 'base_agent'，子类可覆盖
- __call__ 走 run()
"""
from __future__ import annotations

import pytest

from app.agents.base import BaseAgent


class _Concrete(BaseAgent):
    name = "concrete_test"

    def run(self, state):
        return {"echoed": state.get("value", "")}


class _StillAbstract(BaseAgent):
    name = "still_abstract"


class TestBaseAgentContract:
    def test_cannot_instantiate_base_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseAgent()

    def test_subclass_without_run_is_still_abstract(self) -> None:
        with pytest.raises(TypeError):
            _StillAbstract()

    def test_concrete_subclass_is_callable(self) -> None:
        a = _Concrete()
        out = a({"value": "hi"})
        assert out == {"echoed": "hi"}

    def test_default_name_subclasses_can_override(self) -> None:
        assert BaseAgent.name == "base_agent"
        assert _Concrete.name == "concrete_test"

    def test_call_delegates_to_run(self) -> None:
        a = _Concrete()
        # 直接 callable 走 __call__ → run
        out = a({"value": "x"})
        assert out["echoed"] == "x"
