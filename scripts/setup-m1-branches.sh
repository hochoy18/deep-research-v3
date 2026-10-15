#!/usr/bin/env bash
# =============================================================================
# setup-m1-branches.sh
# -----------------------------------------------------------------------------
# 用途：为 M1 (FEATURE-001-m1-infra) 阶段自动创建 5 个 Owner 分支（+ main 兜底），
#       推送 origin，配置 .github/CODEOWNERS、PR 模板、Issue 模板，
#       并尝试设置 branch protection（需要 admin 权限；失败不阻断）。
#
# 幂等：已存在的分支 / 目录 / 模板不会被覆盖，只在日志中标注 SKIP。
# 用法：./scripts/setup-m1-branches.sh [--dry-run]
# 前置：git 已配置 user.name / user.email；gh 已认证；当前在 main。
# =============================================================================

set +e  # 不开 -e/-u：单步失败不中断整体（最后统一报告）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# ---- 参数 ----
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "🟡 DRY RUN 模式 — 不会推送 / 不会写文件"
fi

# ---- 常量 ----
PROTECTED_BRANCH=("main")
MAIN_BRANCH="main"

# 5 个 Owner 工作分支（TL.cai 在 main 上兜底，不开独立分支）
WORK_BRANCHES=(
  "feat/m1-us1-infra:Dev.cai.1"
  "feat/m1-us2-echo-backend:Dev.cai.2"
  "feat/m1-us2-frontend:Dev.cai.3"
  "feat/m1-us3-pr-gate:Dev.cai.3"
  "feat/m1-us4-tests-owners:Dev.cai.4"
)
BOOTSTRAP_BRANCH="001-m1-infra"  # 主 Owner 用的初始 bootstrap 分支

# ---- 工具函数 ----
step()  { printf "\n\033[1;34m▶ %s\033[0m\n" "$1"; }
ok()    { printf "  \033[1;32m✅ %s\033[0m\n" "$1"; }
warn()  { printf "  \033[1;33m⚠️  %s\033[0m\n" "$1"; }
fail()  { printf "  \033[1;31m❌ %s\033[0m\n" "$1"; }
skip()  { printf "  \033[1;90m⏭  %s\033[0m\n" "$1"; }

# ---- 预检 ----
step "0. 预检环境"
git rev-parse --git-dir > /dev/null 2>&1 || { fail "不在 git 仓库中"; exit 1; }
git config user.name > /dev/null 2>&1 || { fail "未配置 git user.name"; exit 1; }
git config user.email > /dev/null 2>&1 || { fail "未配置 git user.email"; exit 1; }

REMOTE_URL=$(git config --get remote.origin.url || echo "")
if [[ -z "$REMOTE_URL" ]]; then
  fail "未配置 remote.origin.url"; exit 1
fi
ok "git remote: $REMOTE_URL"

if gh auth status > /dev/null 2>&1; then
  ok "gh CLI 已认证"
else
  warn "gh CLI 未认证 — branch protection 设置将跳过"
fi

# 确保在 main 上
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "$MAIN_BRANCH" ]]; then
  warn "当前不在 main 分支（当前: $CURRENT_BRANCH），切换到 main"
  git checkout "$MAIN_BRANCH" || { fail "无法切换到 main"; exit 1; }
fi
git pull --ff-only origin "$MAIN_BRANCH" 2>/dev/null || warn "无法 fast-forward main（可能本地有未推送改动）"
ok "已在 main 分支，最新 commit: $(git rev-parse --short HEAD)"

# =============================================================================
# 1. 创建 bootstrap 分支（主 Owner 用）
# =============================================================================
step "1. 创建 bootstrap 分支 $BOOTSTRAP_BRANCH（主 Owner 兜底）"

if git show-ref --verify --quiet "refs/heads/$BOOTSTRAP_BRANCH"; then
  skip "本地分支 $BOOTSTRAP_BRANCH 已存在"
else
  if $DRY_RUN; then
    ok "[DRY] git checkout -b $BOOTSTRAP_BRANCH"
  else
    git checkout -b "$BOOTSTRAP_BRANCH"
    ok "已创建本地分支 $BOOTSTRAP_BRANCH"
  fi
fi

if ! $DRY_RUN; then
  if git ls-remote --heads origin "$BOOTSTRAP_BRANCH" 2>/dev/null | grep -q "$BOOTSTRAP_BRANCH"; then
    skip "远端 origin/$BOOTSTRAP_BRANCH 已存在"
  else
    git push -u origin "$BOOTSTRAP_BRANCH" 2>&1 | head -3
    ok "已推送 origin/$BOOTSTRAP_BRANCH"
  fi
fi

# 回到 main
git checkout "$MAIN_BRANCH" > /dev/null 2>&1

# =============================================================================
# 2. 为 5 个 Owner 创建工作分支
# =============================================================================
step "2. 创建 5 个 Owner 工作分支"

for entry in "${WORK_BRANCHES[@]}"; do
  branch="${entry%%:*}"
  owner="${entry##*:}"

  if git show-ref --verify --quiet "refs/heads/$branch"; then
    skip "本地分支 $branch 已存在"
  else
    if $DRY_RUN; then
      ok "[DRY] git checkout -b $branch (from main)"
    else
      git checkout -b "$branch" "$MAIN_BRANCH" > /dev/null
      ok "已创建 $branch (owner: $owner)"
    fi
  fi

  if ! $DRY_RUN; then
    if git ls-remote --heads origin "$branch" 2>/dev/null | grep -q "$branch"; then
      skip "远端 origin/$branch 已存在"
    else
      git push -u origin "$branch" 2>&1 | tail -1
      ok "已推送 origin/$branch"
    fi
    git checkout "$MAIN_BRANCH" > /dev/null 2>&1
  fi
done

# =============================================================================
# 3. 创建 .github/CODEOWNERS
# =============================================================================
step "3. 创建 .github/CODEOWNERS（路径 → Owner 路由）"

mkdir -p .github/ISSUE_TEMPLATE

CODEOWNERS_FILE=".github/CODEOWNERS"
cat > "$CODEOWNERS_FILE" <<'CODEOWNERS_EOF'
# =============================================================================
# CODEOWNERS — Deep Research M1 (FEATURE-001-m1-infra)
# =============================================================================
# 路径 → Owner 自动路由规则。PR 改动对应路径时，GitHub 自动请求 review。
# Owner 格式：@<github-username>（constitution V + spec Q5）
#
# 注意：以下 username 是 M1 Kickoff 阶段的占位符，集成日前由 TL.cai 回填为
# 真实 GitHub 用户名。所有者矩阵见 specs/001-m1-infra/plan.md §Owner 矩阵。
# =============================================================================

# --- 主 Owner 兜底（最后兜底） ---
*                                                  @TL.cai

# --- 后端（Python / LangGraph / DB） ---
/research_backend/                                 @Dev.cai.2 @Dev.cai.1
/research_backend/app/agents/                      @Dev.cai.2
/research_backend/app/graph/                       @Dev.cai.2
/research_backend/app/api/                         @Dev.cai.2 @Dev.cai.1
/research_backend/app/db/                          @Dev.cai.1
/research_backend/app/auth/                        @Dev.cai.1
/research_backend/app/ratelimit/                   @Dev.cai.1
/research_backend/app/observability/               @Dev.cai.1
/research_backend/tests/integration/               @Dev.cai.2 @Dev.cai.1
/research_backend/tests/unit/                      @Dev.cai.2

# --- 前端（Next.js / React / Tailwind） ---
/research_frontend/                                @Dev.cai.3
/research_frontend/app/                            @Dev.cai.3
/research_frontend/components/                     @Dev.cai.3
/research_frontend/lib/                            @Dev.cai.3
/research_frontend/tests/                          @Dev.cai.3

# --- 部署 / 基础设施 ---
/deploy/                                           @Dev.cai.1
/docker-compose*.yml                               @Dev.cai.1
/Taskfile.yml                                      @Dev.cai.1
/.env.example                                      @Dev.cai.1

# --- CI / 质量门禁 / 安全 ---
/.github/workflows/                                @Dev.cai.3
/.pre-commit-config.yaml                           @Dev.cai.3
/bandit.yaml                                       @Dev.cai.3
/.gitleaks.toml                                    @Dev.cai.3

# --- 测试基础设施 / 单测一键跑 ---
/scripts/                                         @Dev.cai.4
/pyproject.toml                                    @Dev.cai.4
/.coveragerc                                       @Dev.cai.4

# --- 文档 / Spec / 治理（TL.cai 主导） ---
/docs/                                             @TL.cai
/specs/                                            @TL.cai
/.specify/                                         @TL.cai
/README.md                                         @TL.cai
CODEOWNERS                                         @TL.cai
CODEOWNERS_EOF

if $DRY_RUN; then
  skip "[DRY] 跳过写 $CODEOWNERS_FILE"
else
  git add "$CODEOWNERS_FILE"
  git diff --cached --quiet || git commit -m "chore(github): add CODEOWNERS for M1 Owner routing

Spec: FEATURE-001-m1-infra
Owner: TL.cai
Type: config
Converge: N/A
Tests: N/A
Observability: N/A
Security: N/A" > /dev/null 2>&1
  ok "已写入 $CODEOWNERS_FILE 并 commit 到 main"
fi

# =============================================================================
# 4. 创建 PR 模板
# =============================================================================
step "4. 创建 .github/PULL_REQUEST_TEMPLATE.md"

PR_TEMPLATE=".github/PULL_REQUEST_TEMPLATE.md"
cat > "$PR_TEMPLATE" <<'PR_TEMPLATE_EOF'
## 变更说明

<!-- 简述本次 PR 改了什么 / 为什么改 -->

## Spec 追溯（constitution II 强制）

| 字段 | 值 |
|---|---|
| **Spec** | FEATURE-###  <!-- 例：FEATURE-001-m1-infra --> |
| **Owner** | @<username>   <!-- 主 Owner 或执行 Co-Owner --> |
| **Type** | feat / fix / docs / config / test / refactor |
| **User Story** | US-#  <!-- 如适用；config/docs 可填 N/A --> |
| **Task** | T###  <!-- 对应 tasks.md 中的 task id --> |

## Converge 状态

- [ ] 本 PR 不需要新 Converge 任务（增量开发，跟随已有 tasks.md）
- [ ] 本 PR 是 `/speckit-converge` 新追加的 task（T###+）
- [ ] 本 PR 是 `/speckit-converge` post-impl 报告

## 测试（constitution III）

- [ ] 单元测试通过（`task backend:test` / `task frontend:test`）
- [ ] 关键路径 4 条覆盖率 ≥ 80%（如有修改）
- [ ] 集成测试通过（如有）
- [ ] Pact 契约测试通过（如修改 contracts/）

## 可观测性（constitution VII）

- [ ] Langfuse trace 写入验证（后端改动）
- [ ] 结构化日志新增字段（如适用）
- [ ] 不引入新的静默错误

## 安全（constitution I）

- [ ] bandit / pip-audit / npm audit 0 高危
- [ ] gitleaks 0 secret 泄露
- [ ] 用户输入白名单校验（如有改动 query 路径）
- [ ] 越权防护（如有改动 thread/message 权限）

## Reviewer

<!-- @CODEOWNERS 会自动加，但请显式 @ 跨团队 reviewer -->
- [ ] 路径 Owner @<...>
- [ ] 跨团队 reviewer @<...>

## Checklist

- [ ] 关联 GitHub Issue：#<id>
- [ ] commit message 含 Spec / Owner footer
- [ ] 不包含调试代码 / print / console.log
- [ ] 更新了相关文档（README / docs / spec）
PR_TEMPLATE_EOF

if $DRY_RUN; then
  skip "[DRY] 跳过写 $PR_TEMPLATE"
else
  git add "$PR_TEMPLATE"
  git diff --cached --quiet || git commit -m "chore(github): add PR template with Spec/Owner/Converge fields

Spec: FEATURE-001-m1-infra
Owner: Dev.cai.3
Type: config
Converge: N/A
Tests: N/A
Observability: N/A
Security: N/A" > /dev/null 2>&1
  ok "已写入 $PR_TEMPLATE 并 commit 到 main"
fi

# =============================================================================
# 5. 创建 Issue 模板（feature / bug）
# =============================================================================
step "5. 创建 .github/ISSUE_TEMPLATE/"

FEATURE_TEMPLATE=".github/ISSUE_TEMPLATE/feature.md"
cat > "$FEATURE_TEMPLATE" <<'FEATURE_TEMPLATE_EOF'
---
name: Feature Request
about: 新功能 / Spec 增量
title: "[FEATURE] "
labels: ["enhancement"]
assignees: []
---

## 背景

<!-- 为什么要做这个功能？解决什么用户/业务问题？ -->

## Spec 追溯

- **Spec ID**: FEATURE-###-slug
- **关联 User Story**: US-#
- **关联 Plan / Task**: tasks.md T### / plan.md §...

## 验收标准

- [ ] ...
- [ ] ...

## 影响面

- [ ] 后端 API 变更（需要更新 contracts/）
- [ ] 前端 UI 变更
- [ ] 数据库 schema 变更
- [ ] 配置 / 环境变量变更

## Owner

- @<github-username>
FEATURE_TEMPLATE_EOF

BUG_TEMPLATE=".github/ISSUE_TEMPLATE/bug.md"
cat > "$BUG_TEMPLATE" <<'BUG_TEMPLATE_EOF'
---
name: Bug Report
about: 缺陷报告
title: "[BUG] "
labels: ["bug"]
assignees: []
---

## 复现步骤

1. ...
2. ...
3. ...

## 预期行为

<!-- 应该发生什么 -->

## 实际行为

<!-- 实际发生什么 -->

## 环境

- 后端版本: <git-sha>
- 前端版本: <git-sha>
- 复现路径: <本地 / CI / 集成日 demo>

## 根因分析（可选）

<!-- 初步分析：日志 / 截图 / Langfuse trace link -->

## 关联

- **Spec**: FEATURE-###-...
- **Task**: T###
- **Owner**: @<github-username>
BUG_TEMPLATE_EOF

if $DRY_RUN; then
  skip "[DRY] 跳过写 Issue 模板"
else
  git add .github/ISSUE_TEMPLATE/
  git diff --cached --quiet || git commit -m "chore(github): add Issue templates (feature/bug)

Spec: FEATURE-001-m1-infra
Owner: Dev.cai.4
Type: config
Converge: N/A
Tests: N/A
Observability: N/A
Security: N/A" > /dev/null 2>&1
  ok "已写入 Issue 模板并 commit 到 main"
fi

# =============================================================================
# 6. 推送 main 兜底 commit
# =============================================================================
step "6. 推送 main 上的 .github/ 文件"

if $DRY_RUN; then
  skip "[DRY] 跳过 push"
else
  if git status --short | grep -q "^M\|?? \.github/"; then
    git push origin "$MAIN_BRANCH" 2>&1 | tail -3
    ok "已推送 .github/ 配置到 origin/main"
  else
    skip "main 无新 commit 需要推送"
  fi
fi

# =============================================================================
# 7. 尝试设置 branch protection（需要 admin 权限）
# =============================================================================
step "7. 尝试设置 branch protection（best effort）"

if $DRY_RUN; then
  skip "[DRY] 跳过 branch protection"
elif ! gh auth status > /dev/null 2>&1; then
  skip "gh CLI 未认证，跳过 branch protection"
else
  REPO_NAME="hochoy18/deep-research-v3"
  for branch in "${PROTECTED_BRANCH[@]}"; do
    echo "  → 设置 $branch 保护规则..."
    RESULT=$(gh api "repos/$REPO_NAME/branches/$branch/protection" \
      --method PUT \
      --field required_status_checks='{"strict":true,"contexts":["ci/lint","ci/test","ci/sast","ci/sca"]}' \
      --field enforce_admins=false \
      --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true,"require_code_owner_reviews":true}' \
      --field restrictions='null' \
      --field required_linear_history=true \
      --field allow_force_pushes=false \
      --field allow_deletions=false \
      2>&1) || true
    if echo "$RESULT" | grep -q '"url"'; then
      ok "$branch 保护已启用（CODEOWNERS + 1 review + 状态检查）"
    else
      warn "$branch 保护设置失败（可能无 admin 权限）：$RESULT" | head -c 200
    fi
  done
fi

# =============================================================================
# 8. 报告
# =============================================================================
step "8. 完成 — M1 分支与 GitHub 基础设施已就绪"

cat <<EOF

📊 总结
─────────────────────────────────────────────────
分支（本地）:
EOF
git branch --list "feat/m1-*" "$BOOTSTRAP_BRANCH" | sed 's/^/  /'

cat <<EOF
分支（远端）:
EOF
git branch -r | grep -E "feat/m1|$BOOTSTRAP_BRANCH" | sed 's/^/  /'

cat <<EOF
配置文件:
  .github/CODEOWNERS
  .github/PULL_REQUEST_TEMPLATE.md
  .github/ISSUE_TEMPLATE/feature.md
  .github/ISSUE_TEMPLATE/bug.md

下一步:
  1. 在 GitHub Web UI 检查分支列表
  2. Co-Owner 各自 git checkout 自己的分支
  3. 跑 /speckit.implement "执行 Phase 1 (T001-T015)" 启动 M1
─────────────────────────────────────────────────
EOF
