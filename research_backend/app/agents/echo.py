"""EchoAgent — M1 极简 mock 节点（spec Q1 澄清：单节点 echo）。

职责（spec FR-006 / FR-007）：
- 接 user query → 按 token 切分 → 流式回显（每 ~50ms 一片）
- 输出协议：SSEEvent dict（contracts/openapi.yaml §SSEEvent）
  - `event="message"` — 单个 token 切片（Markdown fragment）
  - `event="state_update"` — status 变化（streaming → complete）
  - `event="done"` — 流式结束（带 total_chunks / latency_ms）
  - `event="error"` — 错误（带 code / message）

模块结构（M1 简化，constitution VIII 简洁优先）：
1. `EchoAgent` — LangGraph node（`__call__(state) -> dict`）。
   调用 `stream_echo_response()` 收集完整 chunks 后写回 state。
   适用于 RedisCheckpointSaver 持久化场景（spec FR-008）。
2. `echo_node` — 别名，LangGraph `add_node("echo", echo_node)` 直接使用。
3. `stream_echo_response(query, *, message_id, ...)` — async generator，
   对外暴露 SSEEvent 流。routes.py 用 `StreamingResponse` 包装给前端
   （contracts/openapi.yaml §POST /threads/{id}/messages）。

> **不接 LLM**：M1 阶段 mock 行为 = 直接回显 query。M2+ 由真实 LLM 替换
> （research.md R1 + spec Q1 澄清：M1 不引入 4 Agent）。
> **不直接依赖 Langfuse**：本模块仅产出 stream API；
> `@observe` decorator 由 `app/observability/langfuse.py`（T059，Dev.cai.2 跨任务）
> 在外部 wrap。模块解耦便于单测（test_echo_agent.py T052 不需要 mock Langfuse）。
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage, HumanMessage

if TYPE_CHECKING:
    from langgraph.graph import StateGraph

    from app.graph.state import AgentState


logger = logging.getLogger(__name__)

#: 默认 chunk 间隔（毫秒）。spec FR-007 要求"每 ~50ms 一片"。
DEFAULT_CHUNK_INTERVAL_MS: int = 50

#: chunk 列表上限。spec FR-007 提及"10,000 字符 query"，按 1 字符 ≈ 1 chunk 上限 10000，
#: 留 20% buffer 防御 memory blow-up。
DEFAULT_MAX_CHUNKS: int = 12_000

#: Token 切分正则：以"非空白 + 可选尾部空白"为单位切分（保留 Markdown 格式）。
#: 例 `"  hello world!\n"` → `["  ", "hello ", "world!", "\n"]`。
_TOKEN_SPLIT_RE = re.compile(r"\s*\S+\s*|\s+")


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def _split_into_chunks(query: str, *, max_chunks: int = DEFAULT_MAX_CHUNKS) -> list[str]:
    """把 query 切分为 token 级 chunks。

    Parameters
    ----------
    query : str
        原始 query 字符串（已通过白名单校验，spec FR-022）。
    max_chunks : int
        防御上限，超出截断。

    Returns
    -------
    list[str]
        chunks 列表（保留空白与换行，便于 Markdown 块原样回显）。
    """
    if not query:
        return [""]
    chunks = _TOKEN_SPLIT_RE.findall(query)
    # findall 可能丢尾部（query 末尾无空白）—— 防御性追加。
    if query and not chunks:
        chunks = [query]
    if len(chunks) > max_chunks:
        logger.warning(
            "echo.truncate_too_many_chunks",
            extra={
                "event": "echo.truncate",
                "actor": "echo_agent",
                "chunks": len(chunks),
                "max_chunks": max_chunks,
            },
        )
        chunks = chunks[:max_chunks]
    return chunks


async def stream_echo_response(
    query: str,
    *,
    message_id: str | None = None,
    chunk_interval_ms: int = DEFAULT_CHUNK_INTERVAL_MS,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
) -> AsyncIterator[dict[str, Any]]:
    """SSE 流式 echo generator（routes.py 用 `StreamingResponse` 包装）。

    Yields
    ------
    dict[str, Any]
        SSEEvent dict（与 contracts/openapi.yaml §SSEEvent 一一对应）：
        - `{event: "message", data: {message_id, chunk, index}}`
        - `{event: "state_update", data: {message_id, status: "complete"}}`
        - `{event: "done", data: {message_id, total_chunks, latency_ms}}`
        - `{event: "error", data: {code, message}}`

    Notes
    -----
    - 不写 start_first（state_update streaming 已在 POST /messages 入口处的
      LangGraph callback 里写入；本 generator 只产 token chunks 与 terminal events）。
    - 异常捕获：任何 IO / 逻辑异常 → yield 一个 `error` event 然后退出
      （spec 错误模型，constitution I 安全优先）。
    - 间隔控制：可被测试覆盖（`chunk_interval_ms=0` 提速到极限）。
    """
    msg_id = message_id or str(uuid.uuid4())
    start = time.perf_counter()
    chunks = _split_into_chunks(query, max_chunks=max_chunks)
    interval_s = max(chunk_interval_ms, 0) / 1000.0

    try:
        for index, chunk in enumerate(chunks):
            yield {
                "event": "message",
                "data": {
                    "message_id": msg_id,
                    "chunk": chunk,
                    "index": index,
                },
            }
            if interval_s > 0:
                await asyncio.sleep(interval_s)
    except asyncio.CancelledError:
        # 客户端断开（spec Edge Case：浏览器刷新 / 断连）。
        logger.info(
            "echo.cancelled",
            extra={
                "event": "echo.cancelled",
                "actor": "echo_agent",
                "message_id": msg_id,
                "chunks_sent": 0,  # 此处无可见计数（partial state 在 node 层维护）
                "latency_ms": int((time.perf_counter() - start) * 1000),
            },
        )
        raise
    except Exception as exc:  # pragma: no cover - 异常兜底
        # 任何 LLM / 序列化 / 业务异常 → SSE error 事件（spec 错误模型）。
        logger.exception(
            "echo.error",
            extra={
                "event": "echo.error",
                "actor": "echo_agent",
                "message_id": msg_id,
                "error": str(exc),
            },
        )
        yield {
            "event": "error",
            "data": {
                "code": "internal_error",
                "message": "echo stream failed",
            },
        }
        return

    # 正常结束：state_update (complete) + done
    yield {
        "event": "state_update",
        "data": {"message_id": msg_id, "status": "complete"},
    }
    yield {
        "event": "done",
        "data": {
            "message_id": msg_id,
            "total_chunks": len(chunks),
            "latency_ms": int((time.perf_counter() - start) * 1000),
        },
    }


def _extract_query_from_state(state: AgentState) -> str:
    """从 LangGraph state 提取最新 HumanMessage 作为 echo 输入。

    state["messages"] 是 `add_messages` reducer 累积的 BaseMessage 列表。
    Echo 节点读最后一条 HumanMessage.content。
    """
    messages = state.get("messages") or []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = msg.content
            return content if isinstance(content, str) else str(content)
    # 无 HumanMessage（理论边界）：echo 一个固定 sentinel，便于 ops 排查。
    return ""


async def _build_assistant_message(query: str, *, message_id: str) -> AIMessage:
    """构造完整 AIMessage（一次性写入 state，供 RedisCheckpointSaver 持久化）。

    - 不用 streaming：M1 阶段 LangGraph checkpoint 仅持久化最终 state，
      streaming chunks 通过 SSE 单独推给浏览器（routes.py 路径）。
    - content = query 原样回显（spec Q1 澄清：极简 echo）。
    """
    return AIMessage(
        content=query,
        id=message_id,
        additional_kwargs={"echo": True, "node": "echo_agent"},
    )


class EchoAgent:
    """LangGraph node（M1 极简回显）。

    Usage::

        from app.graph.graph import build_echo_graph
        graph = build_echo_graph(checkpointer=redis_saver)
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content="hello")]},
            config={"configurable": {"thread_id": "..."}},
        )

    LangGraph node 协议 = `async __call__(state) -> dict`（state diff）。
    返回 partial state：`{"messages": [AIMessage(...)]}` 由 reducer 自动追加。
    """

    name = "echo_agent"
    model_role = "echo"  # 占位（无 LLM）

    def __init__(self, *, message_id: str | None = None) -> None:
        # message_id 可由调用方注入（routes.py 在持久化前已生成）；
        # 未传则由节点自生成（确保 Redis checkpoint 中 message_id 稳定）。
        self._message_id = message_id or str(uuid.uuid4())

    async def __call__(self, state: AgentState) -> dict[str, Any]:
        """LangGraph node 入口。

        1. 从 state 提取最新 HumanMessage
        2. 构造 AIMessage（content = query 原样回显）
        3. 返回 state diff：`{"messages": [AIMessage]}`
        """
        query = _extract_query_from_state(state)
        assistant_msg = await _build_assistant_message(
            query, message_id=self._message_id
        )
        # 同步 state slot：user_id / thread_id（让 RedisCheckpointSaver 一并持久化）
        return {
            "messages": [assistant_msg],
            "user_id": state.get("user_id"),
            "thread_id": state.get("thread_id"),
        }

    @property
    def message_id(self) -> str:
        return self._message_id


#: LangGraph 节点别名：`graph.add_node("echo", echo_node)` 即用。
#: 工厂函数形态便于 graph.py 在 compile 时实例化（RedisCheckpointSaver 同层接入）。
def echo_node(state: AgentState) -> dict[str, Any]:
    """同步版 LangGraph node（无 IO，纯回显，便于测试与最小依赖）。

    Notes
    - 选 sync 而非 async 是因为 Echo 不做 IO，async 包装在 M1 阶段属于
      "无收益的抽象"（constitution VIII 简洁优先）。
    - `EchoAgent.__call__` 是 async 版（保留 async 接口供未来嵌入 IO）。
      实际 graph compile 用此 sync 函数（性能更好）。
    """
    query = _extract_query_from_state(state)
    msg_id = str(uuid.uuid4())
    assistant_msg = AIMessage(
        content=query,
        id=msg_id,
        additional_kwargs={"echo": True, "node": "echo_agent"},
    )
    return {
        "messages": [assistant_msg],
        "user_id": state.get("user_id"),
        "thread_id": state.get("thread_id"),
    }


def install_echo_node(graph: StateGraph, *, node_name: str = "echo") -> None:
    """便捷安装函数：把 `echo_node` 注册到给定 StateGraph。

    graph.py 内部使用；外部代码可直接 `add_node`。
    """
    graph.add_node(node_name, echo_node)


__all__ = [
    "DEFAULT_CHUNK_INTERVAL_MS",
    "DEFAULT_MAX_CHUNKS",
    "EchoAgent",
    "echo_node",
    "install_echo_node",
    "stream_echo_response",
]