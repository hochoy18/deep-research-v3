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
