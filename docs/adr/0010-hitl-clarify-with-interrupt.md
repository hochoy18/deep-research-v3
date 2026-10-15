# ADR 0010: HITL Clarify 使用 LangGraph `interrupt()` 而非 fire-and-forget

- Status: Accepted
- Date: 2026-10-15
- Deciders: @cai.he, @hochoy
- References: LangChain Open Deep Research (`src/open_deep_research/clarify.py`),
  LangGraph docs `docs/docs/concepts/human_in_the_loop.md`

## Context

deep-research 的研究流需要在两个节点引入 Human-in-the-Loop：

1. **Clarify 节点**：用户提交模糊 query 时，LLM 生成 1-3 个澄清问题（"你更偏向
   技术方案还是市场分析？"），等待用户回答后再进入下一步。
2. **Topic List 审阅节点**：研究流产出"今日拟调研主题列表"后，等待用户确认或
   编辑，再进入搜索与撰写阶段。

参考实现是 LangChain 官方 `open_deep_research`（2025-09 版本），其 Clarify 节点
仅在 schema 层做了 `ClarifyWithUser` Pydantic 模型，由模型自行决定返回
"clarification" 或 "research brief"——本质是单轮、无持久化、无 UI 交互点，
完全 fire-and-forget。

我们需要在 LangGraph 1.2.15 上实现真正的"暂停 → UI 收集 → 恢复"流程。

### 方案 D1: Fire-and-forget（沿用 Open Deep Research）

LLM 直接在一次 invoke 内返回 clarification 或 answer；不暂停图运行。

### 方案 D2: LangGraph `interrupt()` + `Command(resume=...)`

在节点内调用 `interrupt(payload)`，LangGraph runtime 会：

1. 序列化图状态到 Postgres / Redis checkpointer；
2. 返回 `__interrupt__` 给调用方；
3. UI 调用 `graph.invoke(Command(resume=user_input), config)` 恢复；
4. 自动通过 OpenTelemetry 暴露 `interrupt` 与 `resume` span，便于 Langfuse 评测。

## Decision

**采用方案 D2：使用 LangGraph `interrupt()` 实现 Clarify 与 Topic Review 两个
HITL 节点。** 具体规则：

- Checkpointer 必须为 `PostgresSaver`（生产）或 `MemorySaver`（dev），配置在
  `langgraph.json` 的 `checkpointer` 字段；
- Interrupt payload 必须包含：
  - `kind`: `"clarify"` 或 `"topic_review"`；
  - `prompt`: string，UI 直接渲染；
  - `schema`: JSON Schema，UI 据此渲染表单；
  - `thread_id`: 来自 `config["configurable"]["thread_id"]`；
- 恢复时使用 `graph.invoke(Command(resume={...}), session_config)`，UA 不再
  走 LangGraph SDK 直连，而是通过 FastAPI 端点 `POST /threads/{id}/resume`
  转发；
- Open Deep Research 的 `ClarifyWithUser` schema 作为参考，但不再作为图的
  实际执行节点——升级为 `interrupt()` 的 `schema` payload。

## Consequences

正面：

- **生产级 HITL**：支持跨进程暂停与恢复（Postgres checkpointer），用户可在
  关闭浏览器后从历史 thread 恢复，无需重启研究流；
- **可观测性**：LangGraph runtime 自动为 `__interrupt__` 与 `Command(resume=...)`
  生成 OpenTelemetry span，Langfuse 自动捕获，LLM-as-judge 可基于完整 trace
  评测交互质量；
- **状态可重入**：Clarify 节点的草稿会保存在 checkpoint，UI 刷新不会丢失；
- **复用 Open Deep Research 的 schema 语义**：迁移路径平滑，prompt 模板可借鉴。

负面 / 约束：

- LangGraph 1.2.x 的 `interrupt()` 与部分中间件（如某些 auth handler）兼容性
  有 edge case，需在 E2E 测试覆盖；
- Postgres checkpointer 引入了 schema 迁移负担（`checkpoints`、`checkpoint_blobs`、
  `checkpoint_writes` 三张表），需要在 `langgraph/migrations/` 中维护；
- 与 Open Deep Reference 上游保持 drift，需自己维护 prompt 与 schema 演进，
  不再能 1-click 升级。

## Alternatives

- **Fire-and-forget（Open Deep Research 现状）**：实现成本最低，但缺少真正的
  用户交互点，无法满足产品对"审阅 / 编辑"的支持，pass。
- **自研轮询 + WebSocket**：需要在 FastAPI 外维护独立 session store，且无法复用
  LangGraph 的 checkpoint 与 OTel trace，等于重新发明轮子，pass。
- **LangServe 的 `playground` 组件**：早期 `langserve` 提供 React Playground 用于
  interrupt，但 LangServe 1.0 起已停止维护，且与 Next.js 16 集成需要额外
  customization，pass。