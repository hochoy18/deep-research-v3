"""LangGraph StateGraph（M1 极简 echo 单节点）。

M1 阶段（tasks.md T058）：
- 单 `echo` 节点 + START/END 直连
- RedisCheckpointSaver 接入（依赖 `app/api/deps.py` 注入的 saver；本模块不直连 Redis）
- thread_id 关联：`config["configurable"]["thread_id"]` 由 routes.py 注入

工厂设计（constitution VIII 简洁优先）：
- `build_echo_graph(*, checkpointer=None)` 暴露唯一编译入口
- checkpointer 由调用方注入（Dev.cai.1 负责的 `app/api/deps.py` 持有 Redis 连接）
- 未注入 checkpointer 时退化为内存模式（适合单测 / demo，无需 Redis）

M2+ 演进（docs/graph-design.md §2）：
- 节点扩展为 Planner / Researcher / Writer / Critic + clarify_with_user
- HITL interrupt（`interrupt_before=["clarify_with_user"]`）将在 graph.py 同模块添加
- Researcher 子图（§3）独立编译后挂到主图
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agents.echo import echo_node
from app.graph.state import AgentState

if TYPE_CHECKING:
    from langgraph.checkpoint.base import BaseCheckpointSaver


def build_echo_graph(
    *,
    checkpointer: BaseCheckpointSaver | None = None,
    node_name: str = "echo",
) -> CompiledStateGraph:
    """编译 M1 echo StateGraph。

    Parameters
    ----------
    checkpointer : BaseCheckpointSaver | None
        LangGraph checkpoint saver（生产环境 = RedisCheckpointSaver）；
        `None` 时使用 LangGraph 默认内存 MemorySaver，
        适用于单测与本地 demo（spec FR-008）。
    node_name : str
        echo 节点在 graph 中的注册名（默认 `"echo"`，对应
        Langfuse observation name `echo_agent` 见 observability.md §1）。

    Returns
    -------
    CompiledStateGraph
        编译后的图；调用方（routes.py）通过 `.ainvoke()` / `.astream()` 执行。

    Examples
    --------
    >>> from app.graph.graph import build_echo_graph
    >>> graph = build_echo_graph()  # 内存模式（单测）
    >>> result = await graph.ainvoke({"messages": [HumanMessage("hello")]})

    生产用法（Dev.cai.1 注入 saver）::

        # app/api/deps.py
        from langgraph.checkpoint.redis import RedisSaver
        saver = RedisSaver(redis_url=settings.REDIS_URL)
        saver.setup()
        graph = build_echo_graph(checkpointer=saver)
        app.state.graph = graph  # lifespan 阶段
    """
    builder: StateGraph = StateGraph(AgentState)

    # ---- 单 echo 节点 ----
    builder.add_node(node_name, echo_node)

    # ---- START → echo → END ----
    builder.add_edge(START, node_name)
    builder.add_edge(node_name, END)

    # ---- compile（注入 checkpointer）----
    return builder.compile(checkpointer=checkpointer)


__all__ = ["build_echo_graph"]