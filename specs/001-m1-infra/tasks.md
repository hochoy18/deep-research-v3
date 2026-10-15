---
description: "M1 任务清单（5 个 User Story × 4 人并行 5 天）"
---

# Tasks: FEATURE-001-m1-infra

**Input**: Design documents from `/specs/001-m1-infra/`
- `plan.md` (required) — 技术栈 / 项目结构
- `spec.md` (required) — 5 个 user story + 25 FR + 12 SC
- `research.md` — 10 项技术决策
- `data-model.md` — 5 个 Key Entity
- `contracts/openapi.yaml` — 8 端点 + SSE
- `quickstart.md` — 端到端验证指南

**Prerequisites**:
- README.md §M1 sprint planning（4 人 5 天表）
- docs/milestones.md §M1 端到端 demo
- .specify/memory/constitution.md v1.1.0
- 12 篇 ADR

**Tests**: Constitution III 强制关键路径 4 条 ≥ 80% 覆盖率（TDD 必跑测试）

**Organization**: 按 user story 组织（spec.md 5 条），每条 story 独立可测；Owner 按 spec Q5 1+4 模式分配

**M1 Kickoff 确认（2026-10-15）**：
- 服务列表：5 个最小集（postgres / redis / langfuse / backend / frontend；省略 milvus/minio）
- Owner：TL.cai (主) + Dev.cai.1-4 (Co-Owner)
- PR 模板：加 `Type: docs/config` 例外标识
- CI 工具：Day 1 锁定最新稳定版本

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件，无依赖）
- **[Story]**: 归属 user story（US1-US5）
- 文件路径绝对 / 相对项目根
- Owner 在 Description 末尾用 `[Owner: <name>]` 标注

---

## Phase 1: Setup（项目初始化 + 工具链）

**Purpose**: 项目骨架、CI 工具链、协作基础

**Target**: Day 1 末完成；本阶段不写业务代码

- [ ] T001 初始化 Git 仓库结构与 `.gitignore`（Python + Node + Docker 模板合并） [Owner: Dev.cai.4]
- [ ] T002 [P] 创建后端项目骨架 `research_backend/`（pyproject.toml + uv 锁定 + Python 3.12） [Owner: Dev.cai.1]
- [ ] T003 [P] 创建前端项目骨架 `research_frontend/`（package.json + pnpm + Next.js 16 + React 19 + TypeScript） [Owner: Dev.cai.1]
- [ ] T004 [P] 创建 `Taskfile.yml`（dev:up / dev:down / dev:logs / backend:test / backend:lint / frontend:dev / frontend:test / frontend:lint / test:all / test:coverage） [Owner: Dev.cai.4]
- [ ] T005 [P] 创建 `.pre-commit-config.yaml`（gitleaks + ruff + ruff-format + eslint + prettier + commitlint） [Owner: Dev.cai.4]
- [ ] T006 [P] 创建 `.github/CODEOWNERS`（按 research_backend/ research_frontend/ deploy/ docs/ 分目录路由到 Dev.cai.1-4） [Owner: TL.cai]
- [ ] T007 [P] 创建 `.github/PULL_REQUEST_TEMPLATE.md`（含 `Spec:` / `Owner:` / `Type: docs/config` / `Converge:` / `Tests:` / `Observability:` / `Security:` 字段，constitution 强制） [Owner: TL.cai]
- [ ] T008 [P] 创建 `.github/ISSUE_TEMPLATE/`（bug / feature / docs / config 4 个模板，feature 模板含 `Spec:` 字段） [Owner: Dev.cai.4]
- [ ] T009 [P] 创建 `.github/workflows/ci.yml`（PR 触发：lint + test + build + SAST + SCA + coverage，constitution I/III 门禁） [Owner: Dev.cai.4]
- [ ] T010 [P] 创建 `research_backend/.env.example`（Postgres / Redis / Langfuse / cookie 密钥 / 限流阈值 5+ 变量） [Owner: Dev.cai.1]
- [ ] T011 [P] 创建 `research_frontend/.env.example`（NEXT_PUBLIC_API_URL / NEXT_PUBLIC_LANGFUSE_URL） [Owner: Dev.cai.1]
- [ ] T012 [P] 创建 `deploy/docker-compose.yml`（5 个服务：postgres:16 / redis:8 / langfuse/langfuse:4.59.0 / backend / frontend；含 healthcheck / depends_on / 网络 / 数据卷） [Owner: Dev.cai.1]
- [ ] T013 [P] 创建 `research_backend/Dockerfile`（Python 3.12-slim + uv 安装 + uvicorn 启动） [Owner: Dev.cai.1]
- [ ] T014 [P] 创建 `research_frontend/Dockerfile`（Node 20-alpine 多阶段构建 + Next.js standalone 输出） [Owner: Dev.cai.1]
- [ ] T015 [P] 锁定 CI 工具最新稳定版本（ruff / pytest / coverage / bandit / pip-audit / vitest / eslint / prettier / gitleaks / commitlint 写入 requirements-dev.txt 与 package.json） [Owner: Dev.cai.4]

**Checkpoint**: Day 1 末，所有模板就位，`task dev:up` 至少能让 postgres / redis / langfuse 起来（backend/frontend 容器 build 成功但 /health 可后续接）

---

## Phase 2: Foundational（核心架构 — 阻塞所有 user story）

**Purpose**: 4 人并行所需的核心基础设施；任何 US 都依赖本阶段

**Target**: Day 2 末完成

- [x] T016 创建 `research_backend/app/main.py`（FastAPI app 实例 + lifespan + CORS + 全局异常处理 + 启动 banner） [Owner: Dev.cai.1]
- [x] T017 [P] 创建 `research_backend/app/config.py`（pydantic-settings 加载 .env，启动时校验必备变量，constitution I 兜底） [Owner: Dev.cai.1]
- [x] T018 [P] 创建 `research_backend/app/api/deps.py`（依赖注入：DB session / Redis client / LangGraph compiled graph / Langfuse client） [Owner: Dev.cai.1]
- [ ] T019 创建 `research_backend/app/db/models.py`（SQLAlchemy 2.x async ORM，Thread + Message 两个模型，映射 data-model.md schema） [Owner: Dev.cai.2]
- [ ] T020 创建 `research_backend/app/db/session.py`（async engine + sessionmaker + alembic 集成） [Owner: Dev.cai.2]
- [ ] T021 创建 `research_backend/app/db/migrations/`（alembic init + 第一个 migration：threads + messages 两表，索引匹配 data-model.md） [Owner: Dev.cai.2]
- [ ] T022 [P] 创建 `research_backend/app/auth/anonymous.py`（中间件：首次访问生成 UUID v4 → Set-Cookie httpOnly+Secure+SameSite=Lax Max-Age=2592000；后续从 cookie 读 user_id） [Owner: Dev.cai.4]
- [ ] T023 [P] 创建 `research_backend/app/ratelimit/limiter.py`（Redis 滑动窗口实现：key=ip_hash:user_id，INCR + EXPIRE 原子；阈值每分 10 / 每小时 100，超限 raise HTTPException 429） [Owner: Dev.cai.4]
- [ ] T024 [P] 创建 `research_backend/app/api/schemas.py`（Pydantic 模型：Thread / Message / MessageCreate / SSEEvent / Error，对应 contracts/openapi.yaml） [Owner: Dev.cai.2]
- [ ] T025 [P] 创建 `research_backend/app/observability/langfuse.py`（`get_client()` + `@observe` decorator + OTel 配置，ADR-0006） [Owner: Dev.cai.2]
- [x] T026 [P] 创建 `research_backend/app/observability/logging.py`（structlog 配置：JSON 输出 + ts/level/service/trace_id/actor/event/latency_ms/error 必填字段，constitution VII） [Owner: Dev.cai.1]
- [ ] T027 创建 `research_backend/app/agents/base.py`（BaseAgent 抽象：M1 阶段仅占位，不实现 4 Agent；M2+ 启用，spec Q1 极简 echo） [Owner: Dev.cai.2]
- [ ] T028 [P] 创建 `research_backend/app/agents/echo.py`（M1 极简 echo 节点：接 user query → 按 token 切分 → 流式回显，spec Q1 澄清） [Owner: Dev.cai.2]
- [ ] T029 创建 `research_backend/app/graph/state.py`（AgentState M1 简化为：`{ messages: list, user_id: str, thread_id: str }`，M2+ 扩展） [Owner: Dev.cai.2]
- [ ] T030 创建 `research_backend/app/graph/graph.py`（StateGraph compile：单 echo 节点 + START/END 边 + RedisCheckpointSaver 接入） [Owner: Dev.cai.2]
- [ ] T031 [P] 创建 `research_backend/app/api/routes.py`（路由注册：/health / /threads / /threads/{id} / /threads/{id}/messages，按 contracts/openapi.yaml 落地） [Owner: Dev.cai.2]
- [x] T032 创建 `research_backend/pyproject.toml` dev 依赖（pytest / pytest-asyncio / pytest-cov / ruff / bandit / pip-audit / httpx / factory-boy / freezegun） [Owner: Dev.cai.1]
- [ ] T033 [P] 创建 `research_frontend/app/layout.tsx`（根 layout + 字体 + 全局 ErrorBoundary） [Owner: Dev.cai.3]
- [ ] T034 [P] 创建 `research_frontend/app/page.tsx`（对话主页：左侧 thread 列表 + 右侧 ChatThread） [Owner: Dev.cai.3]
- [ ] T035 [P] 创建 `research_frontend/lib/api.ts`（fetch wrapper：自动携带 cookie + EventSource SSE 客户端 + 错误处理） [Owner: Dev.cai.3]
- [ ] T036 [P] 创建 `research_frontend/lib/store.ts`（Zustand store：当前 user_id / 当前 thread_id / 消息列表） [Owner: Dev.cai.3]
- [ ] T037 [P] 创建 `research_frontend/lib/types.ts`（TypeScript 类型：Thread / Message / SSEEvent，对应 contracts/openapi.yaml） [Owner: Dev.cai.3]
- [ ] T038 创建 `research_frontend/package.json` dev 依赖（vitest / @testing-library/react / @testing-library/jest-dom / jsdom / eslint / prettier / tailwindcss@4） [Owner: Dev.cai.3]
- [ ] T039 [P] 创建 `research_frontend/tsconfig.json`（strict: true + paths alias `@/*`） [Owner: Dev.cai.3]
- [ ] T040 [P] 创建 `research_frontend/tailwind.config.ts`（Tailwind v4 CSS-first 配置 + shadcn 主题，ADR-0007） [Owner: Dev.cai.3]

**Checkpoint**: Day 2 末，`task dev:up` 起 5 个服务，后端 `/health` 返回 ok；前端 `localhost:3000` 看到布局（空白 ChatThread）

---

## Phase 3: User Story 1 - 一键起服务栈 (Priority: P1) 🎯 MVP

**Goal**: 干净机器上 5 分钟内 `task dev:up` 起 5 个服务，浏览器看到对话界面

**Independent Test**: 在干净容器里跑 `task dev:up`，记录启动时间，验证 5 个容器 health 通过且前端可访问

**Owner**: Dev.cai.1 (主责) / TL.cai (审阅)

### Tests for US1 ⚠️ TDD 优先

- [x] T041 [P] [US1] 编写 `research_backend/tests/integration/test_dev_up.py`（集成测试：起 5 个 docker-compose 服务，逐一 curl /health，验证全 up） [Owner: Dev.cai.1]
- [x] T042 [P] [US1] 编写 `research_backend/tests/unit/test_config.py`（单测：pydantic-settings 加载 .env，缺失必备变量 raise ValidationError） [Owner: Dev.cai.1]

### Implementation for US1

- [ ] T043 [US1] 完善 `deploy/docker-compose.yml`（5 服务：postgres:16 / redis:8 / langfuse/langfuse:4.59.0 / backend / frontend；healthcheck + depends_on + 网络 bridge + 数据卷 + 资源限制） [Owner: Dev.cai.1]
- [x] T044 [P] [US1] 完善 `research_backend/Dockerfile`（Python 3.12-slim + uv 装依赖 + uvicorn 启动 + healthcheck） [Owner: Dev.cai.1]
- [ ] T045 [P] [US1] 完善 `research_frontend/Dockerfile`（Node 20-alpine 多阶段：build → standalone output → 运行） [Owner: Dev.cai.3]
- [ ] T046 [P] [US1] 完善 `Taskfile.yml`（增加 dev:up 等待 healthcheck / dev:down 清卷 / dev:logs tail / backend:test / backend:lint / backend:coverage / frontend:test / frontend:dev） [Owner: Dev.cai.4]
- [ ] T047 [P] [US1] 端口冲突检测（`task dev:up` 启动前 lsof 检查 3000/3001/5432/6379/8000 端口，冲突时给明确修复建议） [Owner: Dev.cai.1]
- [ ] T048 [P] [US1] README 启动说明（首次启动预期 5 分钟、镜像大小、常见问题） [Owner: Dev.cai.1]
- [ ] T049 [P] [US1] 编写 `.env.example` 完整模板（含 Postgres / Redis / Langfuse / Langfuse OTel / cookie 签名密钥 / 限流阈值 / 启动超时） [Owner: Dev.cai.1]

**Checkpoint**: Day 3 末，US1 跑通；`task dev:up` 5 分钟内起 5 服务；端口冲突检测生效；`task dev:down` 干净停止

---

## Phase 4: User Story 2 - 端到端 mock 对话流 (Priority: P1) 🎯 MVP

**Goal**: 浏览器输入 query → 后端 mock 流式回显 → Langfuse UI 看到 trace

**Independent Test**: quickstart.md §2.1-§2.4 全部跑通（浏览器 + CLI + 跨刷新 + 跨会话）

**Owner**: Dev.cai.2 (主责) / Dev.cai.3 (前端配合) / TL.cai (审阅)

### Tests for US2 ⚠️ TDD 优先（关键路径 1 + 路径 4）

- [ ] T050 [P] [US2] 编写 `research_backend/tests/integration/test_e2e_echo.py`（端到端：发 query → 收 SSE 流 → 验证 message/state_update/done 4 event type） [Owner: Dev.cai.2]
- [ ] T051 [P] [US2] 编写 `research_backend/tests/integration/test_e2e_trace.py`（端到端：发 query → 查 Langfuse API → 验证 trace 含 node/input/output 3 字段） [Owner: Dev.cai.2]
- [ ] T052 [P] [US2] 编写 `research_backend/tests/unit/test_echo_agent.py`（单测：echo 节点按 token 切片流式输出边界条件） [Owner: Dev.cai.2]
- [ ] T053 [P] [US2] 编写 `research_backend/tests/contract/test_openapi.py`（契约测试：requests 校验 contracts/openapi.yaml 与实际 API 一致，constitution VI） [Owner: Dev.cai.2]
- [ ] T054 [P] [US2] 编写 `research_frontend/tests/e2e/test_chat_thread.spec.ts`（Playwright：浏览器输入 query → 看到流式渲染 → 截图） [Owner: Dev.cai.3]

### Implementation for US2

- [ ] T055 [US2] 实现 `research_backend/app/api/routes.py` 的 4 个端点（POST /threads / GET /threads / GET /threads/{id} / POST /threads/{id}/messages 含 SSE StreamingResponse） [Owner: Dev.cai.2]
- [ ] T056 [US2] 实现 `research_backend/app/api/schemas.py`（Pydantic 模型严格匹配 contracts/openapi.yaml：UserId cookie / Thread / Message / MessageCreate / SSEEvent） [Owner: Dev.cai.2]
- [ ] T057 [US2] 实现 `research_backend/app/agents/echo.py` 完整版（接 state → 按 token 切分 query（每 ~50ms 一片）→ yield SSEEvent） [Owner: Dev.cai.2]
- [ ] T058 [US2] 实现 `research_backend/app/graph/graph.py` 完整版（StateGraph compile + RedisCheckpointSaver + thread_id 关联） [Owner: Dev.cai.2]
- [ ] T059 [US2] 实现 `research_backend/app/observability/langfuse.py` decorator 包裹 echo 节点（写入 trace：node=echo_agent / input=query / output=chunks） [Owner: Dev.cai.2]
- [ ] T060 [P] [US2] 实现 `research_frontend/lib/api.ts` SSE 客户端（EventSource 自动重连 + chunk 拼接 + 错误处理） [Owner: Dev.cai.3]
- [ ] T061 [P] [US2] 实现 `research_frontend/components/chat-thread.tsx`（流式渲染：逐 token 拼接到消息流 + Markdown 实时渲染） [Owner: Dev.cai.3]
- [ ] T062 [P] [US2] 实现 `research_frontend/components/message-input.tsx`（输入框 + 提交按钮 + Enter 快捷键） [Owner: Dev.cai.3]
- [ ] T063 [P] [US2] 实现 `research_frontend/components/thread-list.tsx`（左侧 thread 列表 + 选中态） [Owner: Dev.cai.3]
- [ ] T064 [P] [US2] 实现 `research_frontend/app/page.tsx` 整合（左侧 thread 列表 + 右侧 ChatThread + MessageInput） [Owner: Dev.cai.3]
- [ ] T065 [P] [US2] 实现 `research_frontend/app/threads/[thread_id]/page.tsx`（深链接 thread 详情页） [Owner: Dev.cai.3]
- [ ] T066 [US2] 实现跨刷新恢复（thread_id 持久化到 URL，刷新后从 RedisCheckpointSaver 恢复 state） [Owner: Dev.cai.2]
- [ ] T067 [US2] 实现跨会话重开（GET /threads 列出当前 user_id 所有 thread，点击进入看历史） [Owner: Dev.cai.2]

**Checkpoint**: Day 3 末，US2 跑通；浏览器端到端 mock 对话流全链路成功；Langfuse UI 看到 trace；跨刷新不丢内容

---

## Phase 5: User Story 3 - PR 质量门禁 (Priority: P1)

**Goal**: PR 自动跑 lint + test + build + SAST + SCA + 覆盖率门禁；缺 Spec / 高危漏洞 / 覆盖率 < 80% 阻断合并

**Independent Test**: quickstart.md §3.1（故意失败 PR 被 CI 阻断）+ §3.2（合规 PR 全绿）

**Owner**: Dev.cai.3 (主责) / TL.cai (审阅)

### Tests for US3 ⚠️ TDD 优先

- [ ] T068 [P] [US3] 编写 `research_backend/tests/ci/test_pr_template.py`（测试：解析 PULL_REQUEST_TEMPLATE.md，验证 Spec/Owner/Converge/Tests/Observability/Security 字段存在） [Owner: Dev.cai.3]
- [ ] T069 [P] [US3] 编写 `research_backend/tests/ci/test_coverage_gate.py`（测试：故意低于 80% → CI 阻断） [Owner: Dev.cai.3]
- [ ] T070 [P] [US3] 编写 `research_backend/tests/ci/test_sast_sca.py`（测试：故意引入 SQL 注入 / 带漏洞依赖 → bandit / pip-audit 报警） [Owner: Dev.cai.3]

### Implementation for US3

- [ ] T071 [US3] 完善 `.github/workflows/ci.yml`（PR 触发：gitleaks → ruff → eslint → pytest + coverage → vitest + coverage → build → bandit → pip-audit → npm audit；constitution I/III 门禁） [Owner: Dev.cai.3]
- [ ] T072 [P] [US3] 配置 coverage 关键路径门禁（pytest-cov 配置：仅统计 4 条关键路径对应源码，行覆盖 < 80% → exit 1） [Owner: Dev.cai.3]
- [ ] T073 [P] [US3] 配置 SAST 门禁（bandit 配置：严重级别 high → exit 1；中危 7 天修复警告） [Owner: Dev.cai.3]
- [ ] T074 [P] [US3] 配置 SCA 门禁（pip-audit 配置：高危 CVE → exit 1；npm audit 同理） [Owner: Dev.cai.3]
- [ ] T075 [P] [US3] 完善 `.pre-commit-config.yaml`（gitleaks + ruff-format + eslint --fix + prettier + commitlint；与 CI 一致） [Owner: Dev.cai.4]
- [ ] T076 [P] [US3] 配置 commitlint（conventional commits 规范，contributing.md §2 强制） [Owner: Dev.cai.4]
- [ ] T077 [P] [US3] PR 模板 Spec 字段校验（CI step 解析 PR body，未含 `Spec: FEATURE-` 前缀 → 阻断） [Owner: Dev.cai.3]
- [ ] T078 [P] [US3] PR 模板 Type 字段识别（`Type: docs/config` 例外 → 跳过 Spec 校验但仍走 lint/test） [Owner: Dev.cai.3]
- [ ] T079 [P] [US3] Type: docs/config 例外的 CI 路径（ci.yml 增加 if: 条件：type=docs/config 时跳过 SAST/SCA） [Owner: Dev.cai.3]
- [ ] T080 [P] [US3] 写 `docs/ci/checklist.md`（开发者自检清单：commit 前 / PR 前 / merge 前） [Owner: Dev.cai.3]

**Checkpoint**: Day 4 末，US3 跑通；故意失败 PR 被 CI 阻断；合规 PR 全绿；Type: docs/config 例外生效

---

## Phase 6: User Story 4 - 单测 / 集成测试可本地一键跑 (Priority: P2)

**Goal**: `task backend:test` / `task frontend:test` 一键跑全部测试，结果与 CI 一致

**Independent Test**: quickstart.md §5 跑通；关键路径 4 条 ≥ 80% 覆盖率

**Owner**: Dev.cai.4 (主责) / TL.cai (审阅)

### Tests for US4 ⚠️ TDD 优先（关键路径 2 + 路径 3）

- [ ] T081 [P] [US4] 编写 `research_backend/tests/integration/test_thread_crud.py`（集成测试：POST /threads → GET /threads → GET /threads/{id}；按 user_id 过滤；越权读返回 403，spec FR-011a） [Owner: Dev.cai.4]
- [ ] T082 [P] [US4] 编写 `research_backend/tests/integration/test_ratelimit.py`（集成测试：单 IP+user_id 1 分钟内 11 次请求 → 第 11 次返回 429 + retry_after_seconds，spec FR-011b） [Owner: Dev.cai.4]
- [ ] T083 [P] [US4] 编写 `research_backend/tests/unit/test_ratelimit_limiter.py`（单测：滑动窗口边界：59s 第 10 次 ok / 60s 第 11 次 429；window 切换后计数重置） [Owner: Dev.cai.4]
- [ ] T084 [P] [US4] 编写 `research_backend/tests/unit/test_anonymous_cookie.py`（单测：首次访问生成 UUID v4 / 后续从 cookie 读 / cookie 缺失视为新用户） [Owner: Dev.cai.4]
- [ ] T085 [P] [US4] 编写 `research_backend/tests/integration/test_cross_user_isolation.py`（集成测试：用户 A 创建 thread → 用户 B cookie 读 → 返回 403，spec SC-011） [Owner: Dev.cai.4]
- [ ] T086 [P] [US4] 编写 `research_frontend/tests/unit/test_message_input.spec.ts`（vitest：输入框 + 提交 + Enter 触发） [Owner: Dev.cai.3]

### Implementation for US4

- [ ] T087 [US4] 完善 `research_backend/app/auth/anonymous.py`（中间件：从 cookie 读 user_id，缺失则生成 UUID v4 + Set-Cookie；request.state.user_id 注入） [Owner: Dev.cai.4]
- [ ] T088 [US4] 完善 `research_backend/app/ratelimit/limiter.py`（Redis 滑动窗口：key=`rl:{ip_hash}:{user_id}` / 1m window / 10 req / 1h window / 100 req；超限 raise 429 + 重试时间） [Owner: Dev.cai.4]
- [ ] T089 [US4] 在 `research_backend/app/api/routes.py` 加限流中间件（POST /threads/{id}/messages 端点；其他端点豁免） [Owner: Dev.cai.2]
- [ ] T090 [P] [US4] 在 `research_backend/app/api/routes.py` 加跨用户隔离（GET /threads/{id} 与 GET /threads/{id}/messages 必校验 thread.user_id == request.state.user_id） [Owner: Dev.cai.2]
- [ ] T091 [P] [US4] 完善 `Taskfile.yml` 测试目标（backend:test / backend:coverage / backend:cov:html / frontend:test / frontend:coverage / test:all / test:coverage 全套命令） [Owner: Dev.cai.4]
- [ ] T092 [P] [US4] 配置 pytest（pytest.ini / conftest.py：asyncio mode=auto + 关键路径标记 + 覆盖率输出到 backend/coverage/） [Owner: Dev.cai.4]
- [ ] T093 [P] [US4] 配置 vitest（vitest.config.ts：jsdom 环境 + 关键路径标记 + 覆盖率输出到 frontend/coverage/） [Owner: Dev.cai.3]
- [ ] T094 [P] [US4] 覆盖率徽章（README.md 加 coverage 徽章：从 backend/coverage/coverage.xml + frontend/coverage/coverage.xml 解析） [Owner: Dev.cai.4]

**Checkpoint**: Day 4 末，US4 跑通；`task backend:test` 全绿 + 关键路径 ≥ 80%；`task frontend:test` 全绿；越权 + 限流集成测试通过

---

## Phase 7: User Story 5 - 团队代码归属与审批 (Priority: P2)

**Goal**: PR 自动按目录路由 reviewer；跨团队 reviewer + 领域 Owner 双签才能合并

**Independent Test**: 改不同目录触发不同 reviewer；跨团队 reviewer 强制要求

**Owner**: Dev.cai.4 (主责) / TL.cai (审阅)

### Tests for US5

- [ ] T095 [P] [US5] 编写 `research_backend/tests/ci/test_codeowners.py`（测试：解析 CODEOWNERS 文件，验证 research_backend/ research_frontend/ deploy/ docs/ 都有 Owner） [Owner: Dev.cai.4]
- [ ] T096 [P] [US5] 编写 `research_backend/tests/ci/test_pr_review_rules.py`（测试：模拟 PR 跨团队 reviewer 缺失 → 阻断） [Owner: Dev.cai.4]

### Implementation for US5

- [ ] T097 [US5] 完善 `.github/CODEOWNERS`（按目录分 Owner：research_backend/ → Dev.cai.1+2；research_frontend/ → Dev.cai.3；deploy/ → Dev.cai.1+4；.specify/ → TL.cai；docs/ → 全员 + TL.cai 兜底） [Owner: TL.cai]
- [ ] T098 [P] [US5] 配置 GitHub branch protection（main 分支保护：需 1 跨团队 reviewer + Spec 字段 + 所有 CI check 通过） [Owner: TL.cai]
- [ ] T099 [P] [US5] PR 模板审阅规则说明（在 PULL_REQUEST_TEMPLATE.md 加 `Reviewers:` 字段引导 + 跨团队规则说明） [Owner: Dev.cai.4]
- [ ] T100 [P] [US5] 写 `docs/contributing/pr-review.md`（Reviewer 指南：如何在 24h 内 review / 跨团队 reviewer 选取规则 / 拒绝 PR 的礼仪） [Owner: Dev.cai.4]
- [ ] T101 [P] [US5] CODEOWNERS 自动验证（CI step 解析 CODEOWNERS 格式正确性，未匹配目录给警告） [Owner: Dev.cai.4]

**Checkpoint**: Day 4 末，US5 跑通；改不同目录触发不同 reviewer；branch protection 规则生效

---

## Phase 8: Polish & Cross-Cutting Concerns + 集成日 Demo

**Purpose**: 收尾 + 跨 US 收口 + 集成日 demo

**Target**: Day 5 集成日

- [ ] T102 [P] 跑 quickstart.md 全量验证（§1-§7 全部 scenario 走一遍；记录结果到 docs/m1-validation.md） [Owner: TL.cai]
- [ ] T103 [P] 更新 README.md §M1 状态（"计划中" → "M1 ✅ 完成"） [Owner: TL.cai]
- [ ] T104 [P] 录 demo 视频 / 截图（端到端 mock 对话流全流程 + Langfuse trace + 跨刷新 + 跨用户隔离） [Owner: TL.cai]
- [ ] T105 [P] 写 `docs/postmortem/m1-retrospective.md`（含 4 人体验评分 / 关键 bug / 改进点 / M2 建议） [Owner: TL.cai]
- [ ] T106 [P] 跑 `/speckit-converge`（spec/plan/tasks 三件套一致性检查 + checklist 全过） [Owner: TL.cai]
- [ ] T107 [P] git tag `m1-complete`（M1 里程碑归档） [Owner: TL.cai]
- [ ] T108 [P] M2 kickoff 文档（基于 M1 复盘，写 milestones.md §M2 sprint planning 留白处 + 调 research.md R1 切换为 4 Agent 编排） [Owner: TL.cai]
- [ ] T109 [P] 合并所有分支到 main（Dev.cai.1-4 各 merge 自己的 user story 分支；TL.cai 协调冲突） [Owner: TL.cai]
- [ ] T110 [P] 集成日 bug 修复（demo 过程中发现的任何 issue；按 P0/P1 优先级处理） [Owner: TL.cai]
- [ ] T111 [P] SPEC 文档归档（spec.md 标记 Status: Converged） [Owner: TL.cai]
- [ ] T112 [P] 跑最终覆盖率报告（4 条关键路径 ≥ 80%；HTML 报告附在 M1 复盘文档中） [Owner: TL.cai]

**Checkpoint**: M1 集成日，4 个 Owner 全部 sign-off；Converge-Gate 满足；进入 M2 启动

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: 无依赖，立即开始
- **Phase 2 (Foundational)**: 依赖 Phase 1；**阻塞所有 user story**
- **Phase 3-7 (US1-US5)**: 依赖 Phase 2；可 4 人并行（按 Owner 划分）
- **Phase 8 (Polish)**: 依赖 Phase 3-7 全部完成

### User Story Dependencies

| User Story | Priority | Owner | 依赖其他 US | 可并行 US |
|---|---|---|---|---|
| US1 (一键起服务栈) | P1 | Dev.cai.1 | 无 | US2, US3, US4, US5 |
| US2 (端到端 mock 对话流) | P1 | Dev.cai.2 + Dev.cai.3 | 无 | US1, US3, US4, US5 |
| US3 (PR 质量门禁) | P1 | Dev.cai.3 | 无 | US1, US2, US4, US5 |
| US4 (单测一键跑) | P2 | Dev.cai.4 | 无（但用 US2 的基础设施） | US1, US2, US3, US5 |
| US5 (团队代码归属) | P2 | Dev.cai.4 | 无 | US1, US2, US3, US4 |

**注意**：US2 需 Dev.cai.3 (前端) 与 Dev.cai.2 (后端) 协作；US3 需 Dev.cai.3 主责。

### Within Each User Story

- Tests MUST 写且必须 FAIL 在前（constitution III TDD）
- Models 在 services 前
- Services 在 endpoints 前
- 核心实现在集成前
- Story 完成才能进入下一 priority

### Parallel Opportunities

- Phase 1 全部 [P] 任务可并行
- Phase 2 全部 [P] 任务可并行
- Phase 3-7 完成后，US1-US5 可 4 人并行（按 Owner 划分）
- 每个 US 内的 [P] 任务可并行（不同文件，无依赖）
- 跨 US 任务也可并行（不同 Owner 负责不同文件）

---

## Parallel Example: US2 Implementation

```bash
# T055-T059（后端实现串行 — 同一文件 routes.py / schemas.py）
# 但 T060-T065（前端实现）可与后端 T055-T059 并行

# 实际执行（Dev.cai.2 + Dev.cai.3 并行）:
# Dev.cai.2: T055, T056, T057, T058, T059, T066, T067  (后端)
# Dev.cai.3: T060, T061, T062, T063, T064, T065  (前端)
# Dev.cai.3 还并行做: T054 (Playwright e2e 测试)
```

---

## Implementation Strategy

### MVP First（US1 + US2）

1. Phase 1 Setup → Day 1 末
2. Phase 2 Foundational → Day 2 末
3. Phase 3 US1（一键起服务栈）→ Day 3 中
4. Phase 4 US2（端到端 mock 对话流）→ Day 3 末
5. **STOP and VALIDATE**: 端到端 demo 跑通（query → SSE → Langfuse trace）→ MVP
6. Demo 给团队 + 录视频

### Incremental Delivery

1. Phase 1+2 → 基础设施 ready
2. Phase 3 US1 → 5 分钟一键起服务栈（独立可测）
3. Phase 4 US2 → 端到端 mock 对话流（独立可测，**MVP**）
4. Phase 5 US3 → PR 门禁（独立可测）
5. Phase 6 US4 → 单测一键跑（独立可测）
6. Phase 7 US5 → 团队代码归属（独立可测）
7. Phase 8 Polish → 集成日 demo + 复盘

### Parallel Team Strategy（README §M1 4 人 5 天表）

| Day | Dev.cai.1 (Infra) | Dev.cai.2 (Graph) | Dev.cai.3 (Frontend) | Dev.cai.4 (Deploy/CI) |
|---|---|---|---|---|
| **Day 1** | T001-T015（Setup） | T001-T015 | T001-T015 | T001-T015 |
| **Day 2** | T016-T040（Foundational） | T016-T040 | T016-T040 | T016-T040 |
| **Day 3** | T041-T049（US1） | T050-T059, T066-T067（US2 后端） | T054, T060-T065（US2 前端） | T046（Taskfile） |
| **Day 4** | T089-T090（US4 路由） | T089-T090 | T068-T080, T086（US3 + 部分 US4） | T081-T094, T095-T101（US4 + US5） |
| **Day 5** | T102-T112（Polish） | T102-T112 | T102-T112 | T102-T112 |

**集成顺序**：A（Dev.cai.1）先 merge → D（Dev.cai.4 CI 跑通）→ A 增量 → B（Dev.cai.2）→ C（Dev.cai.3）→ demo

---

## Critical Files Inventory

> Owner 各自负责的核心文件清单（按 user story 划分）

### Dev.cai.1 负责
- `deploy/docker-compose.yml`
- `research_backend/Dockerfile`
- `research_backend/app/main.py`
- `research_backend/app/config.py`
- `research_backend/app/api/deps.py`
- `research_backend/app/observability/logging.py`
- `research_backend/pyproject.toml`
- `research_frontend/Dockerfile`
- `research_frontend/package.json` (启动部分)

### Dev.cai.2 负责
- `research_backend/app/db/models.py`
- `research_backend/app/db/session.py`
- `research_backend/app/db/migrations/`
- `research_backend/app/agents/base.py`
- `research_backend/app/agents/echo.py`
- `research_backend/app/graph/state.py`
- `research_backend/app/graph/graph.py`
- `research_backend/app/api/routes.py`
- `research_backend/app/api/schemas.py`
- `research_backend/app/observability/langfuse.py`

### Dev.cai.3 负责
- `research_frontend/app/layout.tsx`
- `research_frontend/app/page.tsx`
- `research_frontend/app/threads/[thread_id]/page.tsx`
- `research_frontend/components/chat-thread.tsx`
- `research_frontend/components/message-input.tsx`
- `research_frontend/components/thread-list.tsx`
- `research_frontend/lib/api.ts`
- `research_frontend/lib/store.ts`
- `research_frontend/lib/types.ts`
- `research_frontend/tailwind.config.ts`
- `research_frontend/tsconfig.json`
- `research_frontend/tests/`
- `.github/workflows/ci.yml`
- `.github/PULL_REQUEST_TEMPLATE.md`

### Dev.cai.4 负责
- `Taskfile.yml`
- `.pre-commit-config.yaml`
- `.github/workflows/ci.yml` (基础部分)
- `.github/ISSUE_TEMPLATE/`
- `.github/CODEOWNERS`
- `research_backend/app/auth/anonymous.py`
- `research_backend/app/ratelimit/limiter.py`
- `research_backend/pyproject.toml` (dev 依赖)
- `research_frontend/package.json` (dev 依赖)

### TL.cai 负责
- `docs/postmortem/m1-retrospective.md`
- `README.md` 状态更新
- `docs/ci/checklist.md`
- `.github/CODEOWNERS` (审核)
- `.github/PULL_REQUEST_TEMPLATE.md` (审核)
- M1 集成日 demo 协调
- Converge 签字
- M2 kickoff

---

## Definition of Done（M1 DoD）

- [ ] T001-T112 全部勾完
- [ ] Phase 3-7 全部 checkpoint 通过
- [ ] quickstart.md §1-§7 全部 scenario 跑通
- [ ] 关键路径 4 条覆盖率 ≥ 80%（constitution III）
- [ ] SAST/SCA 0 高危漏洞（constitution I）
- [ ] PR 模板强制字段全绿（constitution II）
- [ ] branch protection 配置生效（constitution V）
- [ ] Langfuse UI 看到 mock trace（constitution VII）
- [ ] README.md §M1 状态从「计划中」更新为「M1 ✅ 完成」
- [ ] TL.cai + 4 Co-Owner 全部 sign-off（constitution IV Converge-Gate）
- [ ] spec.md 标记 Status: Converged
- [ ] git tag m1-complete

---

## Notes

- [P] 任务 = 不同文件，无依赖
- [Story] 标签映射到 user story，便于追溯
- 每个 US 独立可完成 + 独立可测
- **TDD 强制**：测试先写 → 红 → 实现 → 绿 → 重构
- 每完成 1 个 task 或逻辑组就 commit
- 在任何 checkpoint 可停下来验证 story
- 避免：模糊任务、同一文件冲突、跨 story 依赖破坏独立性
- **Constitution 兜底**：每个 PR MUST 引用 Spec / 通过 SAST+SCA / 关键路径 ≥ 80% / 1 个跨团队 reviewer
- **M1 → M2 演进**：本 spec Converged 后冻结；M2 新建 `specs/002-m2-research/` 走同样流程
