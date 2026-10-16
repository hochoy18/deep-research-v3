"""T029 AgentState contract 单测：M1 简化版契约必须稳定。

后续节点 / graph 依赖本文件的字段；任何字段改名 / 改语义都会破坏依赖。
"""
from __future__ import annotations

from typing import Annotated, get_args, get_origin, get_type_hints

import pytest
from app.graph.state import AgentState
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.message import add_messages


class TestAgentStateContract:
    """AgentState M1 简化契约 —— spec Q1 / tasks.md T029 锁定。"""

    def test_m1_has_exactly_three_fields(self) -> None:
        """M1 仅 3 字段：messages / user_id / thread_id（M2+ 扩展不应修改本断言）。"""
        hints = get_type_hints(AgentState)
        assert set(hints.keys()) == {"messages", "user_id", "thread_id"}

    def test_total_false_allows_missing_fields(self) -> None:
        """total=False：所有字段可选，构造时可省略。"""
        state: AgentState = {}
        state["messages"] = []  # type: ignore[typeddict-unknown-key]
        assert state["messages"] == []  # type: ignore[typeddict-unknown-key]

    def test_messages_supports_append_reducer(self) -> None:
        """messages 字段必须携带 add_messages reducer（追加语义）。"""
        # `from __future__ import annotations` 让 __annotations__ 仍是字符串，
        # 用 get_type_hints 解析。
        hints = get_type_hints(AgentState, include_extras=True)
        ann = hints["messages"]
        assert get_origin(ann) is Annotated
        # get_args(Annotated[T, X]) -> (T, X); 其中 X 包含 reducer
        metadata = get_args(ann)[1:]
        assert add_messages in metadata

    def test_state_can_carry_user_and_thread_id(self) -> None:
        """user_id / thread_id 是覆盖语义，保存字符串身份。"""
        state: AgentState = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "thread_id": "550e8400-e29b-41d4-a716-446655440001",
            "messages": [HumanMessage(content="hi")],
        }
        assert state["user_id"].startswith("550e8400-")
        assert state["thread_id"].startswith("550e8400-")
        assert state["messages"][0].content == "hi"

    def test_state_messages_list_is_append_only_via_reducer(self) -> None:
        """通过 add_messages reducer 调一次，验证消息是被追加。"""
        existing = {"messages": [HumanMessage(content="a")]}
        result = add_messages(existing["messages"], AIMessage(content="b"))
        assert len(result) == 2
        assert result[0].content == "a"
        assert result[1].content == "b"


@pytest.mark.parametrize(
    "user_id,thread_id",
    [
        ("550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440001"),
        ("f47ac10b-58cc-4372-a567-0e02b2c3d479", "7c9e6679-7425-40de-944b-e07fc1f90ae7"),
    ],
)
def test_state_accepts_uuid_v4_strings(user_id: str, thread_id: str) -> None:
    state: AgentState = {"user_id": user_id, "thread_id": thread_id, "messages": []}
    assert state["user_id"] == user_id
    assert state["thread_id"] == thread_id
