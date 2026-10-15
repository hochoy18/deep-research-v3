# 架构设计（Architecture）

> 本文档是 `hochoy-deep-research` 的整体架构说明。聚焦于"组件是什么、组件间如何协作、数据怎么流动"。具体到 LangGraph 节点定义、Agent prompt、Postgres schema 见对应专题文档。

---

## 1. 设计目标

| 目标 | 度量 |
|---|---|
| **可恢复**：用户中断 / 网络抖动 / 服务重启后能恢复研究 | LangGraph checkpoint + Redis |
| **可观测**：每个 Agent 的输入/输出/耗时/token 都能回溯 | Langfuse trace |
| **可评估**：每次跑都能拿到 LLM-as-judge 的事实性 / 引用 / 覆盖度分数 | Langfuse Datasets + scorers |
| **HITL 友好**：在用户最需要决策的环节（开题、topic 列表、draft 审阅）介入，不打断流程 | LangGraph `interrupt()` + inline chat UI |
| **多供应商容灾**：单一 LLM 失败不影响整体 | 按任务类型路由 + 自动降级 |
| **多 Agent 协作**：规划 / 检索 / 写作 / 核查四阶段清晰解耦 | BaseAgent 模板方法 + LangGraph StateGraph |

## 2. 组件全景

```
                          ┌─────────────────────────────────────────────────────┐
                          │                   Frontend (Next.js 16)              │
                          │  ChatThread | PlanPanel | SourcesPanel | ExportBtn    │
                          └────────────────────┬──────────────────────────────────┘
                                               │  HTTP POST /api/research/stream
                                               │  ←  SSE: event: node_start | tool_call
                                               │        message | state_update | interrupt
                                               │        done | error
                          ┌────────────────────┴──────────────────────────────────┐
                          │                  Backend (FastAPI 0.143)              │
                          │                                                     │
                          │   ┌────────────────────────────────────────────┐       │
                          │   │    LangGraph StateGraph (compile)          │       │
                          │   │    [RedisCheckpointSaver attached]         │       │
                          │   │                                              │      │
                          │   │   clarify_with_user ★interrupt              │      │
                          │   │            ↓                                │      │
                          │   │   write_research_brief                      │      │
                          │   │            ↓                                │      │
                          │   │   Planner ─→ Researcher ─→ Writer ─→ Critic │      │
                          │   │            ↑___________________│            │      │
                          │   └────────────┬──────────────────┬─────────────┘      │
                          │                │                  │                    │
                          │        ┌───────┴───────┐  ┌───────┴──────────┐          │
                          │        │  Tool Layer   │  │  Observability   │          │
                          │        │              │  │                  │          │
                          │        │ web_search   │  │ Langfuse OTel    │          │
                          │        │ fetch_page   │  │ get_client() +   │          │
                          │        │ cite         │  │ start_as_current │          │
                          │        │ (v2: search_ │  │ _observation     │          │
                          │        │  local_kb)   │  │                  │          │
                          │        └──┬────────┬──┘  └──────┬───────────┘          │
                          └───────────┼────────┼────────────┼──────────────────────┘
                                     │        │            │
                  ┌──────────────────┘        │            │
                  ▼                           ▼            ▼
        ┌──────────────────┐        ┌──────────────────┐  ┌──────────────────┐
        │  Bailian / 阿里云 │        │   目标网页（公网） │  │   Langfuse        │
        │  DashScope 1.27  │        │   （HTTP GET）    │  │   self-hosted     │
        │  web_search      │        │   trafilatura    │  │   v4.59.0         │
        │  standard        │        │   提取正文         │  │                   │
        └──────────────────┘        └──────────────────┘  └──────────────────┘

        ┌──────────────────────────────────────────────────────────────────────┐
        │                       Persistent Layer                                │
        │                                                                       │
        │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
        │   │ Postgres 16 │  │  Redis 8    │  │ Milvus 3    │  │ MinIO      │  │
        │   │ threads     │  │ LangGraph   │  │ vector      │  │ PDF /      │  │
        │   │ reports     │  │ checkpoint  │  │ cache       │  │ cached     │  │
        │   │ eval_runs   │  │ TTL 7d      │  │ bge + OpenAI│  │ HTML       │  │
        │   └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │
        └──────────────────────────────────────────────────────────────────────┘
```

## 3. 组件职责

### 3.1 Frontend（Next.js 16）

| 模块 | 职责 |
|---|---|
| **ChatThread** | 流式显示 Agent 输出；接收 SSE event；展示消息历史 |
| **ResearchBriefCanvas**（右侧） | 显示结构化的 Plan / 时间范围 / 受众 / 深度；用户可点击 [编辑] 微调 |
| **PlanPanel** | 显示 Planner 拆解的子任务（`status: pending / running / done / failed`）|
| **SourcesPanel** | 显示 Researcher 检索到的所有来源（url / title / score / excerpt），可点击跳转 |
| **ExportBtn** | 下载当前 thread 的 Markdown / PDF |
| **SettingsDrawer** | 模型路由策略、安全设置（v2）|

技术：Tailwind v4 CSS-first + shadcn + Zustand（前端状态）+ TanStack Query（SSE 缓存）。

### 3.2 Backend（FastAPI 0.143）

| 模块 | 职责 |
|---|---|
| **`app/main.py`** | FastAPI app + 路由注册 + 启动 lifespan |
| **`app/api/routes.py`** | `/research/stream`（SSE 入口）、`/threads`（CRUD）、`/export/{thread_id}`（下载） |
| **`app/api/schemas.py`** | Pydantic 请求/响应模型；SSE event schema |
| **`app/api/deps.py`** | 依赖注入（LangGraph compiled graph、DB session、Redis client） |
| **`app/graph/`** | LangGraph StateGraph 的 compile、State schema、节点、边 |
| **`app/agents/`** | 4 个 Agent + `BaseAgent` 抽象类 |
| **`app/tools/`** | web_search / fetch_page / cite |
| **`app/observability/`** | Langfuse OTel 集成 + trace 上下文管理 |
| **`app/persistence/`** | Postgres session、Redis checkpoint 配置 |
| **`app/eval/`** | HotpotQA 评估 runner、LLM-as-judge scorers |

### 3.3 Agent 层（4 个）

详见 [`docs/agent-design.md`](./agent-design.md)。

| Agent | 职责 | 主要工具 | 默认 LLM |
|---|---|---|---|
| **Planner** | 把 query 拆成子任务列表（带依赖关系） | 无 | GPT-4o |
| **Researcher** | 对每个子任务：搜索 → 抓取 → 摘要 | `web_search`, `fetch_page`, `cite` | GPT-4o |
| **Writer** | 基于 plan + sources 写 Markdown draft | `cite` | GPT-4o |
| **Critic** | 检查 draft 给出 critique；决定回到 Researcher / Writer 还是结束 | 无 | o3-mini |

### 3.4 工具层（Tools）

详见 [`docs/graph-design.md` §4](./graph-design.md)。

| Tool | 输入 | 输出 | 来源 |
|---|---|---|---|
| `web_search` | `query: str`, `max_results: int = 5` | `List[SearchResult]` | Bailian DashScope `web_search` 标准版 |
| `fetch_page` | `url: str` | `PageContent`（HTML→Markdown，去广告/导航）| 自研（trafilatura 抽取 + 自定义清洗） |
| `cite` | `claim: str`, `source_id: str` | `Citation`（绑定引用编号） | 自研 |
| `search_local_kb` | `query: str` | `List[Doc]`（v2 接 Milvus 跨研究复用） | 自研 |

错误处理：单次失败重试 2 次（指数退避）；单源失败不阻塞整体。

### 3.5 可观测性（Langfuse）

详见 [`docs/observability.md`](./observability.md)。

- **Trace**：每个 thread 一条 trace；每条 trace 包含若干 span（每个 Agent 节点、每个 tool call）
- **Score**：trace 完成后用 LLM-as-judge 打分（事实性 / 引用密度 / 覆盖度 / 延迟 / token 成本 / 工具失败率）
- **Datasets**：HotpotQA 子集 + 自造测试集，跑批量 eval

### 3.6 持久化

| 存储 | 数据 | 选型理由（详见 ADR-0003） |
|---|---|---|
| **Postgres 16** | `threads`（会话元数据）/ `reports`（研究产物）/ `eval_runs`（评估结果）| 关系数据 + 事务 + 生态成熟 |
| **Redis 8** | LangGraph checkpoint（`checkpoint:{thread_id}`），TTL 7 天 | 内存 KV，append-only 写入，TTL 原生支持 |
| **Milvus 3** | 历史 source/draft 的向量（chunk 500 tokens）| 生产级向量库；自带 MinIO 减少组件 |
| **MinIO** | PDF / 缓存的 HTML / 用户上传文件（v2）| S3 兼容；复用 Milvus 自带实例，新 bucket 隔离 |

## 4. 核心数据流（一次完整研究）

```
┌────┐
│User│
└─┬──┘
  │ POST /api/research/stream
  │ body: { thread_id?, query, config? }
  ▼
┌──────────────────────────────────────────────────────────────────┐
│ FastAPI: routes.research_stream                                    │
│   1. 创建或恢复 thread (Postgres threads 表)                       │
│   2. 打开 Langfuse trace (OTel current_observation)               │
│   3. compiled_graph.stream(input, thread_id, config)              │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│ LangGraph StateGraph                                              │
│                                                                      │
│   node: clarify_with_user                                          │
│     → interrupt() ──── SSE: event: interrupt ───→ 等待用户           │
│     ← POST /api/research/{thread_id}/resume ───→ Command(resume=) │
│                                                                      │
│   node: write_research_brief                                       │
│     → LLM (GPT-4o, ClarifyWithUser schema)                         │
│     → SSE: event: state_update (plan)                              │
│                                                                      │
│   node: Planner                                                     │
│     → LLM (GPT-4o, structured output: List[SubTask])               │
│     → SSE: event: state_update (plan)                              │
│                                                                      │
│   node: Researcher (循环直到 plan 全部 done)                         │
│     → tool_call: web_search → SSE: event: tool_call                │
│     → tool_call: fetch_page  → SSE: event: tool_call               │
│     → SSE: event: state_update (sources)                           │
│                                                                      │
│   node: Writer                                                     │
│     → LLM (GPT-4o, draft output)                                   │
│     → SSE: event: message (流式 token)                              │
│     → SSE: event: state_update (draft)                             │
│                                                                      │
│   node: Critic                                                      │
│     → LLM (o3-mini, critique + decision)                           │
│     → 路由: approve → END | revise_plan → Planner                  │
│             revise_research → Researcher | revise_draft → Writer  │
│                                                                      │
│   END                                                               │
│     → 生成 Markdown report 存 Postgres + MinIO                      │
│     → LLM-as-judge 打分 存 Langfuse                                 │
│     → SSE: event: done                                             │
└──────────────────────────────────────────────────────────────────┘
                            │
                            ▼ SSE 流到浏览器
                  ┌────────────────────────┐
                  │  EventSource API        │
                  │  → 渲染 chat / plan /  │
                  │    sources / draft     │
                  │  → 触发 toast / 完成   │
                  └────────────────────────┘
```

## 5. 关键技术决策（指向 ADR）

| 决策 | 理由 | ADR |
|---|---|---|
| LangGraph over CrewAI / AutoGen | Redis checkpoint + `interrupt()` + OTel 集成 | [ADR-0001](./adr/0001-langgraph-over-crewai.md) |
| Bailian web_search over Tavily | 中文友好 + 国内合规 + 阿里栈对齐 | [ADR-0002](./adr/0002-bailian-web-search-over-tavily.md) |
| Postgres + Milvus + MinIO | 生产级 + 阿里栈 + Milvus 自带 MinIO | [ADR-0003](./adr/0003-postgres-milvus-minio.md) |
| 单 repo 平级目录 | 简单、跨端改动原子化、3-5 人友好 | [ADR-0004](./adr/0004-single-repo-over-monorepo.md) |
| `langchain-classic` over `langchain-community` | 后者已被官方 sunset | [ADR-0005](./adr/0005-langchain-classic-over-langchain-community.md) |
| Langfuse v5 OTel API | legacy v2 API 已 deprecated | [ADR-0006](./adr/0006-langfuse-v5-otel-api.md) |
| Tailwind v4 CSS-first | 最新稳定 + 配置简化 | [ADR-0007](./adr/0007-tailwind-v4-css-first.md) |
| Trunk-based over Git Flow | 小团队友好 + CI 友好 | [ADR-0008](./adr/0008-trunk-based-over-git-flow.md) |
| v1 不做鉴权 | 内部工具，v2 再加 | [ADR-0009](./adr/0009-v1-no-auth.md) |
| HITL clarification 用 `interrupt()` | production-grade + 可恢复 | [ADR-0010](./adr/0010-hitl-clarify-with-interrupt.md) |
| 按任务类型路由多模型 | 成本最优 + 性能最优 | [ADR-0011](./adr/0011-multi-model-task-routing.md) |
| Python 3.12 锁定 | 当前最稳的 LTS 类版本，生态支持最佳 | [ADR-0012](./adr/0012-python-3-12.md) |

## 6. 关键非功能性需求

| 维度 | 指标 |
|---|---|
| **延迟** | 单次研究流 p95 < 5 分钟（含 HITL 等待时间） |
| **可用性** | 关键依赖（Postgres / Redis / Langfuse）故障降级；LLM 失败自动切备选模型 |
| **安全** | Prompt 注入防护（搜索结果 sandbox） + SSRF 白名单 + 密钥分离 |
| **可观测性** | 100% Agent 节点 + tool call 上报 Langfuse；score 全维度采集 |
| **可恢复** | Redis checkpoint 7 天内任意时刻恢复；session 中断保留 |
| **成本** | 单次研究流 LLM token ≤ $0.5（GPT-4o 主 + 国产降级） |

## 7. v2 演进路线

不在 v1 scope、明确推到 v2 的：

- **多用户 + 鉴权**：JWT + 邮箱密码 + OAuth + SSO
- **HITL 完善**：Sources 审阅、Critic 循环中止、全 HITL 完整版
- **自定义业务 score**：改稿次数、是否触发 Critic 改稿等
- **报告协同编辑**：Notion / Lark Doc
- **监控告警**：Prometheus + Grafana + Alertmanager（v1 只用 Langfuse trace）
- **跨研究复用**：`search_local_kb` 工具化（接 Milvus）
- **自动降级 + token 预算控制**

## 8. 相关文档

- 4 个 Agent 的 prompt / 工具集 → [`agent-design.md`](./agent-design.md)
- LangGraph State / 节点 / 边 / HITL interrupt → [`graph-design.md`](./graph-design.md)
- Langfuse trace / score / 告警 → [`observability.md`](./observability.md)
- 评估数据集 / LLM-as-judge → [`eval.md`](./eval.md)
- 部署 / CI / K8s → [`deployment.md`](./deployment.md)
- 贡献流程 / commit 规范 / CODEOWNERS → [`contributing.md`](./contributing.md)
- 12 篇 ADR → [`adr/`](./adr/)
- 运维应急手册 → [`runbooks/`](./runbooks/)
