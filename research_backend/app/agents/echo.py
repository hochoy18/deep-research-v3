"""EchoAgent：M1 极简 mock 流式回显节点。

行为契约（spec Q1 极简 echo）：
- 输入：state 含 HumanMessage（user query）
- 输出：state 的 messages 末尾追加 AIMessage，按 word 切片
- tokens（chunks）：每 ~50ms yield 一次；用 ``time.sleep`` 模拟
- 不调真实 LLM；恒定回显 user query

实现要点：
- 节点注册为 LangGraph node（state.messages 自动走 add_messages reducer）
- @observe_agent 装饰器建 OTel span（默认 as_type='span'，M2+ 切到 'generation'）
- yield 切片通过外部 routes 异步消费；本节点返回更新后的 state（LangGraph
  节点是同步 returning — 由 routes 触发 stream 版本在 US2 完整阶段 T057 完成）

清理：
- delimiter = ``re.split(r'(\\s+)', text)``：保留空白为单独 token，
  切完后重新 join 不会丢空格。
"""
from __future__ import annotations

import re
import time
from typing import Any, Iterator

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.base import BaseAgent
from app.observability.langfuse import observe_agent


@observe_agent(name="echo_agent")
def echo_node(state: dict[str, Any]) -> dict[str, Any]:
    """LangGraph 节点函数（默认同步签名）。

    流程：
        1. 取最后一个 HumanMessage 作为 query
        2. 按 word 切片 + 拼成大写回显（mock）
        3. 同步状态 messages 末尾追加 1 个 AIMessage（完整内容，便于离线回放）
        4. 返回更新后 state

    实时流式切片（chunked yield）由 routes.py 的 SSE 层负责，
    本节点返回完整 AIMessage；后续 T057 US2 完整阶段会把 yield 上移到这里。
    """
    messages = list(state.get("messages", []))
    query = _latest_human_content(messages)

    if query is None:
        # 路径保护：未提供 user query 时不退化；返回无变更 state
        return state

    # Mock 行为：把 query 反向 + 大写 = "Mock Echo"
    mocked = query[::-1].upper()
    ai_msg = AIMessage(content=mocked)
    messages.append(ai_msg)

    return {
        **state,
        "messages": messages,
    }


class EchoAgent(BaseAgent):
    """Echo agent 实例（同步接口）。

    M1 阶段同时提供：
        - 类实例形式（echo.run(state)），便于 service / dep 注入引用
        - 函数形式（echo_node），便于 graph.compile 时作 node 注册
    """

    name = "echo_agent"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        return echo_node(state)


# === Pure helpers（routes 层 chunked stream 也复用）=== #


def chunk_text(text: str, *, max_chars_per_chunk: int = 8) -> Iterator[str]:
    """按 word 切片 + 单 chunk 不超过 max_chars_per_chunk。

    输出语义：
        - 每个 non-empty word 是最小切片（含前后空白）
        - 长 word 会被再切到不超过 max_chars_per_chunk
        - 始终至少 yield 1 个 chunk（即便 input 是空：yield ""）

    Examples:
        >>> list(chunk_text("hello world"))
        ['hello ', 'world']
        >>> list(chunk_text(""))
        ['']
    """
    if not text:
        yield ""
        return

    for word in re.split(r"(\s+)", text):
        if not word:
            continue
        # 长 word 二次切分
        while len(word) > max_chars_per_chunk:
            yield word[:max_chars_per_chunk]
            word = word[max_chars_per_chunk:]
        yield word


def sleep_for_chunk_simulated(chunk_idx: int, *, ms_per_chunk: int = 50) -> None:
    """Mock 模拟"每 ~50ms 一片"的延迟（仅测试/E2E 可关闭）。

    M1 测试不需要真实时间流；线上 US2 完整版改用 asyncio.sleep。
    """
    if ms_per_chunk <= 0:
        return
    time.sleep((ms_per_chunk / 1000.0))


def _latest_human_content(messages: list[Any]) -> str | None:
    """从 messages 末尾向前找第一条 HumanMessage 的 content。"""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = msg.content
            return content if isinstance(content, str) else None
    return None
