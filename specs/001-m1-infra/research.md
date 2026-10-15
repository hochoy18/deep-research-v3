# Research Findings: FEATURE-001-m1-infra

> **Phase 0 Output** — `/speckit-plan` 阶段产出。
> 所有 spec 中的 [NEEDS CLARIFICATION] 已在 `/speckit-clarify` 阶段解决（5 个澄清见 spec.md `## Clarifications`）。
> 本文档聚焦 M1 阶段**关键技术决策**的调研、备选评估与 ADR 引用。

---

## R1: 单 LangGraph 节点的 echo 行为

- **Decision**: 单一 `EchoAgent` 节点；M1 阶段不实现 Planner / Researcher / Writer / Critic 4 Agent 编排
- **Rationale**:
  - spec Q1 澄清为「极简 echo」
  - constitution VIII 简洁优先
  - M2+ 引入真实 4 Agent（ADR-0001 选 LangGraph）
- **Alternatives considered**:
  - B. 单节点多状态（`thinking → researching → writing → done` 事件）— M1 价值低，UX 复杂度高
  - C. 4 节点占位 — M1 代码量翻倍，违反 YAGNI
- **ADR 引用**: [ADR-0001](../../docs/adr/0001-langgraph-over-crewai.md)

## R2: SSE 流式输出协议

- **Decision**: Server-Sent Events over HTTP/1.1；event types: `message` / `state_update` / `done` / `error`
- **Rationale**:
  - 浏览器原生 `EventSource` 支持，断线自动重连
  - 与 LangGraph `astream_events(version="v2")` 配合
  - M1 阶段单向流（user → agent），不需要 WebSocket 双工
- **Alternatives considered**:
  - WebSocket — 双工但 M1 不需要，复杂度高
  - HTTP chunked — 不可恢复，无标准 event type
- **ADR 引用**: [docs/architecture.md](../../docs/architecture.md) §2 组件全景明确 SSE 协议

## R3: 匿名 ID 持久化

- **Decision**: UUID v4 + httpOnly + Secure + SameSite=Lax cookie；TTL 30 天
- **Rationale**:
  - spec Q2 澄清
  - constitution I Security-First（防越权读 thread）
  - httpOnly 防 XSS、SameSite=Lax 防 CSRF、Secure 防明文传输
- **Alternatives considered**:
  - B. localStorage 存 user_id — 易被 XSS 读
  - C. URL token — 易泄露（referer / 分享链接）
- **ADR 引用**: [ADR-0009](../../docs/adr/0009-v1-no-auth.md) v1 no auth

## R4: 限流算法

- **Decision**: 滑动窗口 + `IP + 匿名 user_id` 二元组；阈值：每分 10 次 / 每小时 100 次
- **Rationale**:
  - spec Q3 澄清
  - 滑动窗口比 fixed window 平滑
  - Redis `INCR + EXPIRE` 原子实现（ADR-0003）
  - 二元组防止单 IP 多用户 / 单用户多 IP 绕过
- **Alternatives considered**:
  - 令牌桶 — 复杂度高，M1 不需要严格整形
  - 漏桶 — 同上
  - 仅 IP 限流 — 单一公司 NAT 后误伤
- **ADR 引用**: [ADR-0003](../../docs/adr/0003-postgres-milvus-minio.md) (Redis) / constitution I

## R5: 关键路径 4 条（test coverage scope）

- **Decision**: 路径 1 query→echo；路径 2 thread CRUD；路径 3 cookie + 限流；路径 4 trace 写入
- **Rationale**:
  - spec Q4 澄清
  - constitution III Test-First（关键路径 ≥ 80%）
  - 4 条路径覆盖 M1 全部业务逻辑，UI 装饰 / 镜像拉取 / 配置加载豁免
- **Alternatives considered**:
  - B. 全部后端路径 — M1 阶段无法收敛
  - C. 仅 2 条主路径 — 限流 / cookie 漏测，安全风险
- **ADR 引用**: spec SC-006

## R6: Owner 模式

- **Decision**: 1 主 Owner + 4 Co-Owner（按 user story 划分）
- **Rationale**:
  - spec Q5 澄清
  - constitution V One-Feature-Owner
  - 5 人 × 5 天 = 25 人天 vs 1 人单干 25 人天；4 人并行提速 4x
- **Alternatives considered**:
  - B. 5 个独立 feature — 协调成本高，违反「一个 milestone 一个 spec」原则
  - C. 单 Owner — 单点风险，Converge-Gate 签字负担集中
- **ADR 引用**: constitution V

## R7: M1 启动的本地服务列表（简化为最小集）

- **Decision**: docker-compose v1 仅启动 5 个：backend / frontend / postgres / redis / langfuse
- **Rationale**:
  - spec FR-005 要求"包含以下服务：数据库、缓存、可观测性平台、后端、前端"（5 个）
  - M1 阶段 mock 流式响应**不需要** Milvus（向量检索）和 MinIO（PDF 缓存）— 留给 M2/M3
  - milestones §M1 列出 7 个服务（含 milvus/minio）→ **本 plan 简化为 5 个最小集**
- **Alternatives considered**:
  - 启动全部 7 个服务 — 资源浪费（Milvus ~2GB 内存），与 constitution VIII 简洁优先冲突
- **ADR 引用**: [ADR-0003](../../docs/adr/0003-postgres-milvus-minio.md) M1 阶段部分启动
- **注意**: 此项需在 M1 kickoff 时与团队确认（若坚持 milestones 原文则改回 7 个）

## R8: 可观测性 Langfuse 版本

- **Decision**: Langfuse self-hosted v4.59.0 + Python SDK 5.0.1（OTel API）
- **Rationale**:
  - ADR-0006 显式选择 v5 + OTel API
  - v5 全面拥抱 OpenTelemetry，跨语言统一
- **Alternatives considered**:
  - v3 (legacy) — 已 EOL
  - SaaS — 数据合规与 ADR 冲突
- **ADR 引用**: [ADR-0006](../../docs/adr/0006-langfuse-v5-otel-api.md) / [docs/observability.md](../../docs/observability.md)

## R9: 后端框架 / 前端框架 / 部署

- **Decision**:
  - 后端：Python 3.12 + FastAPI + LangGraph + LangChain classic
  - 前端：Next.js 16 + React 19 + Tailwind v4 CSS-first + shadcn + Zustand + TanStack Query
  - 部署：docker-compose v1（5 个服务）+ Taskfile.yml + GitHub Actions CI
- **Rationale**:
  - ADR-0004 单 repo over monorepo（单仓平级目录 `research_backend/` `research_frontend/`）
  - ADR-0005 LangChain classic over community
  - ADR-0007 Tailwind v4 CSS-first（虽然有兼容风险，但 milestones §M1 关键风险有回退）
  - ADR-0008 Trunk-based + 短分支
  - ADR-0012 Python 3.12
- **ADR 引用**: ADR-0004 / 0005 / 0007 / 0008 / 0012

## R10: 监控 / CI 工具链

- **Decision**:
  - 代码风格：ruff（后端）+ eslint + prettier（前端）
  - 测试：pytest（后端）+ vitest（前端）
  - 覆盖率：coverage.py + 关键路径阈值 80%（constitution III）
  - Secret scan：gitleaks（pre-commit）
  - SAST：bandit（Python）+ ESLint security（前端）
  - SCA：pip-audit（后端）+ npm audit（前端）
  - 提交规范：commitlint + Conventional Commits（contributing.md）
- **Rationale**:
  - constitution I SAST/SCA 强制门禁
  - constitution III Test-First
  - 工具链成熟，零学习成本
- **ADR 引用**: constitution I / III / [docs/contributing.md](../../docs/contributing.md)

---

## 总结：M1 阶段技术决策清单

| # | 决策 | 选择 | 备选 | 引用 |
|---|---|---|---|---|
| R1 | Agent 编排深度 | 极简 echo 单节点 | 多状态 / 4 节点 | spec Q1 / ADR-0001 |
| R2 | 流式协议 | SSE | WebSocket / chunked | architecture §2 |
| R3 | 匿名 ID 持久化 | httpOnly cookie 30 天 | localStorage / URL | spec Q2 / ADR-0009 |
| R4 | 限流算法 | 滑动窗口 IP+user_id | 令牌桶 / 漏桶 | spec Q3 / ADR-0003 |
| R5 | 关键路径 | 4 条 | 全路径 / 2 条 | spec Q4 |
| R6 | Owner 模式 | 1 主 + 4 Co | 5 独立 / 单 Owner | spec Q5 / constitution V |
| R7 | 本地服务列表 | 5 个最小集 | 7 个全量 | spec FR-005 |
| R8 | Langfuse 版本 | v4.59.0 + SDK 5.0.1 | v3 / SaaS | ADR-0006 |
| R9 | 后端/前端/部署 | Python+FastAPI / Next.js+Tailwind v4 | （已固化为 ADR） | ADR-0004/0005/0007/0008/0012 |
| R10 | CI 工具链 | ruff+pytest+vitest+bandit+pip-audit | （constitution 强制） | constitution I/III |
