# ADR 0009: v1 单用户模式，不实现认证

- Status: Accepted
- Date: 2026-10-15
- Deciders: @cai.he, @hochoy

## Context

deep-research v1 是面向 hochoy 团队的内部研究工具，部署在自有 homelab，
访问入口为内网域名 `dr.internal.hochoy.cn`。当前阶段：

- 实际用户仅 1-3 人（owner + 1-2 名 reviewer），无外部用户；
- 数据敏感度中等（涉及内部研究选题与部分未公开报告），但受内网防火墙保护；
- v1 目标为"6 周内打通 LangGraph + Langfuse + HITL 闭环"，验证产品形态；
- v2 计划把工具开放给 hochoy 全体 ~30 名研究员使用，并外加 1-2 个外部客户。

需要在 v1 时间盒内决定：是否同步实现认证体系？

### 方案 C1: v1 即实现完整认证（邮箱+密码 / SSO）

在 v1 内同步引入 NextAuth.js 或自研 JWT 体系，含注册、登录、会话、密码重置、
OAuth、RBAC。预估 +2 周工作量。

### 方案 C2: v1 不做认证，v2 再加

v1 部署在 `dr.internal.hochoy.cn`，依赖内网防火墙 + Cloudflare Tunnel 做访问控制；
v2 提前预留 `auth.users`、`sessions`、`oauth_providers` 表，迁移成本可控。

## Decision

**采用方案 C2：v1 不实现任何形式的认证。** 具体约束：

- 服务不开放到公网，仅通过 Cloudflare Tunnel 暴露给内网；
- LangGraph server 的 `auth` handler 留空，所有 endpoint 默认接受任何请求；
- 数据模型从 Day 1 预留 `User` 表与 `user_id` 外键，但表中只有 1 条记录
  （即 owner 占位）；
- v1 不实现 session、cookie、CSRF token；
- 文档、ADR、README 中明确标注 `NOT FOR PUBLIC INTERNET`。

## Consequences

正面：

- v1 时间盒（6 周）可专注核心研究流，认证延后节省 ~2 周工作量；
- 减少 v1 测试矩阵（无需覆盖注册、找回密码、OAuth 回调等边界）；
- 部署简单：docker compose 起 Next.js + LangGraph + Redis + Postgres + Langfuse
  即可，无需反向代理 + auth 中间件编排。

负面 / 约束：

- 任何能访问 `dr.internal.hochoy.cn` 的人都能调用全部接口，包括删除研究历史；
- v1 阶段如果出现误操作（比如 LangGraph 中误发 `thread.delete`），无审计
  trail 追责；当前缓解：Redis + Postgres 日志保留 90 天；
- v2 加认证时需做一次破坏性数据迁移：将 v1 历史 `thread_id` 归属到占位 user
  下，并让用户重新认领。已在 `docs/migration/v1-to-v2-auth.md` 留占位。

## Alternatives

- **v1 即上 NextAuth**：增加 2 周工作量，且 1-3 人用户场景下 99% 的代码路径
  不会被触发，投入产出比极低，pass。
- **Basic Auth 中间件**：技术成本低（nginx `auth_basic` 即可），但用户体验差且
  无法演进到 OAuth / SSO，对 v2 来说仍是 100% 重写，pass。
- **API Key 鉴权**：v1 仅 1-3 人，API Key 比邮箱密码更简洁；但 v2 需要多人协作
  时 API Key 仍需做完整用户体系，本质上是把认证问题延迟而非消除，pass。