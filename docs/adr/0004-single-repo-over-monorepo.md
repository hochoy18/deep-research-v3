# ADR 0004：单仓库平级目录而非 monorepo

- **Status**：Accepted（2026-07-15）
- **Date**：2026-07-15
- **Deciders**：架构组 @cai.he、@bob、@alice

---

## Context

deep-research 仓库需要同时托管：

- 后端 Python 服务（`research_backend/`，FastAPI + LangGraph）
- 前端 Next.js 应用（`research_frontend/`，React 19）
- 共享的 prompt 模板、protobuf schema（计划）
- 基础设施脚本（`infra/`，docker-compose、helm chart）
- 文档与 ADR（`docs/`）

团队规模：3-5 人全职 + 兼职贡献者；v1 单机部署；预计 1 年内不超 10 人。

候选方案：

1. **单仓库 + 平级目录**（一个 Git 仓库，前后端各占一个根目录）
2. **单仓库 + Turborepo / Nx**（一个 Git 仓库，前端/后端/shared 各一个 workspace）
3. **双仓库**（`deep-research-backend` + `deep-research-frontend`）

---

## Decision

采用**单仓库 + 平级目录**：

```
deep-research/
├── research_backend/    # Python + uv
├── research_frontend/   # Next.js + pnpm
├── infra/               # docker-compose / helm
├── docs/                # ADR + runbooks + SDD
└── Taskfile.yml
```

不引入 Turborepo / Nx，不引入 pnpm workspace。

---

## Consequences

**正面：**

- 单仓单 issue / 单 PR 即可端到端改完前后端，PR review 一目了然
- CI 简单：一条 workflow 同时 lint / test 前后端，缓存策略直白
- 依赖解耦由各自 `pyproject.toml` 与 `package.json` 承担，无 workspace 拓扑复杂度
- 文档 / ADR / infra 与代码同仓，永远不会"找不到最新设计"
- 容器化天然契合：`docker-compose.yml` 在根目录即可拉起全部服务

**负面：**

- 共享代码（prompt 模板、类型 schema）目前复制粘贴；待量上来再抽 `packages/shared/`
- CI 全量跑时间会增长；用 path filter（`paths:` trigger）缓解
- 前端与后端无法独立发版；v1 不需要，v2 引入 image tag 解耦即可

---

## Alternatives

### A. 单仓库 + Turborepo

- 优点：天然 `packages/shared/`，task graph 加速 CI
- 缺点：uv 与 pnpm workspace 语义不同（uv 1.5+ 才有 `workspace` member 支持），跨语言构建图 Turborepo 不擅长；当前 5 人团队属过度工程
- 否决原因：Turborepo 主要解决 JS / TS 多包场景，对 Python+JS 混合栈收益边际、成本确定

### B. 双仓库

- 优点：前后端彻底解耦，可独立版本
- 缺点：跨仓 PR（API 契约变更）需要双 PR 同步合入，原子性差；新人 onboarding 要克隆两次；CI 配置双份；LICENSE 与 ADR 难以保持单一来源
- 否决原因：v1 单用户产品，跨仓协作摩擦 > 解耦收益

---

## Notes

- 当 `packages/shared` 出现 ≥ 3 个真实使用方、且需要独立版本时再评估 Turborepo（见 ADR 0004-revisit 触发条件）
- 命名锁定：`research_backend/` 与 `research_frontend/` 不改为 `apps/` 或 `services/`，避免无意义重构
