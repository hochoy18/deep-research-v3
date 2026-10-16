"""LangGraph StateGraph compile（M1 mock echo）。

graphs.md / ADR-0001：LangGraph over CrewAI
- tasks.md T030 关键路径：「graph.py 必须能成功 import」

设计契约：
- 1 个节点：echo_node（@observe_agent 包装）
- START → echo → END
- 检查点：RedisCheckpointSaver（在 Redis URL 提供时启用）
- 不 require 真 Redis 即可 compile（M1 dev 模式允许无 saver → InMemorySaver）
- 提供 compile_graph() 工厂；模块级 _compiled_graph 懒初始化

M2+ 演进：消息中将拆 msg → planner → researcher → writer → critic，
        interrupt 与 conditional_edges 加入。

路径切分：
- Dev.cai.2 拥有 graph/state.py + graph.py
- Dev.cai.1 拥有 deps.py 中的 graph provider
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, Optional

from langgraph.graph import END, START, StateGraph

from app.agents.echo import echo_node
from app.graph.state import AgentState

logger = logging.getLogger(__name__)


# === RedisCheckpointSaver 工厂（依赖可降级） === #


def _build_checkpointer() -> Any:
    """构造 checkpointer；Redis URL 提供时启用 Redis，否则 InMemorySaver。

    返回对象必须有 .get / .put 接口（langgraph checkpoint 协议）。
    """
    redis_url = os.environ.get("REDIS_URL", "")
    if not redis_url:
        from langgraph.checkpoint.memory import InMemorySaver

        logger.warning(
            "REDIS_URL not set; using InMemorySaver (M1 dev fallback)"
        )
        return InMemorySaver()

    try:
        from langgraph.checkpoint.redis import RedisSaver

        return RedisSaver.from_conn_string(redis_url)
    except (ImportError, Exception) as exc:
        # 任何 import 或连接失败 → 降级
        logger.warning(
            "RedisSaver unavailable (%s); falling back to InMemorySaver", exc
        )
        from langgraph.checkpoint.memory import InMemorySaver

        return InMemorySaver()


# === Graph compile === #


def compile_graph(checkpointer: Optional[Any] = None) -> Any:
    """构造 M1 极简 graph 并 compile 返回。

    调用者可注入 checkpointer（生产环境用 RedisCheckpointSaver；test 用
    InMemorySaver）；不传则用 ``_build_checkpointer()``。

    Returns:
        CompiledStateGraph；可调用 ``.invoke(state, config=...)`` 或
        ``.stream(state, config=...)``。
    """
    graph = StateGraph(AgentState)

    # 节点注册
    graph.add_node("echo_agent", echo_node)

    # 边：START → echo_agent → END
    graph.add_edge(START, "echo_agent")
    graph.add_edge("echo_agent", END)

    return graph.compile(checkpointer=checkpointer)


@lru_cache(maxsize=1)
def get_compiled_graph() -> Any:
    """单例 compiled graph（首次 init 后稳定引用）。"""
    return compile_graph(_build_checkpointer())


def reset_compiled_graph_for_tests() -> None:
    """测试可调用：清 lru_cache，让下次 get_compiled_graph() 重新 init。"""
    get_compiled_graph.cache_clear()


__all__ = [
    "compile_graph",
    "get_compiled_graph",
    "reset_compiled_graph_for_tests",
]
