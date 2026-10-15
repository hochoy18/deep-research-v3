# ADR 0008: 采用 Trunk-based Development 而非 Git Flow

- Status: Accepted
- Date: 2026-10-15
- Deciders: @cai.he, @hochoy

## Context

deep-research v3 团队规模 3-5 人（含 1 名 AI 协作 owner），发布节奏为每周 1-2 个
迭代。我们需要选择一套 Git 分支工作流，在以下三个目标之间取得平衡：

1. 主分支随时处于可发布状态（CI 必需）；
2. 多人并行开发不互相阻塞；
3. 不引入超过团队规模的协作负担。

当前候选三种主流工作流：

### 方案 B1: Git Flow

`main` + `develop` 双长寿命分支 + `feature/*` / `release/*` / `hotfix/*` 短分支，
需要 `develop` 合并回 `main` 时打 tag。Vincent Driessen 2010 年提出，适合有专职
release manager 的大型团队。

### 方案 B2: GitHub Flow

`main` 永远可部署；任何新功能从 `main` 开短寿命分支（`feature/xxx`），PR review
通过后 squash merge 回 `main`，部署通过 CI/CD 自动触发。Scott Chacon 2011 年提出。

### 方案 B3: Trunk-based Development

所有人在 `main`（即 trunk）上直接提交或开极短寿命分支（< 1 天），依赖 feature flag
管理未完成功能，强调高频率集成。Paul Hammant / Jez Humble 等在
《Accelerate》《Continuous Delivery》中背书。

## Decision

**采用 Trunk-based Development（方案 B3），允许以下分支模式：**

- `main`：唯一长寿命分支，受分支保护，必须通过 CI + 1 reviewer 才能 merge；
- `feat/<ticket-id>-<short-desc>`：单个 PR 级别的短分支，生命周期 < 48 小时，
  完成后 squash merge 并删除；
- `exp/<owner-initials>/<topic>`：仅 owner 使用的探索性分支（AI 协作实验），
  不强制 squash merge；
- 不使用 `release/*`、`hotfix/*` 长寿命分支；hotfix 直接走 PR + CI；
- 不使用 git tag 标记版本，版本号由 `package.json` + CI 自动生成并 push。

主分支保护规则：`main` 必须满足：

- 至少 1 个 reviewer approval；
- 全部 CI job（lint / typecheck / unit / e2e）通过；
- 无 force push；
- commit message 遵循 Conventional Commits。

## Consequences

正面：

- 合并冲突频率显著降低：分支寿命 < 48h，rebase 成本接近零；
- CI 反馈循环短：每次 push 触发完整测试，10 分钟内拿到结果；
- 与 GitHub Actions 的 `pull_request` 触发器天然匹配，无需额外 orchestration；
- 团队 onboarding 成本低：新成员只需要理解 `main` + 短分支两个概念。

负面 / 约束：

- 必须配套完整的 CI 套件才能让 `main` 保持可发布状态，CI 维护成本较高；
- Feature flag 缺失时无法在 `main` 上做"完成 70% 的功能"，目前通过
  `/_experimental/*` 路由前缀临时隔离，可持续到 v1 完结；
- 紧急修复与功能提交在同一分支竞争 reviewer 注意力，目前通过
  GitHub `priority/*` 标签 + Slack 通告解决。

## Alternatives

- **Git Flow**：3-5 人团队下 release 分支管理反而拖慢迭代，且没有专职 release
  manager 角色，pass。
- **GitHub Flow**：与 Trunk-based 高度相似，但允许分支寿命更长；本团队迭代节奏
  短，Trunk-based 的"短分支强制约束"更契合，pass。
- **GitLab Flow (environment branches)**：依赖环境分支（staging / production），
  与我们 "main 即生产" 的部署模型冲突，pass。