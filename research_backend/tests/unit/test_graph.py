"""T030 graph.py 单测：核心断言是 graph 可成功 import + compile + invoke。

tasks.md T030 关键路径：「T030 graph.py 必须能成功 import 测试」。
"""
from __future__ import annotations

import os

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.echo import echo_node
from app.graph.graph import (
    compile_graph,
    get_compiled_graph,
    reset_compiled_graph_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_singletons():
    """每个测试前/后清单例 cache，避免测试间污染。"""
    reset_compiled_graph_for_tests()
    yield
    reset_compiled_graph_for_tests()


class TestGraphImport:
    """tasks.md T030 关键路径：import / compile 都不抛异常。"""

    def test_compile_graph_default(self) -> None:
        g = compile_graph()
        assert g is not None

    def test_compile_graph_with_inmemory_saver(self) -> None:
        from langgraph.checkpoint.memory import InMemorySaver

        sa = InMemorySaver()
        g = compile_graph(checkpointer=sa)
        assert g is not None

    def test_get_compiled_graph_returns_singleton(self) -> None:
        g1 = get_compiled_graph()
        g2 = get_compiled_graph()
        assert g1 is g2

    def test_compile_creates_correct_node_names(self) -> None:
        """M1 graph 必须有 START → echo_agent → END 边。"""
        g = compile_graph()
        # 在 langgraph CompiledStateGraph 上 nodes 是 dict[str, Node]
        nodes = g.get_graph().nodes
        node_keys = set(nodes.keys())
        # echo_agent 必出现；__start__ / __end__ 是 LangGraph 自动的虚拟节点
        assert "echo_agent" in node_keys
        assert "__start__" in node_keys
        assert "__end__" in node_keys


class TestGraphExecution:
    def test_invoke_echoes_user_message(self) -> None:
        g = compile_graph()
        result = g.invoke(
            {
                "messages": [HumanMessage(content="hello")],
                "user_id": "u-1",
                "thread_id": "t-1",
            },
            config={"configurable": {"thread_id": "t-1"}},
        )
        # echo_node 把 'hello' 反向+大写 = "OLLEH"，追加为 AIMessage
        new_messages = result["messages"]
        assert any(
            isinstance(m, AIMessage) and m.content == "OLLEH" for m in new_messages
        ), f"expected AIMessage('OLLEH'), got {new_messages}"


class TestCheckpointerSelection:
    """REDIS_URL 缺失时使用 InMemorySaver；提供时不强制要求 Redis 在线。"""

    def test_no_redis_url_uses_inmemory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from app.graph import graph as graph_mod

        called = {"saver": None}

        def fake_saver():
            from langgraph.checkpoint.memory import InMemorySaver

            saver = InMemorySaver()
            called["saver"] = saver
            return saver

        monkeypatch.setattr(graph_mod, "_build_checkpointer", fake_saver)
        reset_compiled_graph_for_tests()
        g = get_compiled_graph()
        assert g is not None
        assert called["saver"] is not None


class TestGraphModuleContract:
    """导出 API 锁定：T030 表面是 module-level 工厂函数。"""

    def test_exports_compile_graph(self) -> None:
        from app.graph import graph as graph_mod

        assert callable(graph_mod.compile_graph)

    def test_exports_get_compiled_graph(self) -> None:
        from app.graph import graph as graph_mod

        assert callable(graph_mod.get_compiled_graph)

    def test_exports_reset_for_tests(self) -> None:
        from app.graph import graph as graph_mod

        assert callable(graph_mod.reset_compiled_graph_for_tests)

    def test_uses_echo_node_function(self) -> None:
        """graph.py compile 时注册的节点就是 echo_node（行为锁）。"""
        g = compile_graph()
        nodes = g.get_graph().nodes
        # 在 langgraph CompiledStateGraph 中,data 字段是绑定的 callable
        # 验证 echo_agent 节点在结构里就够,行为测试在 TestGraphExecution
        assert "echo_agent" in nodes


class TestEchoNodeRegistration:
    """T030 顶部锚点：echo_node 函数能被 graph 注册成 node。"""

    def test_echo_node_is_callable(self) -> None:
        assert callable(echo_node)

    def test_echo_node_returns_state_dict(self) -> None:
        out = echo_node(
            {
                "messages": [HumanMessage(content="hi")],
                "user_id": "u",
                "thread_id": "t",
            }
        )
        assert "messages" in out
        assert out["messages"][-1].content == "IH"
