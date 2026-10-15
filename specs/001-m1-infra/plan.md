# Implementation Plan: FEATURE-001-m1-infra

**Branch**: `001-m1-infra` | **Date**: 2026-10-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-m1-infra/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

---

## Summary

M1 阶段目标：搭建 hochoy Deep Research Agent 的本地基础设施脚手架，端到端 mock 对话流（极简 echo 单节点）跑通，并落地 PR 全流程质量门禁（constitution I/III/IV）。

**技术方案**（基于 `research.md` R1-R10）：

- 后端：Python 3.12 + FastAPI + LangGraph（单 echo 节点）+ LangChain classic + Pydantic
- 前端：Next.js 16 + React 19 + Tailwind v4 CSS-first + shadcn + Zustand + TanStack Query
- 持久层：Postgres 16（thread / message）+ Redis 8（限流 + checkpoint）+ Langfuse self-hosted v4.59.0
- 部署：docker-compose v1（5 个最小集）+ Taskfile.yml + GitHub Actions CI
- 安全：UUID v4 匿名 cookie + 滑动窗口 IP+user_id 限流 + SAST/SCA 强制门禁
- 可观测性：Langfuse OTel API（v5 SDK）写 trace

**端到端 demo**：5 分钟内 `task dev:up` 启动 → 浏览器输入 query → mock 流式回显 → Langfuse UI 看到 trace。

---

## Technical Context

**Language/Version**: Python 3.12（后端，ADR-0012）+ TypeScript / Node.js 20+（前端）

**Primary Dependencies**:
- 后端：FastAPI 0.143+、LangGraph 1.2.15+、LangChain classic 0.3+（ADR-0005）、Pydantic 2.x、uvicorn
- 前端：Next.js 16、React 19、Tailwind v4（CSS-first，ADR-0007）、shadcn/ui、Zustand、TanStack Query
- 持久层：Postgres 16、Redis 8、Langfuse 4.59.0（self-hosted，ADR-0006）
- 工具链：Task 3.40+、ruff、pytest、vitest、ESLint、Prettier、commitlint、bandit、pip-audit、gitleaks

**Storage**: Postgres 16（thread / message 表）+ Redis 8（限流计数 / LangGraph checkpoint / 匿名 user_id 临时存储）+ Langfuse 持久化 trace

**Testing**: pytest（后端单元 + 集成）+ vitest（前端单元 + 组件）+ coverage.py（关键路径 ≥ 80%）

**Target Platform**: macOS 14+ / Linux 容器；Docker Desktop 4.25+；M1 阶段仅本地（生产部署在 M4）

**Project Type**: Web application（前端 + 后端，constitution VIII 模块化单体；ADR-0004 单 repo 平级目录）

**Performance Goals**（spec SC）：
- 启动时间 ≤ 5 分钟（SC-001）
- mock 流式响应 ≤ 3 秒完成（SC-002）
- 首字呈现延迟 ≤ 500ms（SC-003）
- CI pipeline ≤ 10 分钟（SC-005）

**Constraints**:
- 关键路径测试覆盖率 ≥ 80%（constitution III）
- 限流：每分 10 次 / 每小时 100 次（spec Q3）
- 匿名 user_id cookie TTL 30 天（spec Q2）
- 无鉴权（ADR-0009 v1 no auth）
- 数据保留 ≥ 7 天（constitution 数据保留）

**Scale/Scope**:
- M1 阶段：4 人并行 5 天（README §M1 sprint planning）
- 单机本地 demo，假设 1-3 个并发用户（不优化吞吐量）
- 后续 M2-M4 演进到多用户多模型

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 落地方式 | 状态 |
|---|---|---|
| **I. Security-First** | `.env.example` 启动校验（FR-004） + SAST/SCA 强制门禁（FR-014） + 匿名 cookie 防越权（FR-011a） + IP+user_id 限流（FR-011b） + 用户输入白名单（FR-022 / contracts/openapi.yaml MessageCreate） | ✅ PASS |
| **II. Spec-Traceable** | Spec ID `FEATURE-001-m1-infra`（FR-023） + PR 模板强制 `Spec:` 字段（FR-016） + CI 校验 | ✅ PASS |
| **III. Test-First (NON-NEGOTIABLE)** | 关键路径 4 条 ≥ 80% 覆盖率（FR-013 / SC-006 / spec Q4） + TDD 强制循环（constitution） + 集成测试覆盖 | ✅ PASS |
| **IV. Converge-Gate** | M1 集成日全绿后才归档（SC-009） + 4 个 Owner 签字 + checklist 16/16 通过 | ✅ PASS |
| **V. One-Feature-Owner** | 1 主 Owner + 4 Co-Owner 模式（spec Q5 / FR-022 / Owner 矩阵） | ✅ PASS（待 M1 kickoff 填姓名） |
| **VI. API Contract 优先** | OpenAPI 3.0.3 描述（`contracts/openapi.yaml`） + Pact 契约测试（M1 末 freeze，constitution VI） | ✅ PASS |
| **VII. 可观测性默认** | Langfuse OTel API（FR-009） + 结构化日志（M1 阶段简化为 stdout JSON） + Prometheus `/metrics`（M2+ 完善） | ✅ PASS（M1 部分） |
| **VIII. 简洁优先** | 模块化单体（ADR-0004） + 极简 echo 单节点（spec Q1） + 5 个最小服务（research.md R7） | ✅ PASS |

**Re-check after Phase 1 design**: 8 条原则全部 PASS，0 违例。

**性能与合规**（constitution 附加约束）：
- Performance Standards: P99 延迟 ≤ 300ms（mock 流式 ≤ 3s 总耗时） ✅
- 错误率 ≤ 0.1%：M1 阶段通过关键路径测试覆盖保证 ✅
- Compliance: GDPR / 等保 2.0 三级 — M1 阶段无欧盟数据；等保 2.0 由 M4 阶段审计

---

## Project Structure

### Documentation (this feature)

```text
specs/001-m1-infra/
├── plan.md              # 本文件（/speckit-plan command output）
├── research.md          # Phase 0 output（10 项技术决策）
├── data-model.md        # Phase 1 output（5 个 Key Entity 详细 schema）
├── quickstart.md        # Phase 1 output（端到端验证指南）
├── contracts/           # Phase 1 output
│   └── openapi.yaml     # M1 API 契约 v0.1.0-m1
├── spec.md              # /speckit-specify output（含 5 个 Clarifications）
├── checklists/
│   └── requirements.md  # spec 质量验证清单（16/16 PASS）
└── tasks.md             # Phase 2 output（/speckit-tasks - 下一阶段产出）
```

### Source Code (repository root)

```text
# 单 repo + 平级目录（ADR-0004 single-repo over monorepo）
deep-research/v3/
├── research_backend/            # 后端（Python 3.12 + FastAPI + LangGraph）
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifespan
│   │   ├── api/
│   │   │   ├── routes.py        # /threads /messages /health
│   │   │   ├── schemas.py       # Pydantic 模型
│   │   │   └── deps.py          # 依赖注入（DB / Redis / LangGraph）
│   │   ├── agents/
│   │   │   ├── base.py          # BaseAgent 抽象（M1 阶段仅占位，M2+ 启用）
│   │   │   └── echo.py          # M1 极简 echo 节点
│   │   ├── graph/
│   │   │   ├── state.py         # AgentState（M1 简化为单节点）
│   │   │   └── graph.py         # StateGraph compile + RedisCheckpointSaver
│   │   ├── auth/
│   │   │   └── anonymous.py     # 匿名 user_id 中间件（cookie 生成 + 校验）
│   │   ├── ratelimit/
│   │   │   └── limiter.py       # 滑动窗口 IP+user_id 限流
│   │   ├── observability/
│   │   │   └── langfuse.py      # Langfuse client + decorator
│   │   ├── db/
│   │   │   ├── models.py        # SQLAlchemy ORM（Thread / Message）
│   │   │   ├── session.py       # async session
│   │   │   └── migrations/      # alembic
│   │   └── config.py            # pydantic-settings
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/         # 关键路径 1-4 测试
│   │   └── conftest.py
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── .env.example
│   └── README.md
│
├── research_frontend/           # 前端（Next.js 16 + React 19 + Tailwind v4）
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx             # 对话主页
│   │   └── threads/
│   │       └── [thread_id]/page.tsx
│   ├── components/
│   │   ├── chat-thread.tsx      # 流式渲染组件
│   │   ├── message-input.tsx
│   │   ├── thread-list.tsx
│   │   └── error-boundary.tsx
│   ├── lib/
│   │   ├── api.ts               # fetch wrapper + SSE EventSource
│   │   ├── store.ts             # Zustand store
│   │   └── types.ts
│   ├── tests/
│   │   ├── unit/
│   │   └── e2e/                 # Playwright（M1 阶段可选）
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts       # Tailwind v4 CSS-first
│   ├── Dockerfile
│   ├── .env.example
│   └── README.md
│
├── deploy/
│   └── docker-compose.yml       # 5 个最小集（postgres / redis / langfuse / backend / frontend）
│
├── .github/
│   ├── workflows/
│   │   └── ci.yml               # PR pipeline（lint + test + build + SAST + SCA）
│   ├── CODEOWNERS               # 按目录划分 Owner
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md # 含 Spec: Owner: Converge: Tests: Observability: Security: 字段
│
├── Taskfile.yml                 # dev:up / dev:down / dev:logs / backend:test / frontend:dev
├── .pre-commit-config.yaml      # gitleaks + ruff + eslint + prettier + commitlint
├── .env.example
├── pyproject.toml               # workspace 元数据
├── docs/                        # 设计源头（已固化）
│   ├── architecture.md
│   ├── agent-design.md
│   ├── graph-design.md
│   ├── observability.md
│   ├── eval.md
│   ├── deployment.md
│   ├── contributing.md
│   ├── milestones.md
│   ├── adr/                     # 12 篇 ADR
│   ├── runbooks/                # 3 篇应急手册
│   └── SDD/                     # spec-kit SDD 流程文档
│
├── .specify/                    # spec-kit 工作目录
│   ├── memory/constitution.md   # 治理宪法 v1.1.0
│   ├── templates/               # 5 个模板
│   ├── scripts/bash/            # spec-kit 脚本
│   ├── feature.json             # 当前 feature 路径
│   └── specs/001-m1-infra/      # 本 spec 目录
│
└── specs/                       # spec-kit 流程产物（每个 milestone 一份）
    └── 001-m1-infra/
```

**Structure Decision**: 单 repo + 平级目录（`research_backend/` + `research_frontend/`），遵循 ADR-0004。不拆 monorepo workspace，简化 M1 阶段构建复杂度（constitution VIII 简洁优先）。

---

## Phase 0: Outline & Research

✅ **完成** — `research.md` 包含 10 项关键技术决策：

| # | 决策 | 引用 |
|---|---|---|
| R1 | 单 LangGraph 节点 echo 行为 | spec Q1 / ADR-0001 |
| R2 | SSE 流式输出协议 | architecture §2 |
| R3 | 匿名 ID 持久化（httpOnly cookie 30 天） | spec Q2 / ADR-0009 |
| R4 | 限流算法（滑动窗口 IP+user_id） | spec Q3 / ADR-0003 |
| R5 | 关键路径 4 条 | spec Q4 |
| R6 | Owner 模式（1 主 + 4 Co） | spec Q5 / constitution V |
| R7 | 本地服务列表（5 个最小集） | spec FR-005 |
| R8 | Langfuse v4.59.0 + OTel API | ADR-0006 |
| R9 | 后端 / 前端 / 部署栈 | ADR-0004/0005/0007/0008/0012 |
| R10 | CI 工具链 | constitution I/III / contributing.md |

**NEEDS CLARIFICATION 解决**: 0 个（5 个 clarifications 已在 `/speckit-clarify` 阶段全部整合）

---

## Phase 1: Design & Contracts

✅ **完成** — 3 个 artifacts：

### 1. `data-model.md` — 5 个 Key Entity 详细 schema

- **User**（匿名）：UUID v4 + Redis 临时存储（30 天 TTL）
- **Thread**：Postgres 持久化（含 user_id 索引）
- **Message**：Postgres 持久化（CASCADE 删除）
- **Trace**：Langfuse 持久化（与 thread_id 关联）
- **Service**：5 个 docker-compose 服务（postgres / redis / langfuse / backend / frontend）

详见 [data-model.md](./data-model.md)

### 2. `contracts/openapi.yaml` — M1 API 契约

- 8 个端点：health / threads CRUD / messages（含 SSE 流式）
- SSE event types: `message` / `state_update` / `done` / `error`
- 错误模型：401 / 403 / 404 / 413 / 422 / 429
- 鉴权：Cookie `user_id`（HttpOnly + Secure + SameSite=Lax）
- 版本：v0.1.0-m1（M1 集成日 freeze 为 baseline）

详见 [contracts/openapi.yaml](./contracts/openapi.yaml)

### 3. `quickstart.md` — 端到端验证指南

- §1 一键启动验证（SC-001）
- §2 端到端 mock 对话流验证（FR-006~011 / SC-002~004 / SC-010~012）
- §3 PR 质量门禁验证（FR-012~016 / SC-005~006 / SC-008）
- §4 关键路径 4 条覆盖验证（SC-006）
- §5 一键跑测试验证（FR-017~019）
- §6 集成日 Demo 脚本（SC-009）

详见 [quickstart.md](./quickstart.md)

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| （无） | — | — |

**0 个 Constitution 违例**。所有架构决策均与 constitution 8 原则对齐。

---

## ADR 引用总览

| ADR | 标题 | M1 阶段应用 |
|---|---|---|
| ADR-0001 | LangGraph over CrewAI | 后端编排框架 |
| ADR-0002 | Bailian web_search over Tavily | M2+（M1 不涉及） |
| ADR-0003 | postgres + milvus + minio | M1 简化为 5 服务最小集（research.md R7） |
| ADR-0004 | single-repo over monorepo | 单 repo + 平级目录 |
| ADR-0005 | LangChain classic over community | 后端 LLM 库 |
| ADR-0006 | Langfuse v5 OTel API | 可观测性 SDK |
| ADR-0007 | Tailwind v4 CSS-first | 前端样式 |
| ADR-0008 | Trunk-based over git-flow | 分支策略（contributing.md） |
| ADR-0009 | v1 no auth | 匿名 cookie 模式 |
| ADR-0010 | HITL clarify with interrupt | M2+（M1 单节点无 interrupt） |
| ADR-0011 | multi-model task routing | M2+（M1 不涉及） |
| ADR-0012 | Python 3.12 | 后端语言版本 |

---

## Owner 矩阵（constitution V / spec Q5）

| 角色 | 姓名 | 负责 User Story | 负责关键路径 |
|---|---|---|---|
| **主 Owner** | TBD | 全部 5 个 | 全部 4 条 |
| **Co-Owner #1** | TBD | US-1（一键起服务栈） | 路径 1（部分） |
| **Co-Owner #2** | TBD | US-2（端到端 mock 对话流） | 路径 1 + 路径 4 |
| **Co-Owner #3** | TBD | US-3（PR 质量门禁） | 路径 4（部分） |
| **Co-Owner #4** | TBD | US-4（单测一键跑）+ US-5（团队代码归属） | 路径 2 + 路径 3 |

> M1 kickoff 时由团队指定具体姓名并回填此表。

---

## 下一步

进入 `/speckit-tasks` 阶段：把 plan.md 拆解为可勾选 task 清单（按 user story + 关键路径组织，含 Owner + Day 1-5 维度）。

```bash
/speckit.tasks "基于 specs/001-m1-infra/plan.md + docs/milestones.md §M1 sprint planning（README）生成 tasks.md"
```

---

## Done When

- [x] Plan workflow executed and design artifacts generated
- [x] research.md（10 项决策）
- [x] data-model.md（5 个 Key Entity）
- [x] contracts/openapi.yaml（8 端点）
- [x] quickstart.md（4 条关键路径验证）
- [x] Extension hooks dispatched or skipped（extensions.yml 不存在，跳过）
- [x] Constitution Check 8 原则全 PASS，0 违例
- [x] Completion report to user
