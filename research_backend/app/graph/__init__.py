"""LangGraph state machine.

M1 阶段：单 echo 节点 + RedisCheckpointSaver（spec FR-007）。
M2+ 阶段：扩展为 Planner / Researcher / Writer / Critic 4 节点 + HITL interrupt（ADR-0010）。

详见：
- `state` 模块：`AgentState` TypedDict schema
- `graph` 模块：`build_echo_graph` 工厂，compile StateGraph + 注入 checkpointer
"""

from app.graph.graph import build_echo_graph
from app.graph.state import AgentState

__all__ = ["AgentState", "build_echo_graph"]