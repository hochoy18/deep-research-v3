# Spec-Kit 映射指南（Spec-Kit Mapping Guide）

> 本文档说明 **spec-kit SDD（Specification-Driven Development）** 流程如何消费本项目已固化的设计文档。M1 的 sprint planning 不会直接作为 spec-kit 输入，而是通过翻译映射进入各阶段。

---

## 1. Spec-Kit 是什么

Spec-Kit 是 GitHub 推出的规范驱动开发流程，核心思想：**先写规格，再写计划，再拆任务，最后实施**。它强制把"做什么 / 为什么 / 怎么做 / 验收"分离，避免直接动手写代码导致的设计漂移。

典型 4 个阶段：

```
specify → plan → tasks → implement
   ↓        ↓       ↓         ↓
 spec.md  plan.md  tasks.md   code
```

每个阶段是 GitHub 仓库根目录的 `.specify/` 下的一份 markdown，由 `/speckit.<stage>` 命令生成或迭代。

## 2. 已有文档与 Spec-Kit 阶段的映射

| 已有文档（已固化） | spec-kit 阶段 | 角色 |
|---|---|---|
| [`milestones.md`](./milestones.md) §M1 端到端 demo + 验收标准 | `spec.md` 输入 | **做什么 / 验收什么** |
| [`architecture.md`](./architecture.md) | `plan.md` 输入 | **整体架构 / 组件 / 数据流** |
| [`agent-design.md`](./agent-design.md) | `plan.md` 输入 | **4 Agent 设计契约** |
| [`graph-design.md`](./graph-design.md) | `plan.md` 输入 | **LangGraph 编排 / HITL interrupt** |
| 12 篇 [`adr/`](./adr/) | `plan.md` 输入 | **为什么这么做**（决策依据） |
| [`observability.md`](./observability.md) | `plan.md` + `tasks.md` 输入 | **Langfuse 集成 / score 维度** |
| [`eval.md`](./eval.md) | `tasks.md` 输入 | **评估数据集 / LLM-as-judge** |
| [`deployment.md`](./deployment.md) | `tasks.md` 输入 | **部署 / CI 流程** |
| [`contributing.md`](./contributing.md) | `tasks.md` 输入 | **commit 规范 / PR 流程** |
| [`milestones.md`](./milestones.md) §A.1 Owner × Branch × 任务 | `tasks.md` 输入 | **谁来做什么 / 几天做完** |
| [`runbooks/`](./runbooks/) | `implement` 阶段参考 | **应急手册** |

## 3. 每个阶段的输入 + 产出

### 3.1 `spec.md`（Specify 阶段）

**输入**：
- `milestones.md` §M1（或 §M2/M3/M4）端到端 demo + 验收标准
- 用户故事（user story 1, 2, 3...）

**产出**：`spec.md` 包含：

```markdown
# Spec: M1 - 基础设施

## User Story 1
As a 用户
I want to 输入 query 触发 mock 流式响应
So that 我能在浏览器看到对话流跑通

### Acceptance Criteria
- [ ] `task dev:up` 起所有服务
- [ ] 浏览器打开 http://localhost:3000 输入 query
- [ ] 后端 SSE 推送 mock 流式响应
- [ ] 前端 EventSource 接收并渲染 Markdown
- [ ] Langfuse UI 看到本次请求的 trace

## User Story 2
As a 开发者
I want to 用 `task backend:test` 跑单测
So that 我能验证 PR 通过

### Acceptance Criteria
- [ ] `task backend:test` 通过率 100%
- [ ] 单测覆盖率 ≥ 80%
- [ ] CI 自动跑（PR 触发）

## Out of Scope
- M2+ 的功能（Planner / Researcher / Writer / Critic / 评估 / 鉴权）
- 真实 LLM 接入（M1 用 mock）

## Dependencies
- 已有文档：`architecture.md` `agent-design.md` `graph-design.md` 12 篇 ADR
```

### 3.2 `plan.md`（Plan 阶段）

**输入**：
- `spec.md`
- `architecture.md`（整体架构）
- `agent-design.md` / `graph-design.md`（具体组件）
- 12 篇 ADR（决策依据）

**产出**：`plan.md` 包含：

```markdown
# Plan: M1 - 基础设施

## Technical Context
- Python 3.12 + FastAPI 0.143 + LangGraph 1.2.15
- Next.js 16 + React 19 + Tailwind v4 CSS-first
- Postgres + Redis + Langfuse self-hosted
- 单 repo + 平级目录 + Trunk-based（详见 ADR-0004 / ADR-0008）

## Architecture Snapshot
参见 architecture.md §2 组件全景

## Implementation Strategy
- 接口契约先行：A Day 1 末 freeze OpenAPI schema
- 4 人并行：A-Infra / B-Graph / C-Frontend / D-Deploy
- 集成顺序：D（CI）→ A 增量 → B → C → demo

## Risks & Mitigations
参见 milestones.md §M1 关键风险 + ADR-0007 Tailwind v4 兼容性

## Reference Docs
- [architecture.md](./architecture.md)
- [agent-design.md](./agent-design.md)
- [graph-design.md](./graph-design.md)
- [adr/0004-single-repo-over-monorepo.md](./adr/0004-single-repo-over-monorepo.md)
- [adr/0007-tailwind-v4-css-first.md](./adr/0007-tailwind-v4-css-first.md)
- [adr/0008-trunk-based-over-git-flow.md](./adr/0008-trunk-based-over-git-flow.md)
```

### 3.3 `tasks.md`（Tasks 阶段）

**输入**：
- `plan.md`
- `milestones.md` §A.1 Owner × Branch × 任务（重组为 user story 粒度）

**产出**：`tasks.md` 包含：

```markdown
# Tasks: M1 - 基础设施

## Task Group 1: FastAPI 骨架可启动（user story 1 后端部分）
- [ ] T1.1 [Owner A] FastAPI app + pydantic-settings + `/health` 路由 [Day 1]
- [ ] T1.2 [Owner A] Postgres + Redis 连接 + alembic 初始化 [Day 2]
- [ ] T1.3 [Owner A] Langfuse SDK 接入（OTel API）[Day 2]
- [ ] T1.4 [Owner A] Dockerfile + `.env.example` [Day 3]
- [ ] T1.5 [Owner A] `/threads` 假接口 + Pydantic schema [Day 3]
- [ ] T1.6 [Owner D] docker-compose v1（postgres + redis + langfuse + backend） [Day 2]
- [ ] T1.7 [Owner D] `task dev:up` 一键起 [Day 3]

## Task Group 2: LangGraph 可跑 trace（user story 1 后端编排部分）
- [ ] T2.1 [Owner B] AgentState schema + BaseAgent 抽象 [Day 1]
- [ ] T2.2 [Owner B] Planner Agent（mock LLM）[Day 2]
- [ ] T2.3 [Owner B] RedisCheckpointSaver 接入 [Day 2]
- [ ] T2.4 [Owner B] 第一条端到端 trace 跑通 [Day 3]
- [ ] T2.5 [Owner B] SSE 路由 + StreamingResponse [Day 4]

## Task Group 3: Next.js 对话流（user story 1 前端部分）
- [ ] T3.1 [Owner C] Next.js 16 + Tailwind v4 + shadcn 初始化 [Day 1]
- [ ] T3.2 [Owner C] EventSource 客户端 [Day 2]
- [ ] T3.3 [Owner C] Markdown 渲染（流式 token 拼接） [Day 3]
- [ ] T3.4 [Owner C] 假数据流测试（不依赖后端） [Day 3]
- [ ] T3.5 [Owner C] 接 SSE 真后端 [Day 4]

## Task Group 4: CI/CD + Code Quality（user story 2）
- [ ] T4.1 [Owner D] GitHub Actions PR pipeline（lint + test + build） [Day 1]
- [ ] T4.2 [Owner D] Taskfile.yml（dev:up / backend:test / frontend:dev） [Day 1]
- [ ] T4.3 [Owner D] pre-commit（commitlint + ruff + eslint + secret scan） [Day 2]
- [ ] T4.4 [Owner D] CODEOWNERS（按目录划分） [Day 3]

## Integration Day (Day 5)
- [ ] TI.1 merge 全部 → main
- [ ] TI.2 跑端到端 demo（query → SSE → draft）
- [ ] TI.3 修集成 bug
- [ ] TI.4 录 demo 视频 / 截图

## Definition of Done (M1)
- [ ] 所有 Task Group 1-4 勾完
- [ ] 集成日 demo 跑通
- [ ] `task dev:up` 一键起所有服务
- [ ] PR pipeline 跑通（lint + test + build）
- [ ] 单测覆盖率 ≥ 80%
- [ ] Langfuse UI 看到 mock trace
- [ ] README.md §M1 状态从"计划中"更新为"M1 ✅ 完成"
```

### 3.4 `implement`（Implement 阶段）

按 `tasks.md` 顺序执行，每完成一个 task 勾掉。

不需要 spec-kit 文档，但参考：
- `agent-design.md`（Agent 实现细节）
- `graph-design.md`（LangGraph 节点 / State 实现）
- `runbooks/`（应急）

## 4. M1 跑 Spec-Kit 的完整流程示例

```bash
# 假设项目根目录已有 docs/ 下全部文档

# Step 1: Specify
/speckit.specify "基于 docs/milestones.md §M1 + docs/architecture.md 生成 M1 spec.md"
# → 产出 .specify/specs/001-m1-infra/spec.md

# Step 2: Plan
/speckit.plan "基于 spec.md + docs/architecture.md + docs/agent-design.md + docs/graph-design.md + 12 篇 ADR 生成 plan.md"
# → 产出 .specify/specs/001-m1-infra/plan.md

# Step 3: Tasks
/speckit.tasks "基于 plan.md + docs/milestones.md §A.1 生成 tasks.md"
# → 产出 .specify/specs/001-m1-infra/tasks.md

# Step 4: Implement
/speckit.implement
# → 按 tasks.md 顺序实施；每完成一个 task 勾掉

# Step 5: Archive（spec-kit 自动归档到 .specify/specs/001-m1-infra/）
```

## 5. 关键原则

### 5.1 不要跳阶段

| 错误做法 | 后果 |
|---|---|
| 跳过 `spec.md` 直接进 `tasks.md` | 实施时反复回炉改设计 |
| 跳过 `plan.md` 直接进 `implement` | 架构决策随意变更，难追溯 |
| `spec.md` 太抽象（只写"做 deep research"） | `tasks.md` 拆不出来 |

### 5.2 不要让 sprint planning 直接污染 spec-kit

| 错误做法 | 后果 |
|---|---|
| 在 `tasks.md` 里写"Owner A Day 1 做什么" | spec-kit 是团队通用流程，Owner/工期会变 |
| 在 `plan.md` 里写"Dockerfile 路径" | 太细，应该在 implement 阶段 |

正确分工：
- `spec.md`：业务侧（用户视角的"做什么 / 验收"）
- `plan.md`：技术侧（架构决策 + 关键风险）
- `tasks.md`：实施侧（按 user story 组织的可勾选 task）

### 5.3 spec-kit 跑 M2/M3/M4 时

每个 milestone 都按相同流程跑一遍：

```bash
/speckit.specify "基于 docs/milestones.md §M2 端到端 demo + 验收标准 生成 spec.md"
/speckit.plan "基于 spec.md + agent-design.md §3.1/3.2 + graph-design.md §3 生成 plan.md"
/speckit.tasks "基于 plan.md + milestones.md §M2 sprint planning 占位 生成 tasks.md"
/speckit.implement
```

注意：M2/M3/M4 的 sprint planning（Owner / Day 1-5 细节）在其启动前 kickoff 时填入 `milestones.md` 对应章节的"Sprint planning"留白处，再喂给 spec-kit。

## 6. 与现有 `.specify/` 目录的关系

项目根目录已有 `.specify/` 目录（来自 spec-kit init）。它是 spec-kit 的工作目录：

```
.specify/
├── memory/           # spec-kit 跨会话记忆（constitution / 项目级约束）
├── scripts/          # spec-kit 提供的脚本
├── specs/            # 各 milestone 的 spec/plan/tasks
│   ├── 001-m1-infra/
│   │   ├── spec.md
│   │   ├── plan.md
│   │   └── tasks.md
│   ├── 002-m2-research/
│   └── ...
└── templates/        # spec.md / plan.md / tasks.md 模板
```

注意：
- **不要把我们的设计文档（docs/）放进 .specify/specs/** —— .specify/specs/ 只放 spec-kit 流程产物
- **`docs/` 是设计源头**，`.specify/specs/` 是 spec-kit 流程的快照
- spec-kit 跑完后会自动归档到 `.specify/specs/<milestone>/`

## 7. Spec-Kit 与传统 Sprint Planning 的关系

| 维度 | Spec-Kit | 传统 Sprint Planning |
|---|---|---|
| 时间单位 | Per user story / per milestone | Per sprint（2-4 周） |
| 颗粒度 | spec / plan / tasks 三层 | Backlog + Story + Task |
| 工具 | spec-kit CLI（`/speckit.*`） | Jira / Linear / 飞书任务 |
| 决策依据 | 设计文档（`docs/`） | Product Manager + 团队讨论 |

**本项目的工作流**：用 spec-kit 跑每个 milestone 的设计与任务拆解，用 GitHub Issues / Linear / 飞书任务 做 Owner 分配 + 进度跟踪（sprint planning 层）。

```
设计层 (docs/)          规范层 (.specify/specs/)        执行层 (GitHub Issues)
─────────────────      ────────────────────────       ─────────────────────
milestones.md          spec.md / plan.md / tasks.md    Issue #1: T1.1 FastAPI 骨架
architecture.md    →                                          Owner: A, Milestone: M1
agent-design.md                                              Status: In Progress
12 篇 ADR
```

## 8. 相关文档

- [`milestones.md`](./milestones.md) §M1 / §M2 / §M3 / §M4 + §附录 A
- [`architecture.md`](./architecture.md)
- [`agent-design.md`](./agent-design.md)
- [`graph-design.md`](./graph-design.md)
- [`contributing.md`](./contributing.md) §Git 工作流细节
- [spec-kit 官方文档](https://github.com/github/spec-kit)（外部参考）
