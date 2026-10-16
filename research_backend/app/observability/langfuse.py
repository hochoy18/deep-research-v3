"""Langfuse v5 OTel 集成（ADR-0006）。

要点：
- ``get_client()`` 单例：通过 langfuse.get_client() 拿 v5 SDK 客户端
- ``@observe`` 装饰器：装饰 agent 节点 / 工具调用，自动建 span
- OTel 初始化：lifespan 中调用一次（在 app/main.py 由 Dev.cai.1 触发）

Dev.cai.1 拥有：
- ``app/observability/logging.py``（structlog）
- 在 app/main.py lifespan 中调用 configure()

本模块（Dev.cai.2 所有）：
- get_client()：让 routes / agents 拿到统一 client
- observe_agent()：在节点层统一装饰（M1 仅 echo_agent）
- start_observation/update_observation：标准化 trace 字段
"""
from __future__ import annotations

import os
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from langfuse import Langfuse, get_client as _langfuse_get_client, observe

F = TypeVar("F", bound=Callable[..., Any])


# === Langfuse Client 单例 === #


def get_client() -> Langfuse:
    """获取 Langfuse v5 客户端单例。

    - 默认从环境变量 LANGFUSE_HOST / LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
    - 缺失关键变量时 langfuse SDK 内部 raise；让上层显式处理
    """
    return _langfuse_get_client()


# === 装饰器（节点级 OTel span） === #


def observe_agent(name: str, as_type: str = "span") -> Callable[[F], F]:
    """统一节点装饰器：M1 极简封装。

    等价于 ``@observe(name="echo_agent", as_type="span")``，但承诺：
    - name 必传
    - as_type 默认 "span"（M2+ 接 LLM 时改为 "generation"）

    用法::

        @observe_agent(name="echo_agent")
        async def echo_node(state: AgentState) -> AgentState: ...
    """
    # 直接转发 langfuse.observe；保留单一入口以便后续注入（rate limit / filter）
    return observe(name=name, as_type=as_type)


# === 显式 OTel 控制路径（用于 routes 主动建 trace） === #


def start_observation(
    name: str,
    *,
    as_type: str = "span",
    input_data: Optional[dict] = None,
    metadata: Optional[dict] = None,
) -> Any:
    """显式开一个 observation（context manager 风格）。

    配合 ``with start_observation(...) as obs:`` 使用。
    返回的对象至少支持 ``update(output=...)``。
    """
    client = get_client()
    cm = client.start_as_current_observation(
        as_type=as_type,  # type: ignore[arg-type]
        name=name,
        input=input_data,
        metadata=metadata,
    )
    return cm


def update_observation(
    obs: Any,
    *,
    output: Any = None,
    metadata: Optional[dict] = None,
) -> None:
    """更新当前 observation（output / metadata）。"""
    if output is not None:
        obs.update(output=output)
    if metadata is not None:
        obs.update(metadata=metadata)


# === 配置校验（启动时） === #


def check_langfuse_configured() -> tuple[bool, str]:
    """检查 Langfuse 是否可以连通；用于 /health 端点 dependency 状态位。

    返回 (ok, message)；ok=True 表示 SDK 客户端 OK。
    注意：本函数不强制联网（M1 简化），仅检查 env 是否齐备。
    """
    required = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        return False, f"missing env: {','.join(missing)}"
    return True, "ok"


# === Re-exports === #

__all__ = [
    "get_client",
    "observe_agent",
    "observe",
    "start_observation",
    "update_observation",
    "check_langfuse_configured",
]
