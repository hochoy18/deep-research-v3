"""AgentState — LangGraph StateGraph 的 state schema。

M1 简化（spec Q1 极简 echo + tasks.md T029）：
    - 仅 3 个字段：messages / user_id / thread_id
    - total=False：所有字段可选，节点按需填充

M2+ 扩展（graph-design.md §1）：plan / sources / draft / critique / iteration /
metadata / config 等字段将分阶段加入；本文件作为契约，行为变更需向后兼容
（追加字段而非修改既有字段语义）。

说明：
    - `messages` 用 LangGraph 标准 `add_messages` reducer（追加语义）
    - `user_id` / `thread_id` 为直接覆盖语义
    - 字段命名遵循 data-model.md §2/§3（Snake case）
"""
from __future__ import annotations

from typing import Annotated, List

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """LangGraph 持久化的全部 state（M1 简化版）。

    - ``messages``: LangGraph 标准 messages reducer；节点 append 而非覆盖。
    - ``user_id``: 匿名 cookie user_id（UUID v4 字符串），用于 OTel 关联与越权校验。
    - ``thread_id``: LangGraph checkpoint key（Postgres threads.langgraph_thread_id）。
    """

    # === 标准消息历史（add_messages reducer） ===
    messages: Annotated[List[BaseMessage], add_messages]

    # === 会话身份（spec FR-011a 越权校验使用） ===
    user_id: str

    # === LangGraph checkpoint key + Postgres 关联 ===
    thread_id: str
