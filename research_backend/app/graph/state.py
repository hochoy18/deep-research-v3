"""AgentState schema（LangGraph state machine 持久化字段）。

M1 简化（tasks.md T029）：`{ messages, user_id, thread_id }`。
M2+ 扩展（docs/graph-design.md §1）：追加 `query` / `research_brief` / `plan` /
`sources` / `draft` / `critique` / `iteration` / `metadata` / `config` 等 slot。

设计要点（constitution VIII 简洁优先）：
- `TypedDict, total=False`：所有字段可选，便于部分恢复（断点续跑）
- `messages` 用 LangGraph 标准 `add_messages` reducer：自动追加而非覆盖
- 其它字段默认覆盖语义（LangGraph 默认行为）
- `user_id` / `thread_id` 注入由 `app/api/routes.py` 写入 `config.configurable`
  后，echo 节点通过 `state["user_id"]` / `state["thread_id"]` 读出

> **M1 字段约定**（spec E-R01）：
> - `user_id` 来源：cookie `user_id`（HttpOnly + Secure + SameSite=Lax）
> - `thread_id` 来源：URL path param 或 LangGraph `config.thread_id`
> - `messages` 来源：LangGraph 自动累积 HumanMessage / AIMessage

> **M2+ 演进**：将追加 `plan` / `sources` / `draft` 等 slot，constitution III 关键路径
> 覆盖率门禁会自动跟进（graph-design.md §1 已列出 5 类 SubTask / SourceItem /
> CritiqueItem TypedDict）。
"""

from __future__ import annotations

from typing import Annotated, TYPE_CHECKING

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    """LangGraph 持久化的全部 state（M1 极简版）。

    `total=False` 让所有字段可选；M1 阶段仅 `messages` / `user_id` / `thread_id`
    三字段使用，其余字段（M2+ 引入）保持 None 即可。

    Fields
    ------
    messages : list[BaseMessage]
        对话消息历史。`add_messages` reducer 自动追加而非覆盖。
        Echo 节点读取最后一条 HumanMessage 作为输入 query。
    user_id : str
        匿名 UUID v4（来自 cookie）。用于：(a) trace 关联 Langfuse；
        (b) 越权校验（data-model.md 实体间约束）。
    thread_id : str
        LangGraph checkpoint key（与 Thread 实体的 thread_id 主键一致）。
        RedisCheckpointSaver 用此 key 存取 state 快照。
    """

    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    thread_id: str


__all__ = ["AgentState"]