# 贡献指南 (Contributing Guide)

> 欢迎参与 deep-research！本文说明如何提 PR、命名规范、review 流程与本地开发约束。

---

## 1. 分支策略（Trunk-Based + 短分支）

`main` 是唯一长期分支，**随时可发布**。所有工作在短生命周期 feature 分支上：

| 前缀 | 用途 | 生命周期 |
|------|------|---------|
| `feat/` | 新功能 | ≤ 3 天 |
| `fix/` | Bug 修复 | ≤ 1 天 |
| `chore/` | 依赖升级、文档、refactor | ≤ 3 天 |
| `exp/` | 实验性（PoC、A/B），不强制合并 main | 不限 |

超过 3 天未合入的 `feat/` 必须 rebase `main`，否则 review 拒绝。

---

## 2. 提交规范（Conventional Commits）

格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

常用 type：`feat` / `fix` / `docs` / `style` / `refactor` / `perf` / `test` / `build` / `ci` / `chore` / `revert`。

scope 示例：`backend` / `frontend` / `graph` / `agent` / `infra` / `docs`。

**强制规则：**

- subject 中文不超过 30 字，英文不超过 72 字符
- body 解释 *为什么*，不解释 *做了什么*（diff 已经说明做了什么）
- 破坏性变更在 footer 写 `BREAKING CHANGE: <说明>`
- 关闭 issue 用 `Closes #123`、`Refs #456`

启用 `commitlint` + husky，PR 触发的 `commitlint --edit` 失败则禁止合并。

---

## 3. PR 模板

`.github/pull_request_template.md`：

```markdown
## 背景
<!-- 为什么需要这个改动？关联 issue / ADR -->

## 主要改动
<!-- bullet 列出关键变更 -->

## 测试
- [ ] 单元测试已补 / 已更新
- [ ] 覆盖率 ≥ 80%（核心模块 ≥ 90%）
- [ ] `task test:integration` 通过
- [ ] e2e 影响评估：预算 $X / 用例 N

## 影响面
<!-- 列出可能受影响的模块、配置、文档 -->

## 截图 / 录屏（前端）
<!-- UI 变更必填 -->

## Checklist
- [ ] commit 信息符合 Conventional Commits
- [ ] 文档已更新（如有行为变更）
- [ ] CHANGELOG 已添加条目
- [ ] secret 未入仓（git-secrets 通过）
- [ ] 大文件未入仓（> 1 MB）
```

---

## 4. CODEOWNERS（按目录）

`/.github/CODEOWNERS`：

```
/research_backend/agents/    @cai.he @alice
/research_backend/graph/     @cai.he @bob
/research_backend/api/       @cai.he @alice
/research_backend/auth/      @cai.he @security-team
/research_frontend/          @cai.he @frontend-leads
/infra/                      @cai.he @sre-team
/docs/adr/                   @cai.he @architects
/.github/workflows/          @cai.he @sre-team
```

CODEOWNER 自动成为 reviewer，但**不豁免**下文的 review 人数规则。

---

## 5. PR Review 规则

| 触碰路径 | 最小 reviewer 数 |
|---------|----------------|
| 默认（文档、UI、refactor） | ≥ 1 |
| `research_backend/graph/` | ≥ 2 |
| `research_backend/agents/` | ≥ 2 |
| `research_backend/auth/` | ≥ 2（其中 1 人须为 @security-team） |
| `research_backend/api/` 公共契约 | ≥ 2 |
| `infra/` / `.github/workflows/` | ≥ 2 |
| 文档 / 注释 / typo | ≥ 1 |

reviewer 24 小时内无响应自动重派；超时 ≥ 48h 由作者在 PR 评论里 `@team-lead` 升级。

**reviewer 检查项：**

1. 设计是否对齐相关 ADR
2. 是否引入新的外部依赖 / 许可证冲突
3. 测试覆盖是否达标（单测 ≥ 80%、核心 graph ≥ 90%）
4. 是否影响 Langfuse trace 结构（破坏将影响 nightly e2e 评分）
5. 是否含 PII / secret（git-secrets 自动挡，但需人眼复核 .env.example）

---

## 6. Pre-commit Hooks

启用 `pre-commit`（`.pre-commit-config.yaml`）：

| 钩子 | 范围 | 说明 |
|------|------|------|
| `git-secrets` | 全仓 | 扫描 AWS / GH / 通用 token |
| `ruff check --fix` | `research_backend/**/*.py` | Lint + autofix |
| `ruff format` | 同上 | 格式化 |
| `eslint --fix` | `research_frontend/**/*.{ts,tsx}` | Lint |
| `prettier --write` | 同上 | 格式化 |
| `commitlint` | commit msg | 拦截不符合 Conventional 的提交 |

安装：`task setup-hooks`。

---

## 7. 本地开发流程

```bash
# 克隆
git clone https://github.com/hochoy/deep-research.git
cd deep-research

# 一键起依赖（Postgres / Redis / Langfuse / Milvus / MinIO）
task deps up wait-healthy

# Backend（终端 A）
cd research_backend
uv sync
uv run alembic upgrade head
uv run uvicorn research_backend.app:app --reload

# Frontend（终端 B）
cd research_frontend
pnpm install
pnpm dev

# 跑测试
task test                 # 单测
task test:integration     # 集成测试
task test:e2e:smoke       # e2e 冒烟（预算 $1）
task test:e2e:nightly     # e2e 全量（仅 CI 定时跑，预算 $5）
```

---

## 8. 测试要求

- **覆盖率门槛**：单测 ≥ 80%，核心模块（`graph/`、`agents/`）≥ 90%
- **新增功能必须带测试**，禁止 `pragma: no cover`（仅限 type stub 与不可达分支）
- **LangGraph 节点**改动后必须重跑 `tests/graph/` 下的 state machine 用例
- **e2e nightly** 预算 $5 / 跑，超预算 CI 自动 fail 并发报警到 `#deep-research-ci`
- **flaky test** 标记 `@pytest.mark.flaky`，连续 3 个 nightly 失败须在 1 周内修复或删除

---

## 9. License

本仓库使用 **Apache License 2.0**。提交代码即表示同意以 Apache 2.0 贡献；引入第三方依赖时确认其许可证与 Apache 2.0 兼容（禁用 AGPL / 商业版权源码）。

详细贡献者协议参见 `LICENSE` 与 `CONTRIBUTOR_AGREEMENT.md`。
