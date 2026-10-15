# Milestones（M1–M4 占位文件）

> 本文档是 M1–M4 的**总目标 / 端到端 demo / 依赖 / 风险**的固化文件。Sprint planning（owner 分配、Day 1–5 任务表、工时）**不在此处**，由各 milestone 启动前的 kickoff 决定。

---

## 总时间表

| 周   | Milestone | 一句话目标                                                                | 端到端 demo                              |
| ---- | --------- | ------------------------------------------------------------------------- | ---------------------------------------- |
| W1   | **M1**    | 脚手架：FastAPI + Next.js 骨架 + docker-compose + CI + Langfuse trace 接入 | `task dev:up` 一键起所有服务，浏览器看对话流 |
| W2   | **M2**    | 检索：Planner + Researcher + web_search + fetch_page + Plan/Sources 面板  | 输入 query → Planner 拆任务 → 用户审 topic → Researcher 搜 + 抓 → Sources 面板可见 |
| W3   | **M3**    | 写作：Writer + Critic + cite + Markdown/PDF 导出 + Draft 审阅 HITL        | M2 demo + Writer 流式生成 draft + Critic 改稿 1–2 次 + 导出 PDF |
| W4   | **M4**    | 验收：Eval pipeline + CI/CD + 安全 + 异常降级 + v1 demo                   | 完整 v1 流程 + HotpotQA 10 题跑通 + Langfuse trace + LLM-as-judge score + PDF 报告 |

**总时间**：4 周 / 4 人并行 / 每周 5 天（4 天并行 + 1 天集成 demo）。

---

## M1 - 基础设施（W1）

### 总目标
FastAPI + Next.js 骨架 + docker-compose + CI + Langfuse trace 接入，端到端对话流（mock 数据）跑通。

### 端到端 demo
1. `task dev:up` 起所有服务（postgres / redis / langfuse / milvus / minio / backend / frontend）
2. 打开 `http://localhost:3000`，输入 query
3. 后端 SSE 推送 mock 流式响应
4. 前端 EventSource 接收 → Markdown 渲染
5. Langfuse UI (`http://localhost:3001`) 看到本次请求的 trace

### 关键交付
- `research_backend/`：FastAPI + pyproject.toml + Dockerfile + `.env.example`
- `research_frontend/`：Next.js 16 + Tailwind v4 + shadcn + package.json + Dockerfile
- `deploy/docker-compose.yml`：所有依赖服务
- `.github/workflows/ci.yml`：PR 跑 lint + 单测 + 集成测试（mock LLM）
- `Taskfile.yml`：`dev:up` / `dev:down` / `dev:logs` / `backend:test` / `frontend:dev`
- `.pre-commit-config.yaml`：secret scan + ruff + eslint + prettier
- `CODEOWNERS`：按目录划分

### Sprint planning（已完成 — 见 README §M1）
4 人并行 5 天详细拆解在 `README.md` 的"🧪 M1 里程碑"表。

### 关键风险
| 风险 | 影响 | 回退 |
|---|---|---|
| Tailwind v4 与 Next.js 16 兼容问题 | M1 卡住 | 临时降级到 v3.4 |
| Langfuse self-hosted 镜像 OOM | CI 跑不起来 | 给 docker-compose 加 `mem_limit: 2g` |
| 接口契约 freeze 不及时 → C 用错 schema | 集成冲突 | A Day 1 末必须把 OpenAPI schema 提交到 main |

---

## M2 - 检索（W2）

### 总目标
Planner + Researcher + web_search + fetch_page + Plan/Sources 面板，输入 query 后能跑通"拆任务 → 检索 → 摘要"全流程。

### 端到端 demo
1. 用户输入 query（如"固态电池 2024 进展"）
2. Planner 拆出 3-7 个 sub-task（如"消费电子应用 / 动力电池 / 储能 / 政策"）
3. HITL topic 审阅弹出：用户增删改 topic，可点击 [跳过]
4. Researcher 循环：对每个 sub-task 调 web_search + fetch_page + 摘要
5. Sources 面板展示所有来源（url / title / score / excerpt）
6. Langfuse trace 完整可查

### 关键交付
- `app/agents/planner.py` + Planner system prompt（已在 `agent-design.md` §3.1）
- `app/agents/researcher.py` + Researcher system prompt（已在 `agent-design.md` §3.2）
- `app/tools/web_search.py`（Bailian DashScope 接入 + 重试 2 次指数退避）
- `app/tools/fetch_page.py`（trafilatura + SSRF 白名单 + 去广告/导航）
- `app/agents/base.py`（BaseAgent 抽象类 — 4 Agent 共性抽取）
- 前端 `components/plan-panel/` + `components/sources-panel/`
- Topic 审阅 HITL UI（chip 增删改 + Skip）
- Langfuse OTel 接入（已在 `observability.md`）

### Sprint planning（**待 M2 启动前 kickoff 时填**）

> ⚠️ 留白：以下信息在 M1 完成后、M2 Day 1 前由团队 kickoff 决定
>
> - 4 人 Owner 分配（A / B / C / D）
> - Day 1-5 任务表
> - 工时估算（人天）
> - 优先级 / 阻塞关系

### 关键依赖（依赖 M1 的什么）
- M1 提供的 `app/main.py` + SSE 路由 + `/threads` 接口
- M1 提供的 Langfuse OTel 基础配置
- M1 提供的 Redis 连接 + Postgres schema 基础
- M1 提供的前端对话流组件（用于联调）

### 关键风险
| 风险 | 影响 | 回退 |
|---|---|---|
| Bailian `web_search` 限流 / 不稳定 | Researcher 卡住 | 重试 + 备选 search（自研爬虫 / Bing）；短期切 Tavily（成本可控） |
| trafilatura 对某些站点抽取失败 | fetch_page 返回空 | 备选 readability-lxml；记录失败 URL 到日志 |
| BaseAgent 抽象过早抽象 → 4 Agent 共性不够 | 重构成本 | 先各自实现，Day 4 再抽取共性 |
| HITL topic 审阅 UX 不直观 | 用户不用 | 降级为 inline 列表 + check box，v2 升级 |

---

## M3 - 写作（W3）

### 总目标
Writer + Critic + cite + Markdown/PDF 导出 + Draft 审阅 HITL，从 query 到 PDF 全流程跑通。

### 端到端 demo
1. M2 demo 完成 → Researcher 产 sources
2. Writer 流式生成 draft（每个 token 一个 SSE event）
3. Draft 中所有事实性 claim 带 `[N]` 引用编号
4. Critic 检查 → approve / revise_plan / revise_research / revise_draft
5. revise_draft 时弹出 Draft 审阅 HITL：用户编辑 / 要求重写某段 / 通过
6. 通过后生成 PDF 报告（学术风 + 公司 logo + Sources 附录）
7. 导出按钮触发 MinIO 存储 + 下载链接

### 关键交付
- `app/agents/writer.py` + Writer system prompt + 流式输出（已在 `agent-design.md` §3.3）
- `app/agents/critic.py` + Critic system prompt + decision 路由（已在 `agent-design.md` §3.4）
- `app/tools/cite.py`（claim + source_id → `[N]` 编号绑定）
- `app/api/routes.py` 扩展：`POST /export/{thread_id}` 生成 PDF
- 前端 `components/chat/` Markdown 流式渲染 + 引用高亮
- 前端 `components/export/` 导出按钮 + 设置抽屉
- Draft 审阅 HITL UI（编辑 / 重写 / 通过）
- iteration 兜底（强制 approve ≥ 2 次，防止 Critic 无限循环）
- PDF 模板（`md-to-pdf` + puppeteer + 中文支持 + 学术风样式）

### Sprint planning（**待 M3 启动前 kickoff 时填**）

> ⚠️ 留白：
>
> - 4 人 Owner 分配（A / B / C / D）
> - Day 1-5 任务表
> - 工时估算（人天）
> - 优先级 / 阻塞关系

### 关键依赖（依赖 M2 的什么）
- Planner 输出的 `state["plan"]` 结构
- Researcher 输出的 `state["sources"]` 结构
- M2 提供的 Plan / Sources 面板（在 Draft 流式渲染时联动）
- M2 提供的 BaseAgent 抽象（在 Writer / Critic 中复用）

### 关键风险
| 风险 | 影响 | 回退 |
|---|---|---|
| `md-to-pdf` 中文支持不全 | PDF 中文乱码 | 备选 weasyprint（CSS-first）；先做英文 demo |
| Writer 流式 token 中断 | draft 拼接错乱 | 后端 buffer 兜底 + 重试 |
| Critic 改稿次数失控（>2 次） | 用户体验差 | iteration 硬上限 2 次；强制 approve |
| 引用 `[N]` 编号与 Sources 面板映射错位 | 引用无效 | Writer prompt 内置自校验：每个 cite 必须对应 sources 中某条 |
| PDF 生成慢（>30s） | 用户等待 | 异步任务 + 后台生成 + 完成后通知 |

---

## M4 - 验收（W4）

### 总目标
Eval pipeline + CI/CD + 安全 + 异常降级 + v1 demo，HotpotQA 子集跑通，v1 release tag 发布。

### 端到端 demo
1. 跑 `task e2e:hotpotqa` —— HotpotQA 10 题全跑通
2. 每个 thread 在 Langfuse 上有完整 trace + LLM-as-judge score（事实性 / 引用密度 / 覆盖度 / 延迟 / token 成本）
3. 单次研究流 p95 < 5 分钟（从 query 到 PDF）
4. PR 触发 GitHub Actions → lint + 单测 + 集成测试 + 集成 demo
5. merge to main → 自动 push 镜像 + deploy 到 preview
6. 安全：search 结果 sandbox 后 LLM 不被注入；fetch_page 不访问内网
7. 异常降级：LLM 失败自动切备选模型；用户中断可恢复；硬超时保留部分结果

### 关键交付
- `app/eval/datasets.py`：HotpotQA 100 题导入 + 5 题自造
- `app/eval/scorers.py`：LLM-as-judge 6 维（事实性 / 引用密度 / 覆盖度 / 延迟 / token 成本 / 工具失败率）
- `app/eval/run_eval.py`：nightly e2e 触发器（预算 $5）
- `.github/workflows/nightly.yml`：cron 触发 e2e
- `app/security/`：Prompt 注入防护（搜索结果 sandbox）+ SSRF 黑名单 + 密钥管理
- `app/middleware/rate_limit.py`：FastAPI middleware + Redis 计数
- `app/middleware/timeout.py`：10 分钟硬超时
- `deploy/docker-compose.preview.yml`：独立 preview stack（端口 10000+PR_NUM）
- 3 篇 Runbook（已在 `runbooks/`）
- `CHANGELOG.md`：v1.0.0 release notes
- GitHub tag `v1.0.0`

### Sprint planning（**待 M4 启动前 kickoff 时填**）

> ⚠️ 留白：
>
> - 4 人 Owner 分配（A / B / C / D）
> - Day 1-5 任务表
> - 工时估算（人天）
> - 优先级 / 阻塞关系

### 关键依赖（依赖 M3 的什么）
- Writer 输出的完整 draft + 引用映射
- Critic 输出的 critique + decision
- M3 提供的 Draft 审阅 HITL
- M3 提供的 PDF 导出链路

### 关键风险
| 风险 | 影响 | 回退 |
|---|---|---|
| HotpotQA 子集跑不通（>10% 失败） | v1 不达标 | 调整 LLM-as-judge 阈值；先小流量（5 题）跑通再扩 |
| Langfuse self-hosted 在 nightly 流量下 OOM | e2e 中断 | 调高内存到 4g + trace 采样降级 |
| nightly e2e 预算超 $5 | 成本失控 | 加 token 硬上限；mock LLM 跑 |
| v1 release 后线上 bug 紧急 | 无回滚 | 镜像 tag `{git_short_sha}-{build_timestamp}` 保留可回滚点 |
| Prompt 注入绕过事实核查 | 报告失实 | 搜索结果用 system message 隔离 + Critic 二次校验 |

### v1 验收标准（**v1 release 门槛 — 全部满足才发 tag**）
- [ ] HotpotQA 子集 10 个 query 跑通 + PDF 报告生成
- [ ] Critic 改稿平均 < 2 次
- [ ] 单次研究流 p95 延迟 < 5 分钟
- [ ] Langfuse 能看到每个 query 的完整 trace + LLM-as-judge score
- [ ] 前端对话流 + Plan / Sources 面板 + 导出按钮可见
- [ ] `task dev:up` 一键起 v1
- [ ] 3 篇 Runbook 实战演练通过
- [ ] `docs/CHANGELOG.md` 写完 v1.0.0

---

## Milestone 之间的衔接模式

**串行衔接**（推荐）：每个 milestone 完成 → merge to main → 下一个 milestone Day 1 启动。

- **不重叠**：避免多人同时改 main 导致集成冲突
- **每个 milestone 末尾 1 天集成日**：merge + 修 bug + demo 录制
- **M1 → M2**：M1 集成日 demo 通过后，M2 Day 1 开始
- **M2 → M3**：同上
- **M3 → M4**：同上
- **M4 集成日**：v1 release tag + 验收清单勾完

---

## 何时回退 / 调整

每个 milestone 启动前（M1 Day 1 / M2 Day 1 / M3 Day 1 / M4 Day 1）做一次 30 分钟的 kickoff：

1. **回顾上个 milestone 的 demo**：跑一遍，看哪些环节卡顿 / 哪些指标不达标
2. **确认本 milestone 的"做什么"**：对照本文档的"总目标 + 端到端 demo"
3. **细化 sprint planning**：填 Owner 分配 + Day 1-5 任务表 + 工时
4. **更新风险清单**：基于上个 milestone 的发现调整

如果某个 milestone 风险暴露（如 Bailian 限流严重），可考虑：
- 加 buffer 周（v1.5）
- 减少本周任务范围（砍 demo 场景）
- 引入备选方案（如切 Tavily）

---

## 相关文档

- M1 详细拆解 → `README.md` §M1 里程碑
- 4 Agent 设计 → [`agent-design.md`](./agent-design.md)
- LangGraph State / 节点 / HITL → [`graph-design.md`](./graph-design.md)
- 评估设计 → [`eval.md`](./eval.md)
- 部署 / CI → [`deployment.md`](./deployment.md)
- 贡献流程 → [`contributing.md`](./contributing.md)
- 12 篇 ADR → [`adr/`](./adr/)
- 3 篇 Runbook → [`runbooks/`](./runbooks/)

---

## 附录 A：M1 完整拆解（4 人并行 5 天）

> ⚠️ 本附录是 M1 的**完整 sprint planning**：含 Owner 分配、工时、依赖、集成顺序。其它 milestone（M2-M4）的 sprint planning 在其启动前 kickoff 时填入对应章节。

### A.1 Owner × Branch × 任务 × 工时 × 依赖

| Owner          | Branch             | 任务                                                                                                                                              | 工时 | 依赖             |
| -------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---- | ---------------- |
| A - Backend Infra | `feat/m1-infra`    | FastAPI 骨架 + pydantic-settings + Postgres/Redis 连接 + alembic + Langfuse SDK + Dockerfile + `/health` `/threads` 假接口                       | 3d   | —                |
| B - Graph Base | `feat/m1-graph`    | LangGraph AgentState schema + BaseAgent + Planner（mock LLM）+ RedisCheckpointSaver + 一个端到端假 trace                                          | 4d   | A 的 config      |
| C - Frontend   | `feat/m1-frontend` | Next.js + Tailwind + shadcn + 对话流 + EventSource + Markdown 渲染 + 假数据流测试                                                                  | 3d   | A 的 OpenAPI schema（mock 也行） |
| D - Deploy + CI | `feat/m1-deploy`   | docker-compose v1 + GitHub Actions PR pipeline + Taskfile + pre-commit（commitlint + ruff + eslint）                                                | 2d   | A 的 Dockerfile  |
| 集成日         | —                  | merge 全部 → main → 跑一次端到端（query → SSE → draft）                                                                                            | 1d   | 上面全部         |

### A.2 集成顺序（避免冲突）

1. **Day 1**：A 先 merge 骨架到 main（其他人 rebase）
2. **Day 2-3**：B / C / D 并行在各自分支
3. **Day 4**：依序 merge
   - 先 merge D（CI 跑通）
   - 再 merge A 增量（真实 Postgres/Redis）
   - 再 merge B（Planner 接真 LLM）
   - 最后 merge C（前端接真接口）
4. **Day 5**：跑 demo + 修集成 bug

### A.3 冲突预防规则

- `research_backend/app/api/schemas.py` 由 A 锁定初版，B/C 只能加不能改
- `research_backend/app/config.py` 由 A 锁定
- **接口契约提前一天在 main 上 freeze**：A Day 1 末必须把 `/threads` `/research/stream` 的 request/response schema 定稿
- **C 用 OpenAPI mock**（`msw` / `prism`）独立跑，不依赖 B 真接口

### A.4 spec-kit 翻译指南

M1 sprint planning 应该翻译为 spec-kit 格式，不要直接当 tasks.md：

| spec-kit 文件 | 来源 | 内容 |
| --- | --- | --- |
| `spec.md` | M1 §端到端 demo + 验收标准 | "输入 query → 后端 mock 流式响应 → 前端渲染 → Langfuse trace 可见" |
| `plan.md` | M1 §集成顺序 + A.3 冲突预防 | "接口契约先行 → 4 人并行 → Day 1 A 先 merge → Day 4 依序 merge D → A 增量 → B → C" |
| `tasks.md` | M1 §A.1 owner × branch × 任务 | 按 user story 重组（不是 owner × day）：user story 1 = "FastAPI 骨架可启动"（来自 A Day 1-2 + D Day 1-2）；user story 2 = "LangGraph 可跑 trace"（来自 B Day 1-3）... |

**典型 spec-kit 调用序列**：
```
/speckit.specify    # 基于 milestones.md §M1 + architecture.md → spec.md
/speckit.plan       # 基于 spec.md + ADR → plan.md
/speckit.tasks      # 基于 plan.md → tasks.md（按 user story）
/speckit.implement  # 按 tasks.md 实施
```

详见 [`docs/spec-kit-mapping.md`](./spec-kit-mapping.md)（如尚未创建则下次迭代补充）。
