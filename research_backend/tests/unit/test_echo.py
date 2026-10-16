"""T028 EchoAgent 单测：mock 回显 + 切片行为。

覆盖（spec Q1 极简 echo + tasks.md T052）：
- chunk_text 边界条件
- echo_node 把 HumanMessage 转为反向 + 大写 AIMessage
- 空 query → state 原样
- 多 HumanMessage 选最后一个
"""
from __future__ import annotations

from app.agents.echo import (
    EchoAgent,
    chunk_text,
    echo_node,
)
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# === chunk_text 行为 === #


class TestChunkText:
    def test_empty_yields_empty_chunk(self) -> None:
        assert list(chunk_text("")) == [""]

    def test_single_word_no_whitespace(self) -> None:
        assert list(chunk_text("hello")) == ["hello"]

    def test_two_words_with_space(self) -> None:
        """默认 max_chars_per_chunk=8，能装下 hello 与 world。"""
        chunks = list(chunk_text("hello world"))
        # re.split(r'(\s+)', 'hello world') -> ['hello', ' ', 'world']
        # 过滤掉空字符串 → ["hello", " ", "world"]
        assert chunks == ["hello", " ", "world"]

    def test_long_word_split_into_chunks(self) -> None:
        long_word = "a" * 20
        chunks = list(chunk_text(long_word, max_chars_per_chunk=8))
        assert chunks == ["a" * 8, "a" * 8, "a" * 4]

    def test_chunks_join_preserves_text(self) -> None:
        """切片后再 join，文本应等于原始（不含额外空白）。"""
        original = "The quick brown fox jumps over the lazy dog"
        assert "".join(chunk_text(original)) == original

    def test_cjk_text_chunks(self) -> None:
        """中文（CJK Unified Ideographs）按字符切片。"""
        # 限制 chunk size 让其能触发二次切分
        chunks = list(chunk_text("你好世界你好", max_chars_per_chunk=3))
        joined = "".join(chunks)
        assert joined == "你好世界你好"
        # 至少 2 个 chunk
        assert len(chunks) >= 2


# === echo_node 行为 === #


class TestEchoNode:
    def test_append_ai_message_reversed_upper(self) -> None:
        state = {
            "messages": [HumanMessage(content="hello")],
            "user_id": "u-1",
            "thread_id": "t-1",
        }
        out = echo_node(state)
        msgs = out["messages"]
        assert len(msgs) == 2
        assert isinstance(msgs[1], AIMessage)
        assert msgs[1].content == "OLLEH"  # hello 反向+大写

    def test_empty_messages_returns_state_unchanged(self) -> None:
        """无 HumanMessage 不退化；返回 state 原样。"""
        state = {"messages": [], "user_id": "u-1", "thread_id": "t-1"}
        out = echo_node(state)
        assert out is state or out["messages"] == []

    def test_picks_latest_human_message(self) -> None:
        """取最新 HumanMessage，前面有 system / user 都不影响。"""
        state = {
            "messages": [
                SystemMessage(content="system"),
                HumanMessage(content="first"),
                HumanMessage(content="second"),
            ],
            "user_id": "u-1",
            "thread_id": "t-1",
        }
        out = echo_node(state)
        # "second"[::-1].upper() == "DNOCES"
        new_messages = out["messages"]
        assert new_messages[-1].content == "DNOCES"

    def test_preserves_user_and_thread_id(self) -> None:
        """user_id / thread_id 在 state 中保留。"""
        state = {
            "messages": [HumanMessage(content="x")],
            "user_id": "u-99",
            "thread_id": "t-99",
        }
        out = echo_node(state)
        assert out["user_id"] == "u-99"
        assert out["thread_id"] == "t-99"


class TestEchoAgentClass:
    """EchoAgent 是 BaseAgent 子类（与 LangGraph 节点签名一致）。"""

    def test_class_is_base_agent(self) -> None:
        from app.agents.base import BaseAgent

        assert issubclass(EchoAgent, BaseAgent)

    def test_name_is_echo_agent(self) -> None:
        assert EchoAgent.name == "echo_agent"

    def test_run_delegates_to_node(self) -> None:
        a = EchoAgent()
        out = a.run(
            {"messages": [HumanMessage(content="hi")], "user_id": "u", "thread_id": "t"}
        )
        # hi 反向大写 = "IH"
        assert out["messages"][-1].content == "IH"
