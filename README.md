# Hochoy Deep Research

> 一个生产级的 Deep Research Agent：多 Agent 协作 + 联网搜索 + 事实核查 + HITL 澄清，最终产出 Markdown / PDF 报告。

## ✨ 核心特性

- 🧠 **多 Agent 编排**：Planner → Researcher → Writer → Critic，基于 LangGraph 1.2
- 🔍 **联网检索**：集成 Bailian（阿里云百炼）`web_search`，自动抓取 + 清洗网页正文
- 🪞 **HITL 澄清**：开题前自动追问用户方向（scope / 时间范围 / 受众 / 深度），用 LangGraph `interrupt()` 实现可暂停-可恢复
- 📊 **可观测性**：Langfuse 自托管，完整 trace + LLM-as-judge eval
- 💾 **Checkpoint & 恢复**：LangGraph state 持久化到 Redis，session 中断后可恢复
- 📦 **报告导出**：Markdown + PDF（`md-to-pdf` puppeteer 方案）
- 🛡️ **安全**：Prompt 注入防护 + SSRF 白名单 + 密钥不入 git

## 🏗️ 架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    Next.js 16 Frontend                       │
│  Chat Thread  |  Plan Panel  |  Sources Panel  |  Export     │
└────────────────────────────┬────────────────────────────────┘
                             │  SSE (FastAPI StreamingResponse)
┌────────────────────────────┴────────────────────────────────┐
│                    FastAPI Backend                           │
│                                                              │
│  ┌──────────────────────────────────────────────────┐        │
│  │         LangGraph StateGraph (4 Nodes)            │        │
│  │  START → [clarify_with_user *interrupt*]         │        │
│  │        → write_research_brief                    │        │
│  │        → Planner → Researcher → Writer → Critic  │        │
│  └──────────────────────────────────────────────────┘        │
│                                                              │
│  Tools: web_search | fetch_page | cite | search_local_kb    │
└──────────┬───────────────────────────────────┬───────────────┘
           │                                   │
           ▼                                   ▼
   ┌──────────────┐                   ┌─────────────────┐
   │ Postgres 16  │                   │   Langfuse      │
   │ (threads,    │                   │   self-hosted   │
   │  reports,    │                   │   (trace+score) │
   │  eval_runs)  │                   └─────────────────┘
   └──────────────┘
   ┌──────────────┐    ┌─────────────────┐   ┌────────────┐
   │   Redis 8    │    │   Milvus 3      │   │  MinIO     │
   │ (checkpoint) │    │ (vector cache)  │   │ (objects)  │
   └──────────────┘    └─────────────────┘   └────────────┘
```

完整架构图与设计决策见 [`docs/architecture.md`](./docs/architecture.md)。

## 📚 文档导航

| 文档 | 说明 |
|---|---|
| [`docs/architecture.md`](./docs/architecture.md) | 整体架构图、组件说明、数据流 |
| [`docs/agent-design.md`](./docs/agent-design.md) | 4 个 Agent 的 prompt / 工具集 / 输出契约 |
| [`docs/graph-design.md`](./docs/graph-design.md) | LangGraph State schema、节点、边、HITL interrupt 设计 |
| [`docs/milestones.md`](./docs/milestones.md) | M1–M4 总目标、端到端 demo、依赖、风险（sprint planning 待启动前 kickoff 填） |
| [`docs/spec-kit-mapping.md`](./docs/spec-kit-mapping.md) | Spec-Kit SDD 流程如何消费 `docs/` 的指南（spec.md / plan.md / tasks.md 翻译） |
| [`docs/observability.md`](./docs/observability.md) | Langfuse trace 字段、score 维度、告警阈值 |
| [`docs/eval.md`](./docs/eval.md) | HotpotQA 子集、LLM-as-judge、eval pipeline |
| [`docs/deployment.md`](./docs/deployment.md) | docker-compose 启动、CI/CD、预发、K8s 路线图 |
| [`docs/contributing.md`](./docs/contributing.md) | 分支规范、commit 规范、PR 流程、CODEOWNERS |
| [`docs/adr/`](./docs/adr/) | 12 篇架构决策记录（ADR） |
| [`docs/runbooks/`](./docs/runbooks/) | 运维应急手册 |

## 🚀 快速启动

> 前置条件：Docker 24+、Docker Compose v2、Node.js 20+、Python 3.12、uv 0.13+、pnpm 12+。

```bash
# 1. 克隆
git clone <repo-url> hochoy-deep-research
cd hochoy-deep-research

# 2. 复制环境变量模板
cp research_backend/.env.example research_backend/.env
cp research_frontend/.env.example research_frontend/.env
# 编辑 .env 填入 API keys（OpenAI / DashScope / Langfuse）

# 3. 一键起所有依赖 + 应用
task dev:up

# 4. 看日志
task dev:logs

# 5. 打开浏览器
open http://localhost:3000        # 前端
open http://localhost:8000/docs   # 后端 OpenAPI
open http://localhost:3001        # Langfuse UI（self-hosted）
```

更多启动细节见 [`docs/deployment.md`](./docs/deployment.md)。

## 🛠️ 开发命令（Taskfile）

```bash
task dev:up           # 起所有 docker-compose 服务
task dev:down         # 关掉
task dev:logs         # tail 所有日志
task backend:install  # uv sync
task backend:test     # pytest
task backend:lint     # ruff check .
task frontend:install # pnpm install
task frontend:dev     # pnpm dev（独立跑前端）
task e2e:hotpotqa     # 跑 HotpotQA 评估
task preview:deploy   # 起 CI 预发 stack
```

## 🧪 M1 里程碑（4 人 5 天）✅ v1.0.0-M1（2026-10-16）

| Day | Owner A - Infra | Owner B - Graph | Owner C - Frontend | Owner D - Deploy/CI |
|---|---|---|---|---|
| **Day 1** | FastAPI 骨架 + config + Postgres/Redis + Langfuse SDK | `AgentState` + `BaseAgent` 骨架 | Next.js + Tailwind v4 + shadcn + 对话流 | docker-compose + GitHub Actions + Taskfile + pre-commit |
| **Day 2-3** | Alembic + `/health` + `/threads` 假接口 | Planner + RedisCheckpointSaver + 第一条 e2e trace | Markdown 渲染 + OpenAPI mock | CI 跑通 + preview stack |
| **Day 4** | freeze API schema | Researcher + web_search + fetch_page（mock） | 接 SSE 真后端 | ADR 模板 |
| **Day 5** | merge → main | merge → main | merge → main | 集成 demo + 修 bug |

集成顺序：A 先 merge → D（CI 跑通）→ A 增量 → B → C → demo。

**M1 状态：✅ 已完成**（2026-10-16 / 4 人 4 天并行 + 1 天集成日 / [v1.0.0-M1 tag](CHANGELOG.md) / `git checkout v1.0.0-M1` 拉取）

- 交付物：FastAPI + Next.js 16 骨架 + docker-compose 5 服务 + LangGraph echo mock + 前端对话流 + Taskfile 一键起服务 + pre-commit hook 链 + ci.yml 8-job PR gate
- 详见 [CHANGELOG.md](./CHANGELOG.md) 的 [v1.0.0-M1] 段
- 下一步：M2 检索（Planner + Researcher + web_search + fetch_page + Plan/Sources 面板）

## 📦 技术栈

- **Backend**: Python 3.12 + FastAPI 0.143 + LangGraph 1.2 + langchain-classic
- **Frontend**: Next.js 16 + React 19 + Tailwind v4（CSS-first）+ shadcn
- **Storage**: Postgres 16 + Milvus 3 + MinIO + Redis 8
- **Observability**: Langfuse self-hosted（v4.59.0）+ Python SDK 5.0.1（OTel API）
- **Web Search**: Bailian DashScope 1.27.7 + `web_search` 标准版
- **LLM**: OpenAI（GPT-4o / o3-mini）+ Bailian Qwen3-Max / DeepSeek-V3 / GLM-4.6（按任务类型路由）
- **License**: Apache 2.0

完整版本锁定见 [`docs/deployment.md`](./docs/deployment.md)。

## 🗺️ 路线图

| 版本 | 范围 |
|---|---|
| **v1**（当前） | 单用户、4 Agent、HITL 澄清、Markdown + PDF 导出、HotpotQA 评估 |
| **v2** | 多用户 + 鉴权、自定义业务 score、报告协同编辑（Notion / Lark Doc）、Prometheus + Grafana 监控告警、Milvus `search_local_kb` 工具化 |

## 🤝 贡献

阅读 [`docs/contributing.md`](./docs/contributing.md) 了解分支规范、commit 规范、PR 流程、CODEOWNERS。

---

**License**: Apache 2.0
