  # M1 Day 1 Kickoff Brief

  ## 启动时间：2026-10-16

  ## 6 个分支
  - feature/001-m1-infra（bootstrap，TL.cai 兜底）
  - feat/m1-us1-infra（Dev.cai.1）
  - feat/m1-us2-echo-backend（Dev.cai.2）
  - feat/m1-us2-frontend（Dev.cai.3）
  - feat/m1-us3-pr-gate（Dev.cai.3）
  - feat/m1-us4-tests-owners（Dev.cai.4）

  ## 集成顺序（README §M1 A.2）
  D → A → B → C → demo

  ## 4 个 worktree
  - ../v3-us1-infra       → Dev.cai.1
  - ../v3-us2-backend     → Dev.cai.2
  - ../v3-us2-frontend    → Dev.cai.3
  - ../v3-us4-tests       → Dev.cai.4
 BRIEF_EOF
