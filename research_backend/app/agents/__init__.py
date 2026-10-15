"""Agent implementations.

M1 阶段：仅 `EchoAgent`（极简回显，constitution VIII 简洁优先）。
M2+ 阶段：在此模块新增 `Planner` / `Researcher` / `Writer` / `Critic`，
继承 `BaseAgent` 抽象类（ADR-0001）。
"""

from app.agents.base import BaseAgent
from app.agents.echo import EchoAgent, echo_node

__all__ = ["BaseAgent", "EchoAgent", "echo_node"]