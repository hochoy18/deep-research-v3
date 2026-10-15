"""BaseAgent 抽象类（M1 占位，M2+ 启用）。

设计契约来自 `docs/agent-design.md §2`：

- LangGraph node 接口 = `__call__(state) -> dict`
- 4 个 Agent（Planner / Researcher / Writer / Critic）共享模板方法
- 后续 @observe decorator 包裹入口，由 `app/observability/langfuse.py` 提供
  （constitution VII 可观测性默认，ADR-0006 Langfuse OTel API）

M1 阶段约束（constitution VIII 简洁优先）：
- 本模块仅定义抽象接口 + LangGraph 节点协议，不引入 LLM / Tools / Router
- 真实 LLM 调用在 M2+ 启用（spec Q1：M1 阶段极简 echo 单节点）
- 本文件保持**零外部依赖**（除 typing + typing_extensions），便于单元测试
  与未来 mock 子类快速落地
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from langchain_core.messages import BaseMessage

    from app.graph.state import AgentState

# 泛型参数：StateT 为 LangGraph state 类型，OutputT 为结构化输出类型
StateT = TypeVar("StateT", bound="AgentState")
OutputT = TypeVar("OutputT")


class BaseAgent(ABC, Generic[StateT, OutputT]):
    """4 个 Agent 的基类模板方法（ADR-0001 + agent-design §2）。

    M1 阶段：仅占位，不实例化；`EchoAgent` 不继承本类（极简场景独立实现）。
    M2+ 阶段：Planner / Researcher / Writer / Critic 继承本类，
    通过 LLM Router（`model_role`）解耦具体模型。

    Attributes
    ----------
    name : str
        Agent 名（如 `"planner"` / `"researcher"` / `"writer"` / `"critic"`），
        对应 Langfuse observation name（observability.md §1）。
    model_role : str
        LLM 路由角色（"planner" / "researcher" / "writer" / "critic"），
        Router 层按此查表决定具体模型（ADR-0011）。
    """

    #: Agent 名（LangGraph node name + Langfuse observation name）
    name: str = "base"
    #: LLM 路由角色（用于 Router 查表）
    model_role: str = "default"

    @abstractmethod
    async def build_user_prompt(self, state: StateT) -> list[BaseMessage]:
        """从 state 提取上下文 + 渲染 user prompt。

        子类必须实现。返回消息列表（System Message 在 `__call__` 统一拼装）。
        """
        raise NotImplementedError

    @abstractmethod
    async def post_process(
        self, output: OutputT, state: StateT
    ) -> dict[str, Any]:
        """解析后处理（更新 state slot）。

        子类必须实现。返回 state diff dict（LangGraph 自动 merge）。
        """
        raise NotImplementedError

    async def __call__(self, state: StateT) -> dict[str, Any]:
        """LangGraph node 协议：接 state → 调 LLM → 解析 → 返回 state diff。

        StateGraph 注册节点：`graph.add_node("planner", PlannerAgent())`。
        节点返回值是 partial state（仅填需要更新的 slot）。
        """
        user_prompt = await self.build_user_prompt(state)
        output: OutputT = await self._invoke_llm(user_prompt)
        return await self.post_process(output, state)

    @abstractmethod
    async def _invoke_llm(
        self, user_prompt: list[BaseMessage]
    ) -> OutputT:
        """调 LLM（with_structured_output 已绑 schema）。

        子类必须实现。M1 阶段由 mock 实现（EchoAgent 不走此路径）。
        """
        raise NotImplementedError


__all__ = ["BaseAgent"]