# Spec-Kit SDD 整体开发流程

> 本文档是 spec-kit SDD（Specification-Driven Development）在 hochoy/deep-research 项目中的**端到端工作流**。
>
> 前置：docs/ 目录的设计文档 + `.specify/memory/constitution.md` v1.1.0 已就绪。
>
> 目标：把「设计源头」转化为「可执行的规范/计划/任务」并落地，每个 milestone（M1→M2→M3→M4）跑一遍。

---

## 0. 全局视图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Spec-Kit SDD 全流程                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  设计源头 (docs/)              规范层 (.specify/specs/)     执行层       │
│  ──────────────              ─────────────────────       ─────────     │
│  milestones.md          ┌─→ spec.md           ┌─→ GitHub Issues         │
│  architecture.md        │   (做什么/验收)      │   (Owner + 进度)        │
│  agent-design.md   ─────┤                     │                          │
│  graph-design.md        ├─→ plan.md           │                          │
│  12 篇 ADR              │   (怎么做/风险)      │                          │
│  observability.md       │                     │                          │
│  eval.md                └─→ tasks.md ─────────┴─→ code + PR + merge     │
│                              (谁/几天做完)                                │
│                                                                          │
│  治理层 (.specify/memory/constitution.md)                                │
│  ─────────────────────────────────────────                                │
│  8 大原则：Security-First / Spec-Traceable / Test-First / Converge-Gate │
│            One-Feature-Owner / API Contract / Observability / 简洁优先   │
└─────────────────────────────────────────────────────────────────────────┘
```

**核心原则**：docs/ 是设计源头（慢变量），`.specify/specs/` 是每个 milestone 的快照（中变量），GitHub Issues 是执行追踪（快变量）。三者各司其职，不混用。

---

## 1. 准备阶段（一次性）

### 1.1 检查清单

| 检查项 | 状态 | 说明 |
|---|---|---|
| `.specify/memory/constitution.md` v1.1.0 | ✅ 已就绪 | 8 大原则 + CI Gates |
| `.specify/templates/` 5 个模板 | ✅ 已就绪 | spec / plan / tasks / checklist / constitution |
| `docs/milestones.md` M1-M4 目标 + demo + 风险 | ✅ 已就绪 | Sprint planning 留白处 M2/M3/M4 启动前填 |
| `docs/architecture.md` | ✅ 已就绪 | 组件全景 + 数据流 |
| `docs/agent-design.md` | ✅ 已就绪 | 4 Agent 契约 |
| `docs/graph-design.md` | ✅ 已就绪 | LangGraph 编排 + HITL interrupt |
| `docs/adr/` 12 篇 | ✅ 已就绪 | 决策依据 |
| `docs/observability.md` / `eval.md` / `deployment.md` / `contributing.md` / `runbooks/` | ✅ 已就绪 | 横切关注点 |
| `docs/spec-kit-mapping.md` | ✅ 已就绪 | docs → spec-kit 阶段映射 |
| README.md §M1 sprint planning（Owner × Branch × 任务） | ✅ 已就绪 | M1 已拆好，M2/M3/M4 启动前补 |

### 1.2 初始化 Git 仓库配套

```bash
# 已存在
git init                        # ✅
git config user.name "cai_he"   # ✅

# 需要补
gh repo create                 # 创建 GitHub 远程仓库（如未创建）
gh auth login                  # 认证（如未认证）
```

### 1.3 一次性生成 GitHub 仓库基础设施

| 资产 | 工具/命令 | 时机 |
|---|---|---|
| `.github/CODEOWNERS` | 直接写入（按目录划分 Owner） | M1 启动前 |
| `.github/ISSUE_TEMPLATE/` | 复制 spec-kit 推荐的模板 | M1 启动前 |
| `.github/PULL_REQUEST_TEMPLATE.md` | 包含 `Spec:` `Owner:` 字段（constitution II 要求） | M1 启动前 |
| `Taskfile.yml` | `task dev:up` / `dev:down` / `backend:test` / `frontend:dev` | M1 Day 1 |
| `.pre-commit-config.yaml` | secret scan + ruff + eslint + prettier | M1 Day 2 |
| `.github/workflows/ci.yml` | PR pipeline（lint + test + build + SAST + SCA） | M1 Day 1 |

---

## 2. M1 启动（第一个 milestone，跑通全流程）

> M1 是试点：跑通 specify → plan → tasks → implement → archive 的完整闭环。

### 2.1 Step 1 — Specify（生成 spec.md）

**命令**：
```bash
/speckit.specify "基于 docs/milestones.md §M1 + docs/architecture.md §整体架构 生成 M1 端到端 spec.md，重点是 mock 对话流 + CI 基础设施"
```

**输入**：
- `docs/milestones.md` §M1 端到端 demo + 验收标准
- `docs/architecture.md` §2 组件全景
- 用户故事（user story 1: 对话流；user story 2: CI/单测；user story 3: Langfuse trace）

**产出**：`.specify/specs/001-m1-infra/spec.md`
- 1-3 个 user story（每个 P1 级别，可独立测试）
- 每个 user story 含 Acceptance Scenarios（Given/When/Then）
- Out of Scope（M2+ 明确剔除）
- Dependencies（已就绪的 docs/）

**下一步命令**（constitution II 要求 Spec ID 格式 `FEATURE-<编号>-<slug>`）：
```bash
/speckit.clarify   # AI 提问澄清模糊点（如 SSE 帧格式、Langfuse 是否双写 OTLP）
```

### 2.2 Step 2 — Plan（生成 plan.md）

**命令**：
```bash
/speckit.plan "基于 spec.md + docs/architecture.md + docs/agent-design.md + docs/graph-design.md + 12 篇 ADR 生成 plan.md"
```

**输入**：
- `spec.md`
- `docs/architecture.md`（组件 + 数据流）
- `docs/agent-design.md` §2 BaseAgent 抽象（M1 阶段占位即可）
- `docs/graph-design.md` §3 单 Agent trace（M1 不需要完整 4 Agent）
- 12 篇 ADR（尤其是 0004 单 repo / 0007 Tailwind v4 / 0008 Trunk-based / 0009 v1 无鉴权 / 0012 Python 3.12）

**产出**：`.specify/specs/001-m1-infra/plan.md`
- Technical Context（语言/框架/版本）
- Architecture Snapshot（引用 architecture.md）
- Implementation Strategy（接口契约先行 / 4 人并行 / 集成顺序）
- Risks & Mitigations（引用 milestones.md §M1 关键风险 + ADR-0007）
- Reference Docs（链接到 docs/）

**下一步命令**：
```bash
/speckit.checklist   # 生成验收清单（架构 / 性能 / 安全 / 可观测性 维度）
/speckit.analyze     # 跨 spec/plan/tasks 一致性检查（无 tasks.md 时会跳过）
```

### 2.3 Step 3 — Tasks（生成 tasks.md）

**命令**：
```bash
/speckit.tasks "基于 plan.md + docs/milestones.md §M1 sprint planning（Owner A/B/C/D Day 1-5）生成 tasks.md"
```

**输入**：
- `plan.md`
- `docs/milestones.md` §M1 sprint planning（已固化的 4 人 5 天表）
- `docs/contributing.md`（commit 规范 / PR 流程）

**产出**：`.specify/specs/001-m1-infra/tasks.md`
- 按 Task Group 1-N 拆分（每个 Group 对应一个 user story）
- 每个 Task 含：`[ ] T1.1 [Owner A] 描述 [Day 1]`
- Definition of Done（M1 全部勾完的判定条件）
- **关键**：tasks.md 不引入新架构决策，只把 plan.md 落地为可勾选清单

**可选命令**（constitution IV Converge-Gate）：
```bash
/speckit.converge    # 跨 spec/plan/tasks 收敛检查（一致性 + 完整性）
```

### 2.4 Step 4 — Sync to GitHub Issues

> spec-kit 是规范层，**Owner 分配 + 进度跟踪**走 GitHub Issues（constitution II + V 要求）。

**命令**：
```bash
/speckit.taskstoissues   # 自动把 tasks.md 转为 GitHub Issues
```

**产出**：GitHub 上 N 个 Issue，每个含：
- Title：`[M1] T1.1 FastAPI 骨架可启动`
- Body：复制自 tasks.md，含 Acceptance Criteria
- Label：`milestone:M1` `owner:A` `priority:P1` `spec:FEATURE-001-m1-infra`
- Milestone：`M1 - 基础设施`
- Assignee：Owner A

**手动作业**（如需手工补）：
```bash
gh issue create --title "[M1] T1.1 FastAPI 骨架可启动" \
  --body-file tasks/T1.1.md \
  --label "milestone:M1,owner:A,priority:P1" \
  --milestone "M1 - 基础设施" \
  --assignee A
```

### 2.5 Step 5 — Implement（按 tasks.md 顺序执行）

**命令**：
```bash
/speckit.implement
```

**执行模式**（不是 AI 全自动写，而是**人主导 + AI 辅助**）：

| 阶段 | 人的动作 | AI 的动作 |
|---|---|---|
| 接到 Issue | 拉分支 `git checkout -b feat/m1-t1.1-fastapi-skeleton` | — |
| 写代码 | 写关键逻辑、code review | 用 `/code-review` 辅助 review、`/tdd` 辅助写测试 |
| 提 PR | 推分支、开 PR（PR 模板必填 `Spec: FEATURE-001-m1-infra` `Owner: A`） | — |
| CI 跑 | 看 SAST/SCA/test 结果 | — |
| Merge | 通过后 squash merge 到 main | — |
| 勾 tasks.md | — | AI 助手提示勾掉 `T1.1 [x]` |
| 关 Issue | — | Merge 后自动关 |

**核心约束**（constitution 兜底）：
- 每个 PR MUST 引用 `Spec: FEATURE-001-...`（否则 Converge-Gate 阻断）
- 每个 PR MUST 通过 SAST + SCA（constitution I）
- 关键路径测试覆盖率 ≥ 80%（constitution III）
- 每个 Issue 有且仅有一个 Owner（constitution V）

### 2.6 Step 6 — Converge & Archive

**M1 集成日**（W1 Day 5）：
- [ ] 4 人分支全部 merge → main
- [ ] 跑端到端 demo（query → SSE → mock 流式响应 → Langfuse trace）
- [ ] 录 demo 视频 / 截图
- [ ] `task dev:up` 一键起所有服务
- [ ] CI pipeline 全绿
- [ ] README.md §M1 状态从「计划中」更新为「M1 ✅ 完成」

**归档命令**：
```bash
git tag m1-complete
# spec-kit 会自动把 .specify/specs/001-m1-infra/ 归档
# .specify/specs/ 下保留作为历史快照
```

---

## 3. M2/M3/M4 复用同样流程（模板化）

每个 milestone 的工作流**完全相同**，只是输入的 docs/ 章节不同：

| Milestone | Specify 输入 | Plan 输入 | Tasks 输入 | 关键交付 |
|---|---|---|---|---|
| **M1** 基础设施 | milestones §M1 + architecture §2 | architecture + agent-design §2 + graph-design §3 + ADR 0004/0007/0008/0009/0012 | milestones §M1 sprint planning（已就绪） | 骨架 + CI + Langfuse |
| **M2** 检索 | milestones §M2 + architecture §3 | agent-design §3.1/3.2 + graph-design §4 + ADR 0001/0002/0003/0005/0006/0010/0011 | milestones §M2 sprint planning（**M1 完成后 kickoff 填**） | Planner + Researcher + Plan/Sources 面板 |
| **M3** 写作 | milestones §M3 + architecture §4 | agent-design §3.3/3.4 + graph-design §5 + ADR 0010 | milestones §M3 sprint planning（**M2 完成后 kickoff 填**） | Writer + Critic + cite + 导出 + Draft 审阅 |
| **M4** 验收 | milestones §M4 + architecture §5 | eval.md + observability.md + deployment.md | milestones §M4 sprint planning（**M3 完成后 kickoff 填**） | Eval pipeline + CI/CD + 安全 + v1 demo |

**模板化命令**（以 M2 为例）：

```bash
# M2 启动前 1 天：先在 docs/milestones.md §M2 sprint planning 处填 Owner / Day 1-5
# 然后跑 spec-kit 全流程

/speckit.specify "基于 docs/milestones.md §M2 + docs/agent-design.md §3.1/3.2 + docs/graph-design.md §4 生成 M2 spec.md"
/speckit.clarify
/speckit.plan "基于 spec.md + docs/agent-design.md + docs/graph-design.md + ADR 0001/0002/0010/0011 生成 plan.md"
/speckit.checklist
/speckit.tasks "基于 plan.md + docs/milestones.md §M2 sprint planning 生成 tasks.md"
/speckit.analyze
/speckit.converge
/speckit.taskstoissues
/speckit.implement
```

**循环节奏**：M1 完成 → M2 kickoff（填 sprint planning）→ 跑 M2 完整流程 → M2 集成日 demo → M3 kickoff → ...

---

## 4. 关键节点（Converge-Gate 门禁）

> constitution IV 要求：每个 milestone 结束前必须通过 Converge-Gate。

| 节点 | 检查项 | 工具 | 通过条件 |
|---|---|---|---|
| **spec → plan** | spec.md 与 constitution 8 原则对齐 | `/speckit.analyze` | 0 个 BLOCKING |
| **plan → tasks** | tasks.md 不引入新架构决策 | `/speckit.analyze` | 0 个 BLOCKING |
| **tasks → implement** | tasks.md 全部勾掉、测试覆盖率 ≥ 80%、SAST/SCA 通过 | CI pipeline | 全绿 |
| **implement → archive** | 端到端 demo 跑通、README 更新、Converge-Gate 签字 | 团队 review | 4 个 Owner 全部 sign-off |
| **milestone N → milestone N+1** | N 的所有 Issue 关掉、`task dev:up` 仍可起、langfuse 历史 trace 可查 | 手测 + `/speckit.converge` | 全绿 |

---

## 5. 与外部工具的协作

| 工具 | 角色 | 与 SDD 流程的关系 |
|---|---|---|
| **GitHub Issues** | Issue 追踪（Owner / Label / Milestone） | `tasks.md → Issues`（via `/speckit.taskstoissues`） |
| **GitHub PRs** | Code review + CI 门禁 | 每个 PR 必填 `Spec:` 字段（constitution II） |
| **Langfuse** | Trace 观测（M1 接入 → M2+ 完善 score） | `observability.md` 是 plan 输入 |
| **HotpotQA 数据集** | M4 评估集 | `eval.md` 是 tasks 输入 |
| **Runbooks** | 应急手册（langfuse-down / llm-ratelimit / redis-eviction） | implement 阶段参考 |
| **Notion / 飞书**（可选） | 团队周报 / 决策记录 | 与 spec-kit 解耦，独立使用 |

---

## 6. 易踩的坑（避坑清单）

| 坑 | 后果 | 正确做法 |
|---|---|---|
| 跳过 `spec.md` 直接进 `tasks.md` | 实施时反复回炉改设计 | 严格按 4 阶段顺序跑 |
| `spec.md` 写太抽象（"做 deep research"） | `tasks.md` 拆不出来 | spec 必须是端到端 demo + 验收 |
| `tasks.md` 里写"Owner A Day 1 做什么" | spec-kit 是团队通用流程，Owner/工期会变 | Owner 走 GitHub Issues 分配，工期走 sprint planning |
| `plan.md` 里写"Dockerfile 路径" | 太细，应该在 implement 阶段 | plan 只到架构决策 + 关键风险 |
| PR 没填 `Spec:` 字段 | Converge-Gate 阻断合并 | PR 模板必填，CI 检查 |
| 测试覆盖率 < 80% | Test-First 原则违例 | PR 合并门槛硬卡 |
| 一个 PR 跨多个 user story | 难回滚、难 review | 一个 PR = 一个 user story 一个 Owner |
| M2/M3/M4 启动前没填 sprint planning | spec-kit 跑不出 Owner 维度 | kickoff 第一件事：填 milestones.md §对应 M sprint planning |
| 把 docs/ 文档塞进 `.specify/specs/` | 污染 spec-kit 流程产物 | docs/ 是设计源头（慢变量），.specify/specs/ 是流程快照（中变量） |

---

## 7. 一页纸总结（速查卡）

```
┌─ 准备（一次性）───────────────────────────────────────┐
│ 1. constitution ✅                                    │
│ 2. docs/ 设计文档 ✅                                  │
│ 3. README §M1 sprint planning ✅                       │
│ 4. GitHub 仓库 + CODEOWNERS + PR 模板                  │
└──────────────────────────────────────────────────────┘
                            ↓
┌─ 每个 Milestone（M1→M4）循环跑 ──────────────────────┐
│ 1. /speckit.specify    → spec.md （端到端 demo + 验收）│
│ 2. /speckit.clarify    → 澄清模糊点                  │
│ 3. /speckit.plan       → plan.md（架构 + 风险）        │
│ 4. /speckit.checklist  → 验收清单                    │
│ 5. /speckit.tasks      → tasks.md（可勾选 task）       │
│ 6. /speckit.analyze    → 一致性检查                  │
│ 7. /speckit.converge   → Converge-Gate 门禁          │
│ 8. /speckit.taskstoissues → GitHub Issues            │
│ 9. /speckit.implement  → 按 tasks 写代码 + PR + merge│
│ 10. 集成日 demo + 归档                                │
└──────────────────────────────────────────────────────┘
                            ↓
┌─ 横切关注点（每个 PR 都触发）─────────────────────────┐
│ • Spec 引用（PR 必填 Spec: FEATURE-xxx）              │
│ • SAST + SCA 扫描（constitution I）                   │
│ • 关键路径测试覆盖率 ≥ 80%（constitution III）         │
│ • Langfuse trace（M1 接入）                           │
│ • CODEOWNERS 审批                                     │
└──────────────────────────────────────────────────────┘
```

---

## 8. 相关文档

- [`spec-kit-mapping.md`](./spec-kit-mapping.md) — docs/ → spec-kit 阶段映射详解
- [`../milestones.md`](../milestones.md) — M1-M4 总目标 + 端到端 demo
- [`../architecture.md`](../architecture.md) — 整体架构
- [`../agent-design.md`](../agent-design.md) — 4 Agent 设计契约
- [`../graph-design.md`](../graph-design.md) — LangGraph 编排
- [`../adr/`](../adr/) — 12 篇决策记录
- [`../../.specify/memory/constitution.md`](../../.specify/memory/constitution.md) — 项目治理宪法 v1.1.0
- [`../../.specify/templates/`](../../.specify/templates/) — 5 个 spec-kit 模板
- [`../../README.md`](../../README.md) — M1 sprint planning（4 人 5 天表）
