"""BaseAgent：4 个 Agent 抽象模板。

M1 阶段（spec Q1 极简 echo）：
- 仅定义接口；不实现 4 个具体 Agent
- 提供统一的 ``run(state) -> state`` 调用约定
- M2+ 启动 Planner / Researcher / Writer / Critic / 等

why abstract class 而非 Protocol：
- LangGraph 节点签名直接继承 BaseAgent，子类即可被 graph 直接调用
- type-checker 能在 import 期报"未实现 run" 问题
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Agent 抽象基类（M1 占位）。

    设计意图（graph-design.md §1）：
        所有 agent 节点的入口签名都是 ``run(state) -> state``；
        状态 schema（M1 AgentState）从外面传进来，
        agent 改写 messages / user_id / thread_id 后返回。

    Attributes:
        name: 节点注册到 LangGraph 的名字；M1 唯一取 ``echo_agent``。
    """

    name: str = "base_agent"

    @abstractmethod
    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """处理 state；返回更新后的 state（部分更新）。"""
        raise NotImplementedError

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """让节点实例直接 callable，与 LangGraph 节点签名兼容。"""
        return self.run(state)
