"""Agents 包（M1 mock echo 阶段）。

- BaseAgent：抽象模板方法骨架；M2+ 启动 4 个 agent（spec Q5）
- echo：M1 极简 echo 节点；tasks.md T028
"""
from app.agents.base import BaseAgent
from app.agents.echo import EchoAgent

__all__ = ["BaseAgent", "EchoAgent"]
