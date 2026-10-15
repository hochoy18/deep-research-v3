# Feature Specification: M1 - 基础设施脚手架

**Feature ID**: `FEATURE-001-m1-infra`
**Feature Branch**: `feature/001-m1-infra`
**Created**: 2026-10-15
**Status**: Draft
**Owner**: TBD（constitution V 要求显式声明；M1 kickoff 时指定 — 1 主 Owner + N 个 Co-Owner，见 Q5 澄清）
**Milestone**: M1 - 基础设施（W1）

**Input**: User description: "基于 docs/milestones.md §M1 + docs/architecture.md §2 生成 M1 spec.md"

---

## Clarifications

### Session 2026-10-15

- Q: M1 阶段 mock 对话流要演示到哪个深度？→ A: **极简 echo**（单 LangGraph 节点，后端把用户 query 流式切片返回；不写 Planner/Researcher/Writer/Critic 占位代码；M2+ 引入真实 4 Agent 编排）
- Q: M1 阶段无鉴权下（ADR-0009 v1 no auth）thread 如何归属？→ A: **浏览器匿名 ID**：首次访问后端生成随机匿名 user_id，通过 httpOnly + SameSite=Lax cookie 持久化 30 天；thread 与 user_id 绑定，后端按 user_id 过滤防越权；不要求登录
- Q: M1 阶段无鉴权下是否需要 rate limit / 滥用防护？→ A: **简化 IP 限流**：后端按 IP + 匿名 user_id 二元组限流；阈值：每用户每分钟 ≤ 10 次查询、每小时 ≤ 100 次；超限返回 HTTP 429 + 友好错误信息；用于防误点 / 脚本压测
- Q: M1 阶段 constitution III 要求的"关键路径测试覆盖率 ≥ 80%"具体覆盖哪些范围？→ A: **4 条关键路径**：(1) query 提交 → mock 流式响应全链路；(2) thread 创建 / 列表 / 重开；(3) 匿名 cookie 生成与限流逻辑；(4) 可观测性 trace 写入。其余 UI 装饰 / 配置加载 / 镜像拉取不纳入强制门禁（constitution III 豁免）
- Q: constitution V 要求每个 feature 有且仅有一个 Owner；M1 spec 5 个 user story 的 Owner 模式？→ A: **1 个主 Owner + 多 Co-Owner**：1 个主 Owner 负总责（业务决策 + 跨团队沟通 + Converge-Gate 签字）；每个 user story 配 1 个 Co-Owner 负责该 story 的设计 / 实施 / 交付；具体姓名由 M1 kickoff 时按团队实际人数分配并写入 Owner 矩阵

---

## Owner 矩阵（constitution V — 待 M1 kickoff 时填充）

| 角色 | 姓名 | 负责 User Story | 负责关键路径 | 职责 |
|---|---|---|---|---|
| **主 Owner** | TBD | 全部 5 个 | 全部 4 条 | 业务决策 / 跨团队沟通 / Converge-Gate 签字 / 复盘 |
| **Co-Owner #1** | TBD | US-1（一键起服务栈） | 路径 1（部分） | 后端 / 部署 / CI 流水线 |
| **Co-Owner #2** | TBD | US-2（端到端 mock 对话流） | 路径 1 + 路径 4 | LangGraph 编排 / SSE / 可观测性接入 |
| **Co-Owner #3** | TBD | US-3（PR 质量门禁） | 路径 4 | CI pipeline / SAST / SCA / pre-commit |
| **Co-Owner #4** | TBD | US-4（单测一键跑）+ US-5（团队代码归属） | 路径 2 + 路径 3 | 测试 / CODEOWNERS / PR 模板 |

> 上述 4 个 Co-Owner 占位基于 milestones §M1 "4 人并行" 假设；具体姓名与精确分工由 M1 kickoff 时确定并回填此表。

---

## User Scenarios & Testing

### User Story 1 - 一键起服务栈（Priority: P1）

开发者拉取仓库后，能在本地一键启动所有依赖服务（数据库、缓存、可观测性平台、后端应用、前端应用），并在 5 分钟内完成从 clone 到看到本地界面。

**Why this priority**：没有这个能力，团队任何后续开发都无法启动本地环境；是 M1 端到端 demo 的前置条件。

**Independent Test**：在干净 macOS / Linux 机器上 clone 仓库 → 运行一条命令 → 浏览器自动打开界面。

**Acceptance Scenarios**：

1. **Given** 开发者首次拉取仓库，**When** 运行 `task dev:up`，**Then** 在 5 分钟内所有服务全部就绪（数据库、缓存、可观测性平台、后端、前端），无报错。
2. **Given** 服务全部就绪，**When** 开发者访问对话界面 URL，**Then** 看到对话界面（可输入 query 状态）。
3. **Given** 服务在运行，**When** 开发者运行 `task dev:down`，**Then** 所有服务干净停止、端口释放。

---

### User Story 2 - 端到端 mock 对话流（Priority: P1）

用户在浏览器输入 query 后，能看到后端推送的 mock 流式响应（无需真实 LLM），且可观测性平台能看到本次请求的完整 trace。

**Why this priority**：这是 M1 阶段对外最直观的"价值演示"——证明端到端链路打通（前端 → 后端 → Agent 编排 → 流式输出 → 可观测性），是 M2+ 用真实检索 / 写作能力替换 mock 的基础。

**Independent Test**：浏览器打开界面 → 输入 query → 看到流式响应 → 打开可观测性 UI 看到 trace。

**Acceptance Scenarios**：

1. **Given** 服务全部就绪，**When** 用户在浏览器输入 query 并提交，**Then** 后端通过流式连接逐步推送 mock 响应内容。
2. **Given** mock 响应正在推送，**When** 前端接收，**Then** Markdown 内容逐步渲染到对话流中。
3. **Given** 用户完成一次对话，**When** 开发者打开可观测性 UI，**Then** 能看到本次请求的完整 trace（含节点名、耗时、输入输出）。
4. **Given** mock 响应进行中，**When** 用户刷新页面，**Then** 不丢失已渲染的内容（依赖状态检查点 + 状态恢复）。
5. **Given** mock 响应推送完毕，**When** 用户重新打开同一 thread，**Then** 能看到完整对话历史。

---

### User Story 3 - PR 全流程质量门禁（Priority: P1）

开发者每次提交 PR，必须自动跑过代码质量门禁（代码风格、单测、构建、安全扫描），且覆盖率与测试结果作为合并门禁的一部分。

**Why this priority**：constitution I / III / IV 要求所有 PR 必经 SAST / SCA + 关键路径测试覆盖率 ≥ 80% + Converge-Gate；M1 必须把这条门禁落地，否则后续 milestone 都无法保证质量。

**Independent Test**：开一个故意失败的 PR（覆盖率不达标 / 含高危漏洞）→ CI 阻断合并；开一个合规 PR → CI 全绿。

**Acceptance Scenarios**：

1. **Given** 开发者提交 PR，**When** CI 触发，**Then** 自动跑代码风格检查、单元测试、构建。
2. **Given** PR 包含关键路径代码，**When** CI 触发，**Then** 关键路径测试覆盖率 ≥ 80%，否则合并被阻断。
3. **Given** PR 引入高危安全漏洞，**When** CI 触发，**Then** SAST 扫描必须阻断合并。
4. **Given** PR 引入带漏洞的第三方依赖，**When** CI 触发，**Then** SCA 扫描必须阻断合并。
5. **Given** PR 描述中未引用 spec ID，**When** CI 触发，**Then** 合并被阻断。
6. **Given** 开发者本地提交，**When** pre-commit 触发，**Then** 自动跑 secret 扫描与代码风格，避免脏 commit 进入仓库。

---

### User Story 4 - 单测 / 集成测试可本地一键跑（Priority: P2）

开发者能在本地一键跑全部测试，无需额外配置，验证 PR 是否会通过 CI。

**Why this priority**：降低"本地通过但 CI 失败"的概率；让 TDD 循环在本地可闭环。

**Independent Test**：运行 `task backend:test` → 看到全部后端测试通过；运行 `task frontend:test` → 看到全部前端测试通过。

**Acceptance Scenarios**：

1. **Given** 开发者本地有 Python / Node 环境，**When** 运行 `task backend:test`，**Then** 看到后端单测全绿。
2. **Given** 开发者本地有 Node 环境，**When** 运行 `task frontend:test`，**Then** 看到前端单测全绿。
3. **Given** mock LLM 已配置，**When** 运行集成测试，**Then** 端到端 demo 的核心路径可重放（无需真实 LLM）。

---

### User Story 5 - 团队代码归属与审批（Priority: P2）

开发者提交 PR 时，CI 自动按目录路由审批人，相关团队 Owner 必须审批后才能合并。

**Why this priority**：跨团队协作时，PR 审批责任必须落到明确的人；constitution 开发工作流要求"跨团队 reviewer"。

**Independent Test**：提交一个 PR → 自动分配 reviewer → Owner 审批 → 合并。

**Acceptance Scenarios**：

1. **Given** 开发者改了某个目录的代码，**When** 提交 PR，**Then** CODEOWNERS 自动分配对应 Owner 为 reviewer。
2. **Given** PR 需要跨团队 reviewer，**When** 提交 PR，**Then** 自动请求 1 个非作者团队成员审批。
3. **Given** PR 涉及核心原则（Security / API Contract / 可观测性 / Spec 引用 / Converge-Gate / Owner），**When** 提交 PR，**Then** 必须由对应领域负责人审批。

---

### Edge Cases

- **服务启动失败（端口被占用）**：开发者运行 `task dev:up` → 检测到冲突端口 → 给出明确错误信息 + 修复建议，不静默失败。
- **可观测性平台不可用**：mock 对话流仍能跑通，但 trace 不写入；日志中明确警告，不影响演示。
- **服务中途崩溃**：浏览器端显示友好错误，不白屏；后端 / 前端日志含错误堆栈。
- **网络中断 / SSE 断连**：前端自动重连，已渲染内容不丢失。
- **首次启动慢（镜像拉取）**：README 明确镜像大小与首次启动预期耗时，避免误判为 bug。
- **环境变量缺失**：`.env.example` 模板 + 启动时检查必备变量，缺失给出明确提示。
- **跨刷新后状态不一致**：thread ID 持久化到 URL，刷新后从 checkpoint 恢复，保证内容连续。
- **并发用户（多浏览器）**：同一 thread 的并发请求应独立处理，不互相覆盖（依赖 LangGraph 线程隔离）。
- **限流触发**：单 IP + user_id 在 1 分钟内发起第 11 次请求时 MUST 返回 HTTP 429 + 友好错误 + 剩余冷却秒数；UI 需显示"操作太频繁，请稍后再试"。
- **cookie 失效/清除**：user_id cookie 过期或被用户清除后，访问时视为新用户（新匿名 ID），历史 thread 不可见；不报错，仅显示空对话列表。

---

## Requirements

### Functional Requirements

**服务栈启动与停止**
- **FR-001**：系统 MUST 提供一条命令一键启动所有本地依赖服务与本地应用，并在 5 分钟内全部就绪。
- **FR-002**：系统 MUST 提供一条命令一键停止所有服务并释放端口。
- **FR-003**：系统 MUST 在启动时检测端口冲突并给出明确修复建议。
- **FR-004**：系统 MUST 提供 `.env.example` 模板覆盖所有运行所需环境变量；启动时 MUST 校验必备变量，缺失时给出明确错误。
- **FR-005**：系统 MUST 包含以下本地服务：数据库、缓存、可观测性平台、后端应用、前端应用（参考 architecture §2 组件全景）。

**端到端 mock 对话流**
- **FR-006**：用户 MUST 能在浏览器对话界面输入 query 并提交。
- **FR-007**：后端 MUST 通过单一 LangGraph 节点（极简 echo）通过流式连接逐步推送 mock 响应内容（流式切片 = 按 token 切分 query 字符串回显），模拟 LLM 流式输出。M1 阶段不实现 Planner/Researcher/Writer/Critic 4 Agent 编排。
- **FR-008**：前端 MUST 接收流式内容并按 Markdown 逐步渲染到对话流。
- **FR-009**：每次对话请求 MUST 写入可观测性 trace，含节点名 / 耗时 / 输入输出。M1 阶段 trace 至少包含"单节点名称 + 输入 query + 输出 mock 切片"三字段。
- **FR-010**：系统 MUST 支持用户刷新页面后不丢失已渲染内容（依赖状态检查点 + 状态恢复）。刷新后 MUST 通过 cookie 中的 user_id 找到对应 thread 状态。
- **FR-011**：系统 MUST 支持用户重新打开同一 thread 后看到完整对话历史，且 MUST 只返回当前 user_id 所属的 thread（防越权读取）。
- **FR-011a**（新增）：系统 MUST 在用户首次访问时通过后端生成不可猜测的匿名 user_id（UUID v4 长度 36），通过 httpOnly + Secure + SameSite=Lax cookie 持久化 30 天；M1 不要求登录；后端按 user_id 过滤所有 thread 查询。
- **FR-011b**（新增）：系统 MUST 按 `IP + 匿名 user_id` 二元组限流：每用户每分钟 ≤ 10 次查询、每小时 ≤ 100 次；超限返回 HTTP 429 + 友好错误信息（含剩余冷却时间）；用于防误点与脚本压测，不用于鉴权。

**质量门禁（CI / pre-commit）**
- **FR-012**：每个 PR MUST 自动触发 CI 流水线，含：代码风格检查、单元测试、构建、SAST 扫描、SCA 扫描。
- **FR-013**：关键路径测试覆盖率 MUST ≥ 80%，不达标 MUST 阻断合并（constitution III）。
- **FR-014**：高危 SAST / SCA 漏洞 MUST 阻断合并（constitution I）。
- **FR-015**：pre-commit MUST 包含 secret 扫描与代码风格检查（避免脏 commit 入库）。
- **FR-016**：PR 描述 MUST 引用 spec ID（constitution II），缺失 MUST 阻断合并。

**单测 / 集成测试**
- **FR-017**：开发者 MUST 能在本地一键跑全部测试（后端 + 前端）。
- **FR-018**：集成测试 MUST 用 mock LLM 实现端到端核心路径可重放，不依赖真实 LLM。
- **FR-019**：测试框架 MUST 支持覆盖率统计并输出报告（关键路径 ≥ 80%）。

**代码归属与审批**
- **FR-020**：系统 MUST 维护 CODEOWNERS 文件，按目录划分 Owner。
- **FR-021**：涉及核心原则（Security / API Contract / 可观测性 / Spec 引用 / Converge-Gate / Owner）的 PR MUST 由对应领域负责人审批。

**Spec 引用与 Owner**
- **FR-022**：本 spec 文档 MUST 显式声明 `Owner:` 字段（constitution V）。
- **FR-023**：每次 PR MUST 在描述中引用 spec ID（constitution II）。

### Key Entities

- **Thread（会话线程）**：用户发起的一次研究会话的容器，含 query、对话历史、状态、关联 trace ID、所属 user_id（匿名 ID）。
- **Message（消息）**：对话流中的单条消息，含发送方（user / agent）、内容、状态、生成时间、所属 thread_id。
- **User（匿名用户）**：M1 阶段无登录账号，仅由后端首次访问时生成的匿名 user_id 标识（UUID v4，存于 httpOnly cookie，TTL 30 天）。
- **Trace（追踪）**：一次请求的完整执行轨迹，含节点名、耗时、输入输出、关联 Thread。
- **Service（本地服务）**：通过一键命令启动的本地服务实例（含数据库、缓存、可观测性平台、后端、前端）。

---

## Success Criteria

### Measurable Outcomes

- **SC-001**：开发者在干净机器上从 clone 到看到本地界面的时间 ≤ 5 分钟（含镜像拉取）。
- **SC-002**：端到端 mock 对话流全链路成功率 = 100%（演示 10 次全部成功）。M1 阶段 mock 流式响应 MUST 在 3 秒内完成（单节点 echo 切片输出）。
- **SC-003**：用户在浏览器输入 query 到首字呈现的延迟 ≤ 500ms（不含 LLM 推理）。
- **SC-004**：可观测性 UI 上能查到 100% 的端到端 demo 请求 trace。
- **SC-005**：PR 流水线在 10 分钟内完成（含 lint + test + build + SAST + SCA）。
- **SC-006**：关键路径测试覆盖率 ≥ 80%（constitution III 强制门禁）。M1 阶段关键路径 = 4 条：
  - 路径 1：query 提交 → 后端 mock 流式响应全链路（提交 → cookie 校验 → 限流校验 → LangGraph 单节点 → SSE 推送 → trace 写入）
  - 路径 2：thread 创建 / 列表查询 / 重开（按 user_id 过滤）
  - 路径 3：匿名 user_id cookie 生成 + 限流逻辑（IP + user_id 二元组，超限返回 429）
  - 路径 4：可观测性 trace 写入（节点名 / 输入 query / 输出 mock 切片三字段）
- **SC-007**：本地 `task backend:test` / `task frontend:test` 跑通率 100%，且结果与 CI 一致。
- **SC-008**：开发者 PR 描述中 spec ID 引用率 = 100%（缺失阻断）。
- **SC-009**：M1 端到端 demo 在集成日 1 次跑通，团队对 4 人并行开发的体验评分 ≥ 4/5。
- **SC-010**：同一 thread 跨刷新 / 跨会话重开的对话历史完整率 = 100%。
- **SC-011**（新增）：跨用户隔离正确率 = 100%（用户 A 在 cookie 隔离下无法通过猜测 thread_id 读到用户 B 的 thread；M1 集成日手测 5 次跨用户尝试全部失败）。
- **SC-012**（新增）：限流生效正确率 = 100%（单 IP 单 user_id 在 1 分钟内发起 11 次请求，第 11 次 MUST 返回 HTTP 429；M1 集成日手测 1 次）。

---

## Assumptions

- **目标用户**：hochoy 内部研发人员（3 个团队的工程师），熟悉 macOS / Linux 命令行 + Docker 基础。
- **运行环境**：干净 macOS 14+ / Linux 容器，Docker 已安装并能运行（无需 root 权限）。
- **范围边界**：M1 仅做 mock 对话流（不接真实 LLM、不实现 Planner / Researcher / Writer / Critic）；真实检索 / 写作能力在 M2 / M3 替换。
- **范围边界**：M1 不实现鉴权 / 权限（v1 不接鉴权，详见 ADR-0009）。
- **数据保留**：M1 阶段对话历史保留 ≥ 7 天（依赖状态检查点 TTL）；长期存储在 M4 评估阶段补齐。
- **依赖**：假设可访问公网拉取 Docker 镜像（数据库 / 缓存 / 可观测性平台 等）。
- **外部输入**：M1 阶段用户输入的 query 视为不可信（即使没有鉴权）→ 必须经过白名单校验（constitution I）。
- **mock LLM 实现**：假设 mock LLM 通过固定 prompt + 固定返回实现（如"输入 X 返回固定 Y"），不依赖任何 LLM 供应商。
- **关键路径定义（M1 阶段）**：constitution III 强制关键路径覆盖率 ≥ 80%；M1 阶段关键路径 = 4 条（见 SC-006）；其余 UI 装饰 / 镜像拉取 / 配置加载视为非关键路径（constitution III 豁免），推荐覆盖但不强制。

---

## Out of Scope（M1 不做）

- 真实 LLM 接入（用 mock 替代）
- Planner / Researcher / Writer / Critic 4 Agent 完整实现（M2 / M3 / M4）
- 鉴权 / 权限（v1 不接，详见 ADR-0009）
- 评估 / HotpotQA / LLM-as-judge（M4）
- 真实检索工具（M2）
- PDF 导出（M3）
- 移动端 / 多语言
- 生产部署（M1 仅本地演示）

---

## Dependencies

### 设计文档（已就绪）

- [`docs/milestones.md`](../../docs/milestones.md) §M1 端到端 demo + 验收标准
- [`docs/architecture.md`](../../docs/architecture.md) §2 组件全景 + §3 组件职责
- [`docs/agent-design.md`](../../docs/agent-design.md) §2 BaseAgent 抽象（M1 阶段占位即可）
- [`docs/graph-design.md`](../../docs/graph-design.md) §3 单 Agent trace（M1 不需要完整 4 Agent）
- [`docs/observability.md`](../../docs/observability.md) 可观测性平台接入
- [`docs/eval.md`](../../docs/eval.md) 评估（仅作 M1 关键路径测试参考）
- [`docs/deployment.md`](../../docs/deployment.md) 部署（M1 仅本地一键启动）
- [`docs/contributing.md`](../../docs/contributing.md) commit 规范 / PR 流程

### 决策依据（12 篇 ADR，已就绪）

- [ADR-0004 single-repo over monorepo](../../docs/adr/0004-single-repo-over-monorepo.md)
- [ADR-0007 Tailwind v4 CSS-first](../../docs/adr/0007-tailwind-v4-css-first.md)
- [ADR-0008 trunk-based over git-flow](../../docs/adr/0008-trunk-based-over-git-flow.md)
- [ADR-0009 v1 no auth](../../docs/adr/0009-v1-no-auth.md)
- [ADR-0012 Python 3.12](../../docs/adr/0012-python-3.12.md)

### 治理

- [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md) v1.1.0（8 大原则 + CI Gates）

---

## Constitution 对齐

| 原则 | M1 落地方式 |
|---|---|
| **I. Security-First** | `.env.example` + 启动校验 + SAST/SCA + 用户输入白名单 |
| **II. Spec-Traceable** | PR 模板强制 `Spec:` 字段，CI 校验 |
| **III. Test-First** | 关键路径测试覆盖率 ≥ 80%，CI 阻断 |
| **IV. Converge-Gate** | M1 集成日全绿后才归档 |
| **V. One-Feature-Owner** | 本 spec 显式声明 Owner（M1 kickoff 时指定） |
| **VI. API Contract** | M1 末 freeze OpenAPI schema（M2 接入） |
| **VII. Observability by Default** | 可观测性平台 trace 接入（mock trace 可见） |
| **VIII. 简洁优先** | 模块化单体（不分微服务） |
