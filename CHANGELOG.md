# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.0.0-M1] - 2026-10-16

### M1 里程碑：脚手架完成（FEATURE-001-m1-infra）

> **W1 / 端到端 demo**：`task dev:up` 一键起 5 服务 → 浏览器输入 query → 后端 mock SSE 流式响应 → 前端 Markdown 渲染 → Langfuse UI 看到 trace

### Added

#### 后端（research_backend/, FastAPI + LangGraph + LangChain classic）
- `pyproject.toml` (Python 3.12, uv-managed, PEP 517 hatchling)
- `Dockerfile` (multi-stage, non-root, healthcheck)
- `.env.example` (Postgres / Redis / Langfuse / cookie key / ratelimit 阈值)
- **DB 层** (US-2)：`app/db/models.py` SQLAlchemy 2.x async ORM (Thread + Message) + `app/db/session.py` async engine + `app/db/migrations/` Alembic 初始化 + 第一个 migration
- **API 层** (US-2)：`app/api/schemas.py` Pydantic 模型 (Thread/Message/SSEEvent/Error) + `app/api/routes.py` 路由 (/health, /threads, /threads/{id}, /threads/{id}/messages SSE)
- **Graph 层** (US-2)：`app/graph/state.py` AgentState (M1 简化版) + `app/graph/graph.py` StateGraph compile (单 echo + RedisCheckpointSaver)
- **Agent 层** (US-2)：`app/agents/base.py` BaseAgent 抽象类 + `app/agents/echo.py` EchoAgent (M1 极简 mock)
- **Observability** (US-2)：`app/observability/langfuse.py` Langfuse v3 OTel 集成
- **测试**：8 个 unit test (`test_base_agent / test_db_models / test_db_session / test_echo / test_graph / test_langfuse / test_routes_helpers / test_schemas`)

#### 前端（research_frontend/, Next.js 16 + React 19 + Tailwind v4）
- `package.json` (pnpm 8.15.9 managed)
- `Dockerfile` (multi-stage, standalone output)
- `app/layout.tsx` (根 layout + Geist 字体 + ErrorBoundary)
- `app/page.tsx` (两栏对话 shell：左侧 thread 列表 + 右侧 ChatThread)
- `app/error.tsx` + `app/not-found.tsx` (错误边界)
- `app/globals.css` (Tailwind v4 CSS-first 配置)
- `lib/store.ts` (Zustand state: user_id / thread_id / messages)
- `lib/api.ts` (fetch wrapper + EventSource SSE client)
- `lib/types.ts` (TypeScript types: Thread/Message/SSEEvent)
- `tsconfig.json` (strict + paths alias @/*)
- **测试**：vitest 配置 + 1 个 message_input 单测 (T086 + T093, W-9 顺手修)

#### 基础设施
- `deploy/docker-compose.yml` (5 服务 M1 stack：postgres:16 / redis:8 / langfuse:4.59.0 / backend / frontend)
- `Taskfile.yml` (13 命令：default / dev:up / dev:down / dev:logs / backend:test / backend:lint / backend:coverage / frontend:dev / frontend:test / frontend:lint / frontend:coverage / test:all / test:coverage)
- `.pre-commit-config.yaml` (gitleaks v8.18.4 + ruff v0.8.4 + prettier v3.4.2 + eslint v9.17.0 + commitlint v9.18.0)
- `.coveragerc` (Python coverage 配置，关键路径 ≥ 80%)
- `.github/workflows/ci.yml` (8-job PR gate：backend / frontend-lint / frontend-test / frontend-build / sast / sca-pip / sca-gitleaks / commitlint)
- `scripts/check_codeowners.sh` (CODEOWNERS validator，32 rules + 1 wildcard PASS)

#### 治理 / Spec 追溯
- `.github/CODEOWNERS` (32 路径路由规则 + 兜底 `* @TL.cai`)
- `.github/PULL_REQUEST_TEMPLATE.md` (Spec / Owner / Type(11 种) / User Story / Task / Converge 状态)
- `.github/ISSUE_TEMPLATE/feature.md` (Spec ID 默认 FEATURE-001-m1-infra)
- `.github/ISSUE_TEMPLATE/bug.md` / `docs.md` / `config.md`

### Spec

- **Spec ID**: FEATURE-001-m1-infra
- **5 User Stories**:
  - US-1 一键起服务栈（Dev.cai.1, feat/m1-us1-infra）
  - US-2 端到端 mock 对话流（Dev.cai.2 后端 + Dev.cai.3 前端）
  - US-3 PR 门禁（Dev.cai.3, feat/m1-us3-pr-gate）
  - US-4 单测一键跑（Dev.cai.4, feat/m1-us4-tests-owners）
  - US-5 团队代码归属（Dev.cai.4, scripts/check_codeowners.sh）
- **Tasks**: 114 个 task（specs/001-m1-infra/tasks.md）

### Team

| Role | GitHub | 负责 |
|---|---|---|
| 主 Owner | @TL.cai | 跨 US 协调 / Converge-Gate / 集成日 demo / merge 决策 |
| Co-Owner A | @Dev.cai.1 | US-1 infra (FastAPI + Next.js + Dockerfile + docker-compose) |
| Co-Owner B | @Dev.cai.2 | US-2 backend (DB + API + Graph + Echo + Langfuse) |
| Co-Owner C | @Dev.cai.3 | US-2 frontend + US-3 PR-gate (Next.js + vitest + ci.yml + W-14) |
| Co-Owner D | @Dev.cai.4 | US-4 tests + US-5 owners (Taskfile + pre-commit + coveragerc + CODEOWNERS 验证) |

### Converge-Gate 状态（集成日 2026-10-16 实测）

| # | 验证项 | 命令 | 实测结果 | 状态 |
|---|---|---|---|---|
| 1 | Taskfile ≥ 10 task | `grep -cE "^  [a-z]..." Taskfile.yml` | 13 tasks | ✅ PASS |
| 2 | 后端 uv sync | `cd research_backend && uv sync --extra dev` | 123 packages resolved | ✅ PASS |
| 3 | 前端 pnpm install | `cd research_frontend && pnpm install` | Already up to date | ✅ PASS |
| 4 | 后端能 import graph | `.venv/bin/python -c "from app.graph.graph import get_compiled_graph"` | OK | ✅ PASS |
| 5 | 后端单测 | `.venv/bin/pytest tests/unit -v` | 114 passed, 0 failed | ✅ PASS |
| 6 | 前端单测 | `pnpm test run` | 7/7 passed | ✅ PASS |
| 7 | 关键路径覆盖率 ≥ 80% | `.venv/bin/pytest --cov=app` | **70.51%**（routes.py 35% 拉低） | ⚠️ NOT MET |
| 8 | ruff lint 0 error | `.venv/bin/ruff check .` | 0 errors | ✅ PASS |
| 9 | eslint 0 error | `pnpm lint` | exit 0 (0 errors, 0 warnings) | ✅ PASS |
| 10 | bandit 0 high | `.venv/bin/bandit -r app/ -ll` | 0 high | ✅ PASS |
| 11 | gitleaks 0 leak | `gitleaks detect --source .` | 工具未装 | ⏭️ SKIP |
| 12 | CODEOWNERS 路径覆盖 | `bash scripts/check_codeowners.sh` | 32 rules PASS | ✅ PASS |
| 13 | ci.yml 8 jobs 名 | `grep -E "^\s{2}[a-z-]+:" .github/workflows/ci.yml` | 8 jobs | ✅ PASS |
| 14 | dev:up 启服务 | `task dev:up` | task 工具未装 + Docker 5 容器 | ⏭️ SKIP |

**最终**: 11/14 PASS · 1/14 NOT MET (#7 coverage) · 2/14 SKIP (#11 gitleaks, #14 dev:up)

**集成日修复**（主 Owner TL.cai）：
- `c61f25d` `fix(backend): ruff 0 errors`（加 RUF001/002/003 ignore for 中文 docstring）
- `74f550c` `fix(backend): add dev optional-dependencies`（补 T002 漏掉的 langfuse + 补 redis 依赖）
- `96bd221` `fix(frontend): vitest 7/7 + eslint 0 errors`（JSX plugin / flat config / TS 7→5.7）

**已知债务**：
- **#7 coverage 70.51% < 80%**：routes.py 35% 拉低（HTTP 路由需要 integration tests，超出 M1 单测范围）。M2 加 integration test suite 补上
- **#11 gitleaks 未装**：pre-commit 链已配置（`gitleaks v8.18.4`），CI job `sca-gitleaks` 也会跑；只是本机未装。集成日未装不影响 CI gate
- **#14 dev:up 未跑**：需 `brew install go-task` + Docker 5 容器（Postgres 16 / Redis 8 / Langfuse 4.59 / backend / frontend）。手动 follow `docs/deployment.md` 即可

### 已知债务（Deferred）

- **W-14**: branch protection status check 名与 ci.yml job 名已对齐（Dev.cai.3 在 feat/m1-us3-pr-gate::ecab237 修），但需要在 GitHub Settings → Branches 实际配置时确认 8 个 status check 全勾上
- **S-1**: CODEOWNERS 含 `bandit.yaml` / `.gitleaks.toml` / `.coveragerc` 等尚未创建的文件（任务未到，M2 时创建）
- **S-2**: Dev.cai.4 的 US-4/US-5 可在 M2 拆分（feat/m1-us4-tests + feat/m1-us5-owners）
- **S-3**: PR template User Story/Task 字段需要 format validation（可在 M2 加 GitHub Action）
- **S-4**: Issue templates 缺 milestone 标签（m1/m2/m3/m4）— M2 启动前补

### Merge 集成日 commit 历史

```
ec2735c merge: M1 milestone complete (integrate 4 Co-Owner deliveries)
856cac5 merge: Dev.cai.3 — CI tools pin + vitest + W-14 status check
fb84325 merge: Dev.cai.3 — frontend layout + page + store
ef89387 merge: Dev.cai.2 — schemas + langfuse + BaseAgent + EchoAgent + routes
685be9d merge: Dev.cai.1 — pyproject + package.json + .env.example + Dockerfile × 2 + docker-compose
18f2e42 merge: Dev.cai.4 — Taskfile + pre-commit + coveragerc + check_codeowners
```

---

## [Unreleased]

### M2 计划（W2 / 检索）
- Planner + Researcher + web_search + fetch_page + Plan/Sources 面板
- 输入 query → Planner 拆任务 → 用户审 topic → Researcher 搜 + 抓 → Sources 面板可见
- 详见 `docs/milestones.md` §M2

### M3 计划（W3 / 写作）
- Writer + Critic + cite + Markdown/PDF 导出 + Draft 审阅 HITL

### M4 计划（W4 / 验收）
- Eval pipeline + CI/CD + 安全 + 异常降级 + v1 demo
- HotpotQA 10 题跑通 + v1.0.0 release tag
