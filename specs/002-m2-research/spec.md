# Feature Specification: M2 - 检索（Planner + Researcher + Topic HITL）

**Feature ID**: `FEATURE-002-m2-research`
**Feature Branch**: `feature/002-m2-research`
**Created**: 2026-10-16
**Status**: Draft
**Owner**: TL.cai（constitution V — M2 单人开发模式，本 spec 一个主 Owner 全包；不分 Co-Owner；不开子分支；Day 7 self-merge → main → tag v1.0.0-M2）
**Milestone**: M2 - 检索（W2）

**Input**: User description: "基于 docs/milestones.md §M2 + docs/agent-design.md §3.1/§3.2 + docs/graph-design.md §3/§4 + 12 篇 ADR 生成 M2 spec.md"

---

## Clarifications

### Session 2026-10-16

- **Q1**：M2 demo Day 5 用真实 LLM 还是 mock 即可？→ **A：真实 LLM**（Bailian DashScope / OpenAI-compatible），BaseAgent 调真 LLM；需要 `DASHSCOPE_API_KEY` 或 `OPENAI_API_KEY`；限流风险由 retry + runbook 兜底；mock 仍保留为 `LLM_MOCK=1` 环境变量下的兜底方案，供测试 / CI 使用
- **Q2**：Topic 审阅 HITL `interrupt()` 必须靠 `POST /threads/{id}/resume` 路由驱动 `Command(resume=...)`。M2 是否必做？→ **A：必做**。graph-design §4 契约；OpenAPI v0.2.0-m2 必含此路由；interrupt 暂停/恢复全靠它；M2 demo 才能跑通 topic 审阅后继续 Researcher 循环
- **Q3**：M2 contract test 走 Pact consumer-driven 还是 OpenAPI parity check（轻量）？→ **A：OpenAPI parity check**（不引 Pact）。在 `tests/contract/test_openapi.py` 验证 `openapi.yaml` 的 schemas 与 `app/api/schemas.py` (Pydantic) + `lib/types.ts` (TS) 100% 一致；零新依赖，1-2 个测试文件即可
- **Q4**：M2 仍延续 TL.cai + Dev.cai.1-4 4 人并行？→ **A：单人**（TL.cai 全包）。M1 已是 4 人 5 天 4 worktree 并行；M2 简化为单人顺序开发 5-7 天，不分 Co-Owner，不建 `feat/m2-usN-*` 分支，不开子 worktree；集成日由 TL.cai 自己 review + merge main + tag v1.0.0-M2
- **Q5**：`app/llm/router.py` 现在建还是 M3+ 再建？→ **A：M2 创最小版**（单 `model_role` + 单 `provider`），给 BaseAgent 占位用；M3+ 再扩展为 multi-model routing
- **Q6**：Planner 拆任务是先做 `clarify_with_user` 节点再做 planner，还是只做 `topic_review` 一个 HITL？→ **A：只做 `topic_review`**。spec 范围清晰是 "HITL topic 审阅"；`clarify_with_user` 节点（带 research_brief 澄清）留 M3+（届时 M3 spec 决策）
- **Q7**：Researcher 循环是否要带 sub-graph（search → fetch → summarize → decide_next 4 节点）还是单节点循环？→ **A：sub-graph**（graph-design §3 已固化，复用设计）
- **Q8**：Bailian `web_search` 限流时是否切 Tavily 备选？→ **A：先接 Bailian + 重试 2 次指数退避**；Tavily 仅在 `runbooks/llm-ratelimit.md` 兜底段中列方案，不增加 provider 实现
- **Q9**：SSRF 白名单：M2 是否允许任意公网域名？→ **A：否**。默认 `SSRF_ALLOWLIST` 从 env 注入（CSV 格式，约 30 条主流新闻/学术/政府域名）；其余走 trafilatura 抽取 + 警告日志；测试时通过 env 注入 mock 域名
- **Q10**：M2 demo Day 5 是否包含真实 LLM？→ **A：必含**。D1 已确认真实 LLM；集成日 demo 必含真 LLM 跑通（query → Planner 真拆任务 → Researcher 真检索）
- **Q11**：`MAX_RESEARCH_ITERATIONS` 设多少？→ **A：5**（与 agent-design §3.2 设计一致；Researcher sub-graph 兜底防死循环）
- **Q12**：Topic chip 上限（用户增删改 topic 的最大数量）？→ **A：硬编码 20**（v1 简化；topic_review 节点拒绝 > 20 并返回 HTTP 400）

---

## Owner 矩阵（constitution V）

| 角色 | 姓名 | 负责 User Story | 负责关键路径 | 职责 |
|---|---|---|---|---|
| **主 Owner** | TL.cai | 全部 5 个（US-1 ~ US-5） | 全部 5 条（见 SC-006） | 业务决策 / Converge-Gate 签字 / 集成日 self-merge / 复盘 / M3 kickoff 占位 |

> **M2 单人模式说明**：M1 4 人并行模式（M1 kickoff 时 1 主 + 4 Co-Owner）不延续到 M2。M2 决策改为 TL.cai 单人顺序开发 5-7 天，理由：(1) M1 已打通端到端基建（FastAPI / Next.js / LangGraph / Langfuse / Taskfile / CI），M2 主要是新功能叠加；(2) 真实 LLM 调试 + topic HITL 串行依赖强，并行易冲突；(3) 单人 demo 录视频时无需协调 4 个 Owner。Constitution V（One-Feature-Owner）仍满足 — 一个 feature 一个主 Owner，**单人也算一个 Owner**。

---

## User Scenarios & Testing

### User Story 1 - Planner 拆任务 + Topic 审阅 HITL（Priority: P1）

用户输入 query 后，后端先调 Planner 把 query 拆成 3-7 个结构化 sub-task（每个含搜索词 + 期望来源数），前端弹出 topic 审阅 UI 让用户增删改 topic（可点 Skip），确认后 Researcher 才启动。

**Why this priority**：Planner + Topic HITL 是 M2 demo 第 2-3 步（拆任务 + 用户审方向），没有它 Researcher 就盲目跑且结果无法人工干预；M2 端到端 demo 的"价值核心"——把"用户研究方向"显式化、可交互，而不是黑盒 LLM。

**Independent Test**：输入 query "固态电池 2024 进展" → 等 5 秒内看到 topic 列表 chip UI → 增删一个 topic → 点确认 → 看到 Researcher 启动。

**Acceptance Scenarios**：

1. **Given** 用户在前端输入 query，**When** 后端收到消息并调 Planner，**Then** Planner 在 5 秒内输出 3-7 个 sub-task（带 `description` / `search_queries` / `expected_sources` / `depends_on`），且每个 sub-task 都有 ≥ 1 个搜索词。
2. **Given** Planner 输出 3-7 个 sub-task，**When** 后端进入 `topic_review` 节点调 `interrupt()`，**Then** 前端 SSE 收到 `event: interrupt` 事件，含 `data.topics`（topic 列表）+ `data.operations`（`add` / `delete` / `edit`）+ `data.skip_available: true`。
3. **Given** 前端收到 `interrupt` 事件，**When** 用户编辑 topic（如删除"政策"、新增"学术论文"），**Then** 前端 `POST /threads/{id}/resume` body 含 `topics: [...]` + `skip: false`，后端 `Command(resume=...)` 恢复 graph 并更新 `state["plan"]`。
4. **Given** 用户编辑 topic 后点确认，**When** 后端处理 resume，**Then** `state["plan"]` 含更新后的 sub-task 列表（新增的"学术论文"在内），且 `current_subtask_id` 被设置到第一个 pending sub-task。
5. **Given** 用户在 topic 审阅 UI 点 Skip，**When** 后端收到 `resume={skip: true}`，**Then** `state["plan"]` 保持 Planner 原始输出，直接进入 Researcher。
6. **Given** Planner 输出 > 20 个 sub-task（边界），**When** 后端进入 `topic_review` 节点，**Then** 节点 MUST 拒绝并返回 HTTP 400 + 错误信息 "topic 数量超过上限 20"；不调 `interrupt()`。

---

### User Story 2 - Researcher 检索 + 摘要 + Sources 面板（Priority: P1）

确认 topic 后，Researcher 对每个 sub-task 循环调 `web_search`（Bailian DashScope）+ `fetch_page`（trafilatura + SSRF 白名单）+ LLM 摘要，累加所有来源到 `state["sources"]`，前端 Sources 面板实时显示（url / title / score / excerpt）。

**Why this priority**：Researcher + Sources 是 M2 demo 第 4-5 步（实际检索 + 累加来源），是 M2 的"输出价值"——用户能看到 Planner 拆的方向被实际搜到内容填充；M3 Writer 写 draft 依赖 `state["sources"]` 完整。

**Independent Test**：点确认 topic → 等 30 秒内 Sources 面板有 ≥ 3 条来源 → 点任一来源看 excerpt → 刷新页面后 Sources 仍在。

**Acceptance Scenarios**：

1. **Given** `topic_review` 完成 + `current_subtask_id` 设置，**When** Researcher 节点启动，**Then** 按 `current_subtask_id` 取 sub-task，调 `web_search(search_queries)`，获得 top 5 URL。
2. **Given** 获得 5 个 URL，**When** `fetch_page` 节点逐个调取，**Then** trafilatura 抽取正文，**AND** 命中 `SSRF_ALLOWLIST` 的域名直接通过，**AND** 未命中白名单的域名返回空 + 警告日志（"SSRF blocked: <url>"）。
3. **Given** 5 个 URL 抓取完成，**When** LLM 摘要节点对每页生成 200-500 字 excerpt，**Then** 输出 `SourceItem` 列表（含 `id` / `url` / `title` / `excerpt` / `score` / `fetched_at` / `used_in_subtask`）。
4. **Given** 一个 sub-task 处理完成，**When** `decide_next` 节点判断，**Then** 若有 pending sub-task 则 `current_subtask_id` 移到下一个并跳回 `search` 节点，**OR** 若 `iteration >= MAX_RESEARCH_ITERATIONS (5)` 则强制跳 END 兜底。
5. **Given** Researcher 累加来源，**When** 新 `SourceItem` 列表追加到 `state["sources"]`，**Then** URL 重复的去重（按 `url` 哈希），**AND** 前端 SSE 收到 `event: state_update` `data.sources` 增量更新。
6. **Given** Sources 面板渲染，**When** 用户在前端查看，**Then** 看到所有来源的 url / title / score / excerpt 字段，**AND** 来源按 `score` 降序排列，**AND** 重复 URL 仅显示 1 条。
7. **Given** Bailian `web_search` 返回限流错误（HTTP 429），**When** `web_search` 节点处理，**Then** 重试 2 次指数退避（1s / 2s），**AND** 第 3 次仍失败则 `state["sources"]` 不变 + 错误日志 + 跳过该 sub-task。

---

### User Story 3 - BaseAgent 抽象 + web_search / fetch_page 工具 + SSRF 白名单（Priority: P1）

后端实现 `BaseAgent` 模板方法（`build_user_prompt` / `post_process` / `llm_with_struct` / `__call__`），让 Planner / Researcher / Writer(M3) / Critic(M3) 4 个 Agent 共享 LLM 调度、Langfuse 装饰、错误处理；同时实现 `web_search` + `fetch_page` 两个工具，含 SSRF 白名单 + 2 次指数退避重试。

**Why this priority**：BaseAgent + tools 是 M2 4 个 US 的"基础底座"——没有 BaseAgent 模板方法，US-1/US-2 就要重复写 LLM 调用、Langfuse 装饰、错误处理；没有 tools，US-2 检索无从跑。SSRF 白名单是 constitution I（Security-First）强制要求（外部输入 MUST 经过白名单校验）。

**Independent Test**：写一个 fixture Agent 继承 BaseAgent → 调 `__call__` → 看到 Langfuse span + LLM 输出 + post-process 结果；写一个 `fetch_page` 单测，传入 `SSRF_ALLOWLIST` 之外 URL → 看到 SSRF 拦截。

**Acceptance Scenarios**：

1. **Given** `app/agents/base.py` 定义 `BaseAgent` 抽象类，**When** Planner / Researcher 继承，**Then** 只需实现 `build_user_prompt` + `post_process` + `model_role`，**AND** `__call__` 由父类统一处理（`llm_with_struct` → `@observe_agent` → post-process → state update）。
2. **Given** `BaseAgent.__call__` 执行，**When** LLM 调 `llm_with_struct(PlanOutput)`，**Then** 输出是 `PlanOutput` 实例（含 `subtasks: List[SubTask]` + `reasoning: str`），**AND** Pydantic 校验失败时抛 `ValidationError` + 写 Langfuse 错误 span。
3. **Given** `app/tools/web_search.py` 实现，**When** 调用 `web_search("固态电池 2024")`，**Then** 调 Bailian DashScope `web_search` API（`DASHSCOPE_API_KEY` env），**AND** 返回 top 5 URL 列表（每条含 `url` / `title` / `snippet`），**AND** HTTP 429 时重试 2 次（1s / 2s 退避），**AND** 第 3 次仍 429 抛 `RateLimitError`。
4. **Given** `app/tools/fetch_page.py` 实现，**When** 调用 `fetch_page("https://example.com/article")`，**Then** 读 `SSRF_ALLOWLIST` env（CSV 格式），**AND** 命中 allowlist 的域名 → trafilatura 抽取正文，**AND** 未命中 → 返回空 + 警告日志 + 不抛异常（让 Researcher 跳到下一条）。
5. **Given** `SSRF_ALLOWLIST` env 未设，**When** `fetch_page` 启动时初始化，**Then** 默认 allowlist = M2 spec §Assumptions 列出的 30 条主流新闻/学术/政府域名（如 wikipedia.org / nature.com / arxiv.org / .gov.cn / xinhuanet.com / reuters.com / bloomberg.com 等），**AND** 测试可通过 `SSRF_ALLOWLIST=mock.test,example.com` 覆盖。
6. **Given** `fetch_page` 调 trafilatura 抽取，**When** 抽取失败（页面 JS 渲染 / 反爬），**Then** 记录失败 URL 到 Langfuse span（`status=failed`），**AND** Researcher 跳到下一条 URL，**AND** 不阻塞整个 sub-task。

---

### User Story 4 - PR 门禁扩展（contract test + 关键路径新增）（Priority: P2）

M2 在 M1 8-job PR 门禁基础上扩展：(1) 新增 `contract-check` job（OpenAPI parity check）；(2) 关键路径从 M1 的 4 条扩展为 M2 的 5 条（新增"外部 API 调用 + SSRF 拦截"路径）。

**Why this priority**：constitution VI（API Contract 优先）要求契约变更前先更新契约测试；M1 留的 `tests/contract/` 占位未做（`lib/types.ts:9` 引用了但目录不存在），M2 必须补上；同时覆盖 M1 已知债务（coverage 70.51% < 80%）。M2 demo Day 5 跑通依赖 PR 门禁全绿。

**Independent Test**：故意改 `lib/types.ts` 的 `SSEEvent` 类型（与 openapi.yaml 不一致）→ 提交 PR → `contract-check` job 失败；改回一致 → 通过。

**Acceptance Scenarios**：

1. **Given** `tests/contract/test_openapi.py` 创建，**When** pytest 跑 `tests/contract/`，**Then** 验证 (a) `openapi.yaml` 的 `SSEEvent` 4 种 type（`message` / `state_update` / `done` / `error`）在 `app/api/schemas.py` 的 Pydantic model 中存在且字段一致，**AND** (b) `openapi.yaml` 的 `InterruptEvent` 在 M2 实施后 schema 一致，**AND** (c) `lib/types.ts` 的 TS 类型与 openapi.yaml 字段一一对应（手工或 `openapi-typescript` 生成）。
2. **Given** 故意修改 `lib/types.ts` 把 `SSEEvent.message_id: string` 改为 `SSEEvent.message_id: number`，**When** pytest 跑，**Then** `tests/contract/test_openapi.py` 必失败（schema 不一致），**AND** CI 阻断合并。
3. **Given** `.github/workflows/ci.yml` 8-job 变 9-job，**When** 加 `contract-check` job，**Then** 跑 `pytest tests/contract -v`，**AND** 5 分钟内完成，**AND** 失败阻断 merge。
4. **Given** 关键路径 5 条定义（见 SC-006），**When** `pytest --cov=app --cov-fail-under=80` 跑，**Then** 5 条路径都 ≥ 80% 行覆盖，**AND** 修复 M1 已知债务（routes.py 35% 拉低）至 ≥ 80%。
5. **Given** `bandit` / `pip-audit` / `gitleaks` SAST/SCA 扫描，**When** PR 含高危漏洞（如 `subprocess.call(shell=True)`），**Then** CI 阻断合并（constitution I 强制）。

---

### User Story 5 - 关键路径测试 / 限流 runbook / docs 增量（Priority: P2）

M2 实施配套交付：(1) 关键路径 5 条 ≥ 80% 覆盖率（M1 已知债务修复）；(2) `runbooks/llm-ratelimit.md` 应急手册（Bailian 限流 + Tavily 备选）；(3) docs SDD 增量（`docs/spec-kit-mapping.md` §5.3 已在 M1 写 M2 流程，复用即可）；(4) `docs/milestones.md` §M3 留白 + kickoff placeholder。

**Why this priority**：constitution III 要求关键路径测试覆盖率 ≥ 80%，M1 实际 70.51% 是不合规债务，M2 实施时必须补；runbook 是 constitution I（Security-First）+ VII（可观测性）的兜底文档；docs 增量保证 M3 kickoff 有据可循。

**Independent Test**：跑 `pytest --cov=app --cov-fail-under=80` → 全绿；打开 `runbooks/llm-ratelimit.md` → 看到 Bailian 限流 3 种降级方案。

**Acceptance Scenarios**：

1. **Given** `pytest --cov=app` 跑测试，**When** 关键路径 5 条（SC-006）都覆盖，**Then** 总覆盖率 ≥ 80%（修复 M1 债务 + 新增 M2 路径），**AND** `pytest --cov-fail-under=80` 退出 0。
2. **Given** `runbooks/llm-ratelimit.md` 创建，**When** 团队读，**Then** 包含 (a) Bailian `web_search` 限流检测（HTTP 429），(b) 3 种降级方案（重试 / 切 Tavily / 走 cached sources），(c) oncall 联系人 + 升级路径，**AND** M2 集成日手测 1 次：mock 限流 → 走 Tavily 兜底 → 完整 5 路径跑通。
3. **Given** `docs/milestones.md` §M3 段存在，**When** M2 集成日完成，**Then** §M3 sprint planning 留白（与 M2 模式一致：owner 矩阵 + Day 1-5 + 工时）+ M3 kickoff 引用 `docs/spec-kit-mapping.md` §5.3 流程。
4. **Given** `docs/architecture.md` / `docs/agent-design.md` / `docs/graph-design.md` 已 M1 就绪，**When** M2 实施时引用，**Then** 不修改 M1 文档（constitution V "Owner 变更走 RFC"），M2 增量仅写 `runbooks/llm-ratelimit.md`。
5. **Given** M2 集成日 demo 录视频，**When** 视频包含（query 输入 → Planner 真拆任务 → topic HITL → Researcher 真检索 → Sources 面板），**Then** 视频保存到 `docs/demo/m2-demo.mp4` 或外部链接，**AND** README §M2 状态更新为"✅ v1.0.0-M2"。

---

## Edge Cases

- **Planner 输出 0 个 sub-task**：用户 query 极短或无法拆解时 Planner 返回空 → 后端 MUST 抛 `PlannerEmptyError` + 写 Langfuse 错误 span + 返回 HTTP 422 + 友好错误"无法拆解您的查询，请补充上下文"。
- **Planner 输出 > 20 个 sub-task**：超过 topic chip 上限 → topic_review 节点 MUST 拒绝 + 返回 HTTP 400 + 不调 interrupt()；用户须调整 query 重试。
- **LLM 输出 schema 非法**（Planner Pydantic 校验失败）：BaseAgent MUST 捕获 `ValidationError` + 重试 1 次（用同样 prompt），**AND** 第 2 次仍失败则抛 `LLMSchemaError` + 写 Langfuse 错误 span + 提示用户重试。
- **Bailian `web_search` 持续限流**（3 次重试都 429）：`web_search` 抛 `RateLimitError` + Researcher 跳过该 sub-task + 错误日志"web_search rate-limited, skipping subtask"；不停整个 plan。
- **Bailian `web_search` API key 缺失**：启动时 `app/llm/router.py` 必检测 `DASHSCOPE_API_KEY` env，缺失 MUST 抛 `ConfigurationError` + 友好错误（不依赖 LLM 启动期的话用 mock 兜底）。
- **`fetch_page` 命中 SSRF 黑名单**：未在 `SSRF_ALLOWLIST` 的域名 → 返回空 `SourceItem` + 警告日志"SSRF blocked: <url>"；不抛异常，让 Researcher 继续下一条。
- **`fetch_page` trafilatura 抽取失败**（页面 JS 渲染 / 反爬）：记录失败 URL + 跳过；不阻塞整个 sub-task。
- **interrupt 丢失 resume**（前端 crash / 网络断）：LangGraph checkpointer 持久化中断状态，30 分钟内用户重连可继续；超时后 MUST 标记 thread 为 `interrupted_expired` + 提示用户重开 thread。
- **并发同 thread**：M1 已实现 LangGraph 线程隔离（thread_id 区分 config），M2 继承 + interrupt 阶段也按 thread_id 隔离；同一 thread 的并发 resume MUST 拒绝（后写入的 409）。
- **cookie 失效 / 越权**：M1 FR-011a 匿名 cookie 隔离；M2 继承 + interrupt 恢复时 MUST 校验 user_id 与 thread 拥有者一致，**AND** 不一致 MUST 拒绝 + 返回 HTTP 403。
- **Researcher 死循环**：超过 `MAX_RESEARCH_ITERATIONS=5` → `decide_next` 强制跳 END + 警告日志"research iteration limit reached, ending researcher early"。
- **多 sub-task 同 URL 去重**：Researcher 累加 sources 时按 `url` 哈希去重；同一 URL 不重复入 `state["sources"]`。
- **OpenAPI schema 不一致**（手工改了 `lib/types.ts` 未同步 openapi.yaml）：`tests/contract/test_openapi.py` 必失败 + CI 阻断（constitution VI 强制）。
- **M1 已知债务 - coverage 70.51% < 80%**：M2 实施时 MUST 修复（routes.py 加 integration test 补 80%+）；Converge-Gate #7 必绿。

---

## Requirements

### Functional Requirements

**LangGraph 编排（State + Graph + Sub-graph）**
- **FR-001**：系统 MUST 在 `app/graph/state.py` 扩展 `AgentState` 5 个新字段（`query` / `research_brief` / `plan` / `current_subtask_id` / `sources`），M1 已有 3 字段（`messages` / `user_id` / `thread_id`）不变。
- **FR-002**：系统 MUST 在 `app/graph/graph.py` 注册新节点：`planner`（拆任务） / `topic_review`（HITL interrupt） / `researcher`（sub-graph） / `cl_writer` 暂用 stub（M3+ 才真实现 Writer）。
- **FR-003**：系统 MUST 实现 Researcher sub-graph（`app/graph/researcher_subgraph.py`），含 4 节点：`search` / `fetch` / `summarize` / `decide_next`；`decide_next` 用 `add_conditional_edges` 跳回 `search` 或 END。
- **FR-004**：系统 MUST 在 `topic_review` 节点用 `langgraph.types.interrupt()` 暂停 graph，等待用户 resume；用户响应后 MUST 用 `Command(resume=...)` 恢复。

**Agent 层（Planner + Researcher + BaseAgent）**
- **FR-005**：系统 MUST 实现 `app/agents/planner.py`，含 `Planner(BaseAgent)` 类 + `model_role="planner"`；`build_user_prompt` 返回 Planner system prompt + 用户 query；`post_process` 把 `PlanOutput.subtasks` 写入 `state["plan"]` + 初始化每个 `status="pending"`。
- **FR-006**：系统 MUST 实现 `app/agents/researcher.py`，含 `Researcher(BaseAgent)` 类 + `model_role="researcher"`；`post_process` 把 `ResearcherOutput.sources` 追加到 `state["sources"]`（去重 by URL 哈希）+ 更新 `current_subtask_id`。
- **FR-007**：系统 MUST 实现 `app/agents/base.py` 模板方法升级：抽象方法 `build_user_prompt` / `post_process` / `model_role`；具体方法 `__call__`（`llm_with_struct` → `@observe_agent` → `post_process` → state update）+ `llm_with_struct`（用 `ChatOpenAI.with_structured_output(PlanOutput)` 等）。
- **FR-008**：系统 MUST 实现 `app/agents/prompts.py` 集中放 Planner / Researcher / 未来 Writer / Critic 的 system prompt 字符串。
- **FR-009**：系统 MUST 实现 `app/agents/schemas.py` 含 `SubTask` / `PlanOutput` / `SourceItem` / `ResearcherOutput` 4 个 Pydantic model（与 `docs/agent-design.md` §3.1/§3.2 schema 1:1）。
- **FR-010**：系统 MUST 实现 `app/agents/clarifier.py` 的最小版本（M2 只做 `topic_review` interrupt，`clarify_with_user` 节点为占位 M3+ 才真实现）。

**Tools 层（web_search + fetch_page + SSRF）**
- **FR-011**：系统 MUST 实现 `app/tools/web_search.py` 调 Bailian DashScope `web_search` API（`DASHSCOPE_API_KEY` env）；返回 top 5 URL 列表；HTTP 429 时重试 2 次指数退避（1s / 2s）；第 3 次仍失败抛 `RateLimitError`。
- **FR-012**：系统 MUST 实现 `app/tools/fetch_page.py` 调 trafilatura 抽取 + 读 `SSRF_ALLOWLIST` env（CSV 格式）；命中白名单通过 + 未命中返回空 + 警告日志；trafilatura 失败记录错误 URL + 跳过。
- **FR-013**：系统 MUST 在 `app/llm/router.py` 创最小版 LLM router（单 `model_role` 映射到单 `provider`）；M3+ 扩展为 multi-model routing。
- **FR-014**：系统 MUST 实现 `app/auth/anonymous.py`（M1 留白未做）+ `app/ratelimit/limiter.py`（M1 FR-011b 部分实现，M2 必填）；M2 必做理由：interrupt resume 路由的 user_id 越权校验依赖这两个。

**SSE / OpenAPI 扩展**
- **FR-015**：系统 MUST 扩展 `specs/002-m2-research/contracts/openapi.yaml` 到 v0.2.0-m2：新增 (a) `InterruptEvent` schema（含 `data.type: clarify|topic_review`、`data.questions` / `data.topics` / `data.operations` / `data.skip_available`），(b) `state_update.data` 新增 5 字段（`query` / `research_brief` / `plan` / `current_subtask_id` / `sources`），(c) `POST /threads/{id}/resume` 路由（含 `Request Body: { skip: bool, topics: [...] }` + `Response: SSE`）。
- **FR-016**：系统 MUST 在 `app/api/routes.py` 加 `POST /threads/{id}/resume` 路由：body 校验 + 越权 user_id 校验 + 调 `graph.astream(Command(resume=body), config={"configurable": {"thread_id": ...}})` + 返回 SSE 流。
- **FR-017**：系统 MUST 同步扩展 `app/api/schemas.py` Pydantic model（`InterruptEvent` / `ResumeRequest` / `SourceItem` / `SubTask`）以匹配 openapi.yaml v0.2.0-m2。
- **FR-018**：系统 MUST 同步扩展 `research_frontend/lib/types.ts` TS 类型以匹配 openapi.yaml v0.2.0-m2（手动维护 + `tests/contract/test_openapi.py` 验证）。

**前端（Plan + Sources 面板 + Topic 审阅 HITL UI）**
- **FR-019**：系统 MUST 新增 `research_frontend/components/plan-panel/`，展示 `state["plan"]`（sub-task 列表 + status badge）。
- **FR-020**：系统 MUST 新增 `research_frontend/components/sources-panel/`，展示 `state["sources"]`（url / title / score / excerpt），按 `score` 降序。
- **FR-021**：系统 MUST 新增 `research_frontend/components/topic-review/`，收到 `interrupt` 事件后弹 chip UI（add / delete / edit + Skip 按钮 + Confirm 按钮），用户编辑后调 `POST /threads/{id}/resume`。
- **FR-022**：系统 MUST 扩展 `research_frontend/lib/store.ts` Zustand store：新增 `plan` / `sources` / `interrupt` 状态 + SSE event handler。

**Contract test + Converge-Gate 扩展**
- **FR-023**：系统 MUST 创建 `tests/contract/test_openapi.py`，验证 (a) `openapi.yaml` 的 schemas 与 `app/api/schemas.py` 100% 一致，**AND** (b) `lib/types.ts` 字段与 openapi.yaml 一致。
- **FR-024**：系统 MUST 在 `.github/workflows/ci.yml` 新增 `contract-check` job（跑 `pytest tests/contract -v`），与 M1 8-job 共 9-job。
- **FR-025**：关键路径 5 条 MUST 覆盖 ≥ 80%（constitution III 强制；修复 M1 已知债务 routes.py 35%）。

**Spec / Owner 引用**
- **FR-026**：本 spec 文档 MUST 显式声明 `Owner:` 字段（constitution V）— TL.cai 单人。
- **FR-027**：每次 PR MUST 在描述中引用 spec ID `FEATURE-002-m2-research`（constitution II）。
- **FR-028**：M2 集成日 demo 录视频 MUST 保存到 `docs/demo/m2-demo.mp4` 或外部链接，README §M2 状态更新为"✅ v1.0.0-M2"。

### Key Entities

- **Plan（研究计划）**：Planner 输出的结构化 sub-task 列表，含 `subtasks: List[SubTask]`（每条含 `id` / `description` / `search_queries` / `expected_sources` / `depends_on` / `status: pending|running|done|failed`）+ `reasoning: str`（拆分思路）。
- **SubTask（子任务）**：单个研究子任务，Planner 输出 + Researcher 执行单位；状态机：`pending → running → done|failed`。
- **Source（检索来源）**：Researcher 检索结果单条记录，含 `id` / `url` / `title` / `excerpt`（200-500 字）/ `score`（0-1 相关度）/ `fetched_at`（ISO 8601）/ `used_in_subtask: str`。
- **Interrupt（中断事件）**：HITL 暂停事件，LLM 调用 `interrupt({type, ...})` 触发，front-end 收到后弹 UI；恢复时 `Command(resume=user_reply)` 继续 graph。
- **ResearchBrief（研究方向）**：M3+ 才实现的"已澄清研究方向"对象（scope / time range / audience / depth）；M2 暂为可选字段，topic_review 节点填入 `state["research_brief"]`。

---

## Success Criteria

### Measurable Outcomes

- **SC-001**：用户输入 query 到 Planner 输出 sub-task 列表的端到端延迟 ≤ 5 秒（含 LLM 推理 + Pydantic 校验 + Langfuse span 写入）。
- **SC-002**：用户输入 query 到 Sources 面板首次显示来源的端到端延迟 ≤ 30 秒（含 3-7 个 sub-task 的 web_search + fetch_page + summarize 串行处理）。
- **SC-003**：Topic 审阅 UI 弹出响应时间 ≤ 500ms（`interrupt()` 调用 → SSE 推送 → 前端渲染）。
- **SC-004**：Topic 审阅 HITL `interrupt` 恢复成功率 = 100%（用户点确认后 MUST 100% 进入 Researcher；M2 集成日手测 10 次全成功）。
- **SC-005**：Sources 面板可见率 = 100%（每次 Researcher 完成 plan 后 MUST 看到 ≥ 3 条来源；M2 集成日手测 5 次全成功）。
- **SC-006**：关键路径测试覆盖率 ≥ 80%（constitution III 强制门禁）。M2 阶段关键路径 = **5 条**（M1 4 条 + 新增"外部 API 调用 + SSRF 拦截"）：
  - 路径 1：query 提交 → Planner 真拆任务 → topic_review interrupt + resume（提交 → cookie 校验 → 限流校验 → langgraph planner 节点 → interrupt → /resume 路由 → state update）
  - 路径 2：Researcher sub-graph 循环（search → fetch → summarize → decide_next，命中 SSRF 白名单 / 重试 / 去重）
  - 路径 3：user_id 越权隔离（FR-011a + interrupt resume 路由的 user_id 校验）
  - 路径 4：可观测性 trace 写入（Langfuse `as_type="generation"` 装饰 + Planner/Researcher 节点 span）
  - 路径 5：外部 API 调用 + SSRF 拦截（Bailian `web_search` 重试 2 次 + `fetch_page` SSRF 白名单 + trafilatura 失败兜底）
- **SC-007**：本地 `task backend:test` 跑通率 100% 且结果与 CI 一致；测试数 ≥ 150（含 M1 114 + M2 新增 ≥ 36：planner / researcher / web_search / fetch_page / interrupt / resume / contract test 等）。
- **SC-008**：本地 `task frontend:test` 跑通率 100%；测试数 ≥ 15（含 M1 7 + M2 新增 ≥ 8：plan-panel / sources-panel / topic-review chip UI / SSE interrupt handler）。
- **SC-009**：PR 流水线在 12 分钟内完成（9 jobs：M1 8 + contract-check）；ci.yml 9 jobs 全绿后 MUST 可合并。
- **SC-010**：M2 端到端 demo 在集成日 1 次跑通；含真实 LLM 跑通（query → Planner 真拆任务 → topic HITL → Researcher 真检索 → Sources 面板），团队对单人开发 + 真 LLM demo 体验评分 ≥ 4/5。
- **SC-011**：M1 已知债务 #7 coverage 70.51% < 80% MUST 修复至 ≥ 80%（M2 集成日 `pytest --cov-fail-under=80` 退出 0）。
- **SC-012**（新增）：OpenAPI parity check 通过率 100%（`tests/contract/test_openapi.py` 与 `lib/types.ts` 字段 100% 一致；故意改坏 schema 必失败）。
- **SC-013**（新增）：interrupt 恢复成功率 = 100%（M2 集成日手测 10 次，10 次都能从中断恢复到 Researcher 完成）。
- **SC-014**（新增）：跨用户隔离正确率 = 100%（用户 A 在 cookie 隔离下无法通过猜测 thread_id resume 用户 B 的中断；M2 集成日手测 5 次跨用户尝试全部失败）。
- **SC-015**（新增）：限流生效正确率 = 100%（M1 SC-012 继承 + interrupt resume 路由的限流同步生效；M2 集成日手测 1 次）。

---

## Assumptions

- **目标用户**：hochoy 内部研发人员（3 个团队的工程师）+ 内部测试用户（demo 阶段）；M2 仍是研发自用，**不上线**。
- **运行环境**：本地 macOS 14+ / Linux 容器；M2 集成日 demo 需 `DASHSCOPE_API_KEY` 或 `OPENAI_API_KEY`（用户 env 注入）；CI 测试用 `LLM_MOCK=1` 走 mock fixture。
- **范围边界**：M2 仅做检索阶段（Planner + Researcher + web_search + fetch_page + topic HITL）；写作 / Critic / 评估留 M3 / M4。
- **范围边界**：M2 仍无鉴权（v1 不接，详见 ADR-0009），interrupt resume 路由只校验 user_id 与 thread 拥有者一致（不要求登录）。
- **数据保留**：M2 阶段对话历史保留 ≥ 7 天（依赖状态检查点 TTL）；`state["sources"]` 长期存储在 M4 评估阶段补齐。
- **依赖**：假设可访问 Bailian DashScope `web_search` API（或 OpenAI-compatible provider）；M2 不引入 Tavily（兜底写 runbook）。
- **依赖**：trafilatura 可处理主流新闻 / 学术 / 政府网站；对 JS 渲染的 SPA 抽取失败可接受（fallback 警告日志 + 跳过）。
- **M2 LLM mock 兜底**：`LLM_MOCK=1` env 启用 mock fixture（固定输入→固定输出）；M2 单元测试 + CI 全用 mock；M2 集成日手测可切真 LLM。
- **M2 critical path 5 条定义**：见 SC-006；M1 4 条继承 + 新增"外部 API 调用 + SSRF 拦截"路径；非关键路径（UI 装饰 / 日志格式化）豁免（constitution III 豁免）。
- **Topic chip 上限 20**：硬编码（v1 简化）；如用户想扩到 50+ 走 M3+ 评估。
- **MAX_RESEARCH_ITERATIONS=5**：与 agent-design §3.2 一致；Researcher sub-graph 兜底防死循环。

---

## Out of Scope（M2 不做）

- Writer / Critic Agent 完整实现（M3）
- Draft 流式生成 / Draft 审阅 HITL（M3）
- cite 工具（M3）
- Markdown / PDF 导出（M3）
- LLM-as-judge 评估 / HotpotQA（M4）
- 鉴权 / 权限（v1 不接，详见 ADR-0009）
- `clarify_with_user` 节点（research_brief 澄清）— M2 仅做 `topic_review`，research_brief 字段为可选占位
- Milvus / MinIO（向量缓存 / 对象存储）— M3 启动时再加
- 移动端 / 多语言
- 生产部署（M2 仍仅本地演示 + 集成日 demo）
- Tavily 等其他 web_search provider（M2 只接 Bailian；Tavily 兜底写进 runbook 不实现）

---

## Dependencies

### 设计文档（已就绪）

- [`docs/milestones.md`](../../docs/milestones.md) §M2 端到端 demo + 5 交付 + 风险表
- [`docs/architecture.md`](../../docs/architecture.md) §2 组件全景 + §3 组件职责（M2 新增 tools / llm router）
- [`docs/agent-design.md`](../../docs/agent-design.md) §2 BaseAgent 抽象 + §3.1 Planner + §3.2 Researcher
- [`docs/graph-design.md`](../../docs/graph-design.md) §3 Researcher sub-graph + §4 HITL interrupt（含 topic_review 节点 + /resume 路由契约）
- [`docs/observability.md`](../../docs/observability.md) Langfuse OTel 集成（`@observe_agent(as_type="generation")` for LLM nodes）
- [`docs/deployment.md`](../../docs/deployment.md) 部署（M2 不加新容器，web_search 走公网 / fetch_page 走本地）
- [`docs/contributing.md`](../../docs/contributing.md) commit 规范 / PR 流程

### 决策依据（12 篇 ADR，已就绪）

- [ADR-0001 LangGraph over alternatives](../../docs/adr/0001-langgraph-over-alternatives.md)
- [ADR-0002 Bailian `web_search` over Tavily](../../docs/adr/0002-bailian-web-search-over-tavily.md)
- [ADR-0003 Postgres + Redis + MinIO 5 服务](../../docs/adr/0003-postgres-redis-minio.md)
- [ADR-0004 single-repo over monorepo](../../docs/adr/0004-single-repo-over-monorepo.md)
- [ADR-0005 LangChain classic + LangGraph 1.2+](../../docs/adr/0005-langchain-classic-langgraph.md)
- [ADR-0006 Langfuse self-hosted OTel API](../../docs/adr/0006-langfuse-self-hosted-otel.md)
- [ADR-0007 Tailwind v4 CSS-first](../../docs/adr/0007-tailwind-v4-css-first.md)
- [ADR-0008 trunk-based over git-flow](../../docs/adr/0008-trunk-based-over-git-flow.md)
- [ADR-0009 v1 no auth](../../docs/adr/0009-v1-no-auth.md)
- [ADR-0010 HITL clarify with interrupt](../../docs/adr/0010-hitl-clarify-with-interrupt.md)
- [ADR-0011 multi-model task routing](../../docs/adr/0011-multi-model-task-routing.md)
- [ADR-0012 Python 3.12](../../docs/adr/0012-python-3.12.md)

### 治理

- [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.1.0（8 大原则 + CI Gates）

### 上游依赖（M1 交付）

- `app/main.py` + SSE 路由 + `/threads` CRUD 接口
- `app/agents/echo.py`（M1 mock 流式响应；M2 不删除作为 mock 兜底）
- Langfuse OTel 基础配置（`app/observability/langfuse.py` 的 `@observe_agent` 装饰器 M2 复用 + 切 `as_type="generation"`）
- Redis checkpointer + Postgres schema 基础（M1 FR-007 / FR-008）
- 前端 `app/page.tsx` 两栏布局 + `lib/api.ts` SSE client + `lib/store.ts` Zustand 基础
- `app/auth/anonymous.py` 留白待 M2 创建（Dev.cai.4 债务）

---

## Constitution 对齐

| 原则 | M2 落地方式 |
|---|---|
| **I. Security-First** | SSRF `SSRF_ALLOWLIST` env 白名单（`fetch_page` 强校验）+ Bailian `web_search` 重试 + 限流 + audit log（user_id / thread_id / reason）+ `app/auth/anonymous.py` 越权拦截 + 9-job CI 含 bandit + pip-audit + gitleaks |
| **II. Spec-Traceable** | 本 spec 显式声明 `Owner: TL.cai` + `Feature ID: FEATURE-002-m2-research`；PR 模板 `Spec:` 字段必填；M2 集成日自检 spec-link |
| **III. Test-First** | TDD 红绿重构循环；关键路径 5 条 ≥ 80%（SC-006）；`tests/contract/test_openapi.py` OpenAPI parity check；M1 已知债务 routes.py 35% 修复至 ≥ 80% |
| **IV. Converge-Gate** | M2 集成日 Converged 6 子条件全绿：(1) spec 落库（本文），(2) plan 落库（Phase C），(3) tasks 全 Closed（Phase F），(4) checklist 16 项 PASS（Phase E），(5) `/speckit-analyze` 无未对齐，(6) CI 9-job + coverage ≥ 80% + SAST/SCA/Pact pass |
| **V. One-Feature-Owner** | 本 spec 显式声明 `Owner: TL.cai`（constitution V 要求）；M2 单人模式不分 Co-Owner；变更走 RFC（M2 不改） |
| **VI. API Contract** | OpenAPI v0.2.0-m2 增量（interrupt event + /resume route + state 5 字段）；`tests/contract/test_openapi.py` parity check 强制；`lib/types.ts` 同步；不引 Pact 框架（轻量 parity 即可） |
| **VII. Observability by Default** | Langfuse `@observe_agent(as_type="generation")` 装饰 Planner + Researcher + 关键工具节点；`/metrics` Prometheus 端点（M1 stub，M2 补全基础 4 指标）；structured JSON logs 8 必填字段（继承 M1） |
| **VIII. 简洁优先** | 模块化单体（继承 M1）；BaseAgent 模板方法只抽 4 个 Agent 共性，不做 4 抽象层；tools 包最小接口（`web_search` / `fetch_page`）；YAGNI（topic chip 上限硬编码 20 而非可配置） |
