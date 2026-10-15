# ADR-0001 选择 LangGraph 作为多 Agent 编排框架

- **Status**: Accepted
- **Date**: 2026-10-15
- **Deciders**: Architecture Team

## Context

deep-research v3 需要编排 4 个 Agent（Planner → Researcher → Writer → Critic），形成可观测、可恢复、可中断的 stateful 工作流。研究员节点会循环调用工具，可能 5–30 次，必须：
1. 在 Redis 中持久化 checkpoint，便于断网后从中断点继续；
2. 暴露 `before_node` / `after_node` 钩子，供 Langfuse OTel 打点；
3. 允许外部触发「人工审核 → 修改 state → 续跑」（interrupt / resume）；
4. 状态图本身可被代码审查（纯图结构，而非提示词黑盒）。

满足这些特性的时间预算 1 人月。

## Decision

采用 **LangGraph 1.2.15** + **LangChain 1.4.6** + **langchain-classic** 组合，**不**引入 `langchain-community`（v1 起 LangChain 已分层为 core / classic / community，独立模块会更轻更稳）。状态图用 `StateGraph[ResearchState, ..., ...]` 描述，节点显式声明读写 slot；Redis 用作 `Checkpointer`，key = `thread_id`。

## Alternatives

| 方案 | 取舍 |
| --- | --- |
| **CrewAI** | 角色化抽象对 v1 太重；Redis checkpoint 支持弱，需自实现；OTel hook 需要 monkey-patch。 |
| **AutoGen (Microsoft)** | 群聊式编排，循环次数不可控；researcher 节点每次重启会丢上下文；interrupt 模型与生产期望不符。 |
| **自研编排层（async 协程）** | 灵活度高但要重写：状态机、checkpoint、retry、observability。估计 3 人月，远超预算。 |
| **LangGraph（采纳）** | 见 Decision。 |

## Consequences

**正面**
- `langgraph.checkpoint.redis.RedisSaver` 直接复用既有 Redis 8.1.0，省基础设施。
- `interrupt_before` / `interrupt_after` 一行配置即可在 Critic 后挂审核，与 v1 后续多用户审核场景对齐。
- LangChain 5.x 的 `CallbackHandler` 自动桥接 Langfuse OTel，`score.*` 写入零代码。
- 图结构可视化导出 SVG，方便非工程师评审。

**负面**
- LangGraph 1.2 与 LangChain 1.x 之间仍有零星 breaking change（已在 `pyproject.toml` 用 `~=` 锁版本）。
- 嵌套图（subgraph）调试栈较深，需要 `langgraph dev` UI 辅助。

**回退成本**

若 LangGraph 路线失败，迁移到自研编排的成本约为 6 人周（替换 checkpoint / OTel / interrupt 三个子模块）。
