# ADR-0003 选择 Postgres + Milvus + MinIO 作为存储栈

- **Status**: Accepted
- **Date**: 2026-10-15
- **Deciders**: Architecture Team

## Context

deep-research v3 的存储需求包含三类：
1. **结构化数据** — LangGraph checkpoint、研究任务元数据、评估结果；
2. **向量检索** — Planner 把历史研究主题、HotpotQA 候选摘要 embed 进向量库，用于 query rewrite 与 cache；
3. **对象存储** — 网页快照、长报告 PDF 导出、评估数据集附件。

向量库与结构化库需要事务一致（删研究任务时，关联向量同步清理）。

## Decision

采用 **Postgres 16**（结构化）+ **Milvus 3.0.2**（向量，standalone 模式）+ **MinIO**（对象存储，复用 Milvus 3.0 自带的 MinIO 子模块）。三者通过 `docker-compose.yml` 编排在同一 Pod，统一阿里云 ACK 节点池。

向量同步机制采用 **outbox 模式**：业务事务先写 Postgres `outbox` 表，CDC worker 拉取后再写 Milvus，简单可靠。

## Alternatives

| 方案 | 取舍 |
| --- | --- |
| **Postgres + pgvector** | 单库部署最简，单机 > 100 万向量召回衰减明显；无独立水平扩展；与 LangGraph checkpoint 共库压力大。 |
| **Postgres + Qdrant** | Qdrant 性能优秀，但对象存储要额外起 MinIO；运维栈扩到 4 个组件。 |
| **SQLite + Chroma** | 适合 demo 单机；并发写易锁；零生产 SLA 承诺；与 LangGraph checkpoint 同样需要迁库。 |
| **Postgres + Milvus + MinIO（采纳）** | 见 Decision。 |

## Consequences

**正面**
- Milvus 3.0 standalone 自带 MinIO + etcd，单条 `docker compose up milvus` 即可启动；后续切 cluster 仅改 compose profile。
- 向量规模到 1 亿级仍可水平扩（已是 Milvus 验证过的生产指标）。
- Postgres 16 已用于 LangGraph Redis 之外的「业务事实源」，报告 ID、评测分数同库可 join。
- 检查点 TTL 7 天由 Postgres `pgAgent` 定期清理，无需 Redis 单独配 eviction。

**负面**
- Milvus 的 SDK 不在 `langchain-community`（即未纳入 classic 兼容列表），需自写 `BaseTool` 包装。
- etcd 增加一个组件，监控告警需加 etcd group 维度。

**回退成本**

迁到 Qdrant 仅需替换 vector store 适配器（约 1 人周），但 Milvus 已经满足上限指标，无明确收益。
