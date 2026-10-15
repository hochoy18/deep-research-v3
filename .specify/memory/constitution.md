<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0 (MINOR)
Rationale: 在五大核心原则基础上,新增 3 条原则(Spec-Traceable / Converge-Gate /
            One-Feature-Owner),并对 2 条既有原则进行强化(Security-First 增加
            SAST/SCA 强制门禁;Test-First 将覆盖率指标从"单元测试 ≥80%"
            收口为"关键路径 ≥80%",更贴合主链路质量)。

Modified principles (old → new):
  - I.  Security-First                    (强化: 新增 SAST/SCA 强制门禁条款)
  - III. Test-First (NON-NEGOTIABLE)      (收口: 覆盖率指标改为关键路径 ≥80%)

Added principles:
  - II.  Spec-Traceable                   (新增)
  - IV.  Converge-Gate                    (新增)
  - V.   One-Feature-Owner                (新增)

Renumbered (shifted by +3):
  - 原 III. API Contract 优先          → VI.
  - 原 IV.  可观测性默认                → VII.
  - 原 V.   简洁优先                    → VIII.

Added / updated sub-sections:
  - 开发工作流 - CI Gates: 新增 Spec-Trace / Converge-Gate / One-Feature-Owner / 关键路径覆盖率
  - 开发工作流 - PR 模板: 新增 Spec ID 字段与 Owner 字段
  - 治理(GOVERNANCE):无结构改动,仅补充与新增原则相关的合规性表述。

Follow-up TODOs: 无

Notes:
  - 所有占位符已替换,无遗留 `[ALL_CAPS_IDENTIFIER]` 标记。
  - 所有规范均使用 MUST/SHOULD/MAY 语气,避免模糊词。
  - 本项目由 3 个研发团队协作,本文档作为跨团队契约的最高约束。
  - Converge-Gate 与 One-Feature-Owner 与 Speckit 框架的
    `/speckit-converge`、`/speckit-specify`、`/speckit-tasks` 流程对齐。
-->

# Deep Research Agent Constitution
<!-- 极贝科技 hochoy Deep Research Agent 项目治理宪法。本项目由 3 个研发团队协作,
所有跨团队行为都必须以本宪法为最高约束,优先级高于各团队内部规范。 -->

## Core Principles

### I. Security-First（安全优先）
**规则**:所有外部输入 MUST 经过白名单校验;认证鉴权 MUST 在服务端执行;
任何审计敏感操作 MUST 记录 `actor`、`timestamp`、`reason` 三元组;
**任何 PR MUST 通过 SAST(静态应用安全测试)与 SCA(软件成分分析)扫描**。

**细则**:
- 外部输入(用户输入、第三方 API 响应、上传文件、外部检索结果)在进入业务逻辑前
  MUST 通过白名单校验(字段、长度、类型、来源)。
- 鉴权与授权 MUST 在服务端执行;前端 token 仅作调用凭证,不得承担策略决策。
- 涉及权限变更、数据导出、模型微调、审计日志读取等敏感操作 MUST 在审计日志中
  同时写入 `actor`(主体)、`timestamp`(UTC ISO 8601)、`reason`(可读文本说明)。
- **SAST / SCA 强制门禁**:
  - 每个 PR MUST 通过 SAST 扫描(代码层安全漏洞,例如 SQL 注入、XSS、不安全反序列化)。
  - 每个 PR MUST 通过 SCA 扫描(第三方依赖 CVE、许可证合规性、供应链完整性)。
  - **高危漏洞 MUST 阻断合并**;中危漏洞 MUST 在 7 天内修复;低危漏洞纳入技术债排期。
  - SAST/SCA 工具链 MUST 在 CI 中执行,扫描结果作为 PR 检查项,人工豁免 MUST
    由 Security Owner 书面批准并登记。
- 安全缺陷属于 P0 级别,一经发现 MUST 24 小时内修复或回滚。
- **理由**:Deep Research Agent 涉及外部检索与外部内容消费,边界由字面构成;
  漏掉白名单校验、审计记录,或引入带漏洞的第三方库,将导致数据泄露、合规事故
  与供应链攻击风险。SAST/SCA 是 CI 阶段对"代码 + 依赖"两端的硬性兜底。

### II. Spec-Traceable（规格可追溯）
**规则**:每个 PR MUST 引用一个 spec ID(规格标识符)。

**细则**:
- **spec ID 来源**:由 `/speckit-specify` 流程产出,命名格式
  `FEATURE-<编号>-<slug>`,例如 `FEATURE-007-streaming-pricing`。
- **PR 模板强制字段**:每个 PR MUST 在描述中填写 `Spec:` 字段,
  引用至少一个 spec ID;缺失 MUST 阻断合并。
- **hotfix 例外**:紧急生产修复(`hotfix/*`)允许在 PR 中先标注
  `Spec: HOTFIX-<日期>-<slug>`,但 MUST 在 5 个工作日内补建正式 spec 并 Converge。
- **跨 PR 关联**:同一 spec 的多个实现 PR MUST 在 PR 描述中互相 `Refs:` 链接,
  便于审计与回溯。
- **废弃 spec 处理**:spec 被废弃时 MUST 走 RFC 并标注 `Deprecated` 状态;
  仍引用此 spec ID 的 PR MUST 同时给出替代 spec 引用。
- **理由**:3 个团队并行迭代,代码变更若无法回溯到业务需求,会出现"实现
  了谁的需求"责任真空;Spec-Traceable 让需求 → 设计 → 实现 → 验证的链路
  永远可追溯,审计与责任归属可执行。

### III. Test-First (NON-NEGOTIABLE)（测试优先,不可妥协）
**规则**:TDD 强制循环(红 → 绿 → 重构);**关键路径测试覆盖率 ≥ 80%**;
集成测试覆盖所有权限和工作流分支。

**细则**:
- 任何业务代码提交前 MUST 先有失败的测试用例;严禁"先实现后补测"。
- 红绿重构循环 MUST 严格遵循:写失败测试 → 测试失败 → 写最小实现 →
  测试通过 → 重构 → 重测试。
- **关键路径定义**:以下代码路径视为关键路径,覆盖率 MUST ≥ 80%(行覆盖):
  - 检索 → 过滤 → 推理 → 生成主链路。
  - 鉴权与授权路径(含失败/越权分支)。
  - 状态机迁移路径(每个合法迁移 + 每个非法迁移)。
  - 外部 API 调用(含超时、重试、熔断、降级分支)。
  - 数据持久化与恢复路径。
- 非关键路径(纯展示型 UI、日志格式化、一次性迁移工具等)推荐覆盖,
  不纳入强制门禁。
- 集成测试 MUST 覆盖:每个权限分支(读/写/管理员)、每个工作流分支(成功/失败/重试)。
- 跨团队契约变更 MUST 先更新 Pact 契约测试,再实现,再联调。
- **理由**:深度研究路径长(检索 → 过滤 → 推理 → 生成),任何中间环节回归都会
  导致最终答案失真;TDD 与"关键路径高覆盖"组合,是控制多团队并行演进唯一
  可规模化执行的手段。"整体单元覆盖率"在大型工程中容易被工具膨胀稀释,
  把指标收口到"关键路径"更贴合业务风险。

### IV. Converge-Gate（收敛门禁）
**规则**:任何 feature MUST **Converged** 才能合并到 `main`/`release/*`。

**细则**:
- **Converged 判定**:feature 同时满足以下条件才算 Converged:
  1. `/speckit-specify` 产出 spec 文档(spec ID 已分配)。
  2. `/speckit-plan` 产出实现计划,与最终实现一致。
  3. `/speckit-tasks` 产出任务清单,所有任务 Closed。
  4. `/speckit-checklist` 全部勾选通过。
  5. `/speckit-analyze` 与 `/speckit-converge` 检测无未对齐项。
  6. CI 必备覆盖率自动达成(关键路径 ≥80%、SAST/SCA 通过、Pact 通过、性能基准)。
- **合并门禁**:任何 feature 分支的 PR 在合并前 MUST 在 PR 描述中链接
  Converge 报告(由 `/speckit-converge` 产出);缺失 MUST 阻断合并。
- **例外**:纯文档、纯配置变更(如 CI 脚本、依赖升级)不需要走 Converge,
  但 MUST 由 Owner 标注 `Type: docs/config` 并通过常规 PR 评审。
- **回退**:已 Converged 的 feature 若发现缺陷,走 `hotfix/*` 修复并补开
  Converge 报告。
- **理由**:多团队并行迭代若无强收敛门禁,会出现"看起来做完了但实际未对齐"
  的隐性技术债;Converge-Gate 让 feature 在合并前就被强制走完 Speckit
  全流程,把模糊性浪费前置到 PR 阶段。

### V. One-Feature-Owner（特性单一 Owner）
**规则**:每个特性有且仅有一个 **Owner**(负责人)。

**细则**:
- **Owner 职责**:
  1. 业务决策权:对 spec、plan、tasks 中的业务取舍负最终责任。
  2. 跨团队沟通:代表本 feature 与其他团队对接,参与 RFC 与 Code Review。
  3. 交付责任:负责 Converge 报告完整产出与归档。
  4. 事后复盘:feature 上线后 30 天内组织复盘,归档到 `docs/postmortem/`。
- **唯一性**:同一时间每个 feature MUST 只有一个主 Owner;
  协作者以 `Co-Owner` 标注,但不承担决策与责任。
- **Owner 任命**:feature 创建时 MUST 在 spec 文档中显式声明 `Owner: <name>`;
  缺失 Owner 的 spec 不予 Converge。
- **Owner 变更**:Owner 变更 MUST 走 RFC,原 Owner 与新 Owner 双签确认,
  并在 spec 与 Converge 报告中同步更新。
- **理由**:多团队协作若无明确 Owner,会出现"多人负责 = 无人负责"的
  责任逃逸;One-Feature-Owner 把责任显式落到个人,降低协调成本与决策延迟。

### VI. API Contract 优先（API 契约优先）
**规则**:所有内部/外部接口 MUST 用 OpenAPI 描述并通过 Pact 契约测试;
不允许在 Controller 里硬编码业务规则。

**细则**:
- 所有 HTTP 接口 MUST 提交 OpenAPI 3.0+ 描述文件,与代码同仓库同分支。
- 跨服务/跨团队接口 MUST 通过 Pact(消费者驱动)双向锁定;契约变更 MUST
  先与消费者团队沟通并形成 RFC。
- 业务规则(权限校验、字段映射、状态机迁移) MUST 落在 Service 层或领域层,
  Controller 只承担协议转换与参数装配。
- 契约破坏性变更(Major) MUST 走版本号(URL Path 或 Header),不得默默替换。
- **理由**:Deep Research Agent 涉及检索、增强、推理、生成等多个子服务,
  没有契约锁定会导致联调成本爆炸,3 个团队的并行迭代无法收敛。

### VII. 可观测性默认（Observability by Default）
**规则**:所有服务 MUST 输出结构化日志、暴露 Prometheus 指标、关键路径打 Trace。

**细则**:
- 日志 MUST 结构化(JSON),必须字段:`ts`(UTC)、`level`、`service`、`trace_id`、
  `actor`、`event`、`latency_ms`、`error`。
- 所有服务 MUST 暴露 `/metrics` Prometheus 端点;核心业务计数器/直方图
  MUST 在 PR 评审前定义清楚。
- 关键路径(检索 → 推理 → 生成) MUST 打 OpenTelemetry Trace,
  且 `trace_id` MUST 贯穿日志与指标。
- 缺失可观测性的服务 MUST 在合并前补齐,否则不予发布。
- **理由**:深度研究链路长、单请求成本高,没有可观测性无法定位延迟与失败,
  无法对外提供 SLA 承诺。

### VIII. 简洁优先（Simplicity First）
**规则**:能用模块化单体解决的不要拆微服务;YAGNI;禁止过早抽象。

**细则**:
- 在没有清晰"独立扩展、独立故障域、独立团队"三大需求之一时,优先模块化单体。
- 不为未发生的未来需求设计接口或抽象;YAGNI(You Aren't Gonna Need It)。
- 抽象层级 MUST 由 3 次以上重复使用驱动;过早抽象属于技术债,纳入评审红线。
- 微服务拆分 MUST 配套:独立的 CI/CD、独立的部署预算、独立的值班责任,
  缺一视为过度拆分。
- **理由**:Deep Research Agent 还在快速演进阶段,过早微服务化会让 3 个团队
  的协调成本远大于扩展收益。

## 附加约束（Additional Constraints）

本节定义性能与合规的硬性基线,违反任一条 MUST 在 CI 阶段被拦截。

### Performance Standards（性能基线）
- **P99 延迟 ≤ 300ms**:同步接口 P99 MUST ≤ 300ms(不含外部检索与 LLM 推理)。
- **错误率 ≤ 0.1%**:5 分钟粒度错误率 MUST ≤ 0.1%(4xx 不计入,5xx 计入)。
- 性能 MUST 在性能测试流水线中执行,纳入合并门禁;不达标 MUST 阻断发布。
- 关键路径 MUST 单独定义 SLO,登记到可观测性平台。

### Compliance（合规）
- **GDPR**:涉及欧盟自然人数据 MUST 满足数据主体权利(访问、删除、可携带);
  默认开启数据最小化与目的限制。
- **等保 2.0 三级**:满足网络安全等级保护 2.0 第三级要求,
  包括身份鉴别、访问控制、安全审计、边界防护、入侵防范、数据完整性、
  数据保密性、个人信息保护等控制点。
- **数据脱敏规则**:
  - 身份证、手机号、银行卡、邮箱等个人信息 MUST 在日志、指标、审计中脱敏。
  - 脱敏 MUST 在数据进入业务逻辑前完成,严禁事后批量替换。
  - 脱敏规则 MUST 在 `data-classification` 仓库集中维护,跨团队统一。
- 合规变更 MUST 由 Tech Lead Council 过半数批准,变更前必须附带数据流图(DDF)
  与风险评估(PIA)。

## 开发工作流（Development Workflow）

### 分支策略:Git Flow + Trunk-based 混合
- **`main` 分支**:可发布状态;只接受通过 PR 合并,严禁直接 push。
- **`feature/*` 分支**:功能开发,基于 `main` 拉取,完成合入后删除。
- **`release/*` 分支**:发布准备(冻结功能、回归测试、性能验证)。
- **`hotfix/*` 分支**:生产紧急修复,基于 `main` 拉取,合入后同步到 `release/*`。
- 长期分支(Factor / Mavis 等子产品线)使用 Git Flow;
  高频小步合并的工程 → Trunk-based。

### Code Review 强制要求
- 每个 PR MUST 至少有 **1 个跨团队 reviewer**(非作者同团队)批准。
- 涉及核心原则(Security、API Contract、可观测性、Spec-Traceable、
  Converge-Gate、One-Feature-Owner)的 PR MUST 由对应领域负责人批准。
- 涉及宪法修改的 PR MUST 由 Tech Lead Council 过半数批准。
- PR 模板 MUST 包含以下字段:
  - `Spec:` — 引用的 spec ID(由 `/speckit-specify` 产出)。
  - `Owner:` — 本 feature 的 Owner。
  - `Converge:` — Converge 报告链接(由 `/speckit-converge` 产出)。
  - `Tests:` — 测试报告(关键路径覆盖率、契约/集成测试结果)。
  - `Observability:` — 可观测性确认(日志/指标/Trace 字段对齐)。
  - `Security:` — SAST/SCA 扫描结果链接。

### 禁止事项
- **不允许直接 push main**;所有变更 MUST 走 PR 流程。
- **PR 必须引用 Spec ID**(除已声明的 `Type: docs/config` 例外)。
- 跨团队契约变更 MUST 走 RFC 流程并形成书面记录。
- 性能不达标 MUST 阻断发布,不得通过技术债方式延期。
- 审计日志、监控指标、Trace 不允许缺失,缺失视为 P0 缺陷。
- feature 未 Converged MUST 阻断合并。
- 同一 feature 不允许同时存在两个主 Owner。

### 持续集成门禁(CI Gates)
- **Spec ID 引用校验**:缺失 MUST 阻断合并。
- **Converge 报告校验**:feature 分支 MUST 链接有效 Converge 报告;缺失 MUST 阻断合并。
- **Owner 校验**:spec 中 MUST 存在 `Owner:` 字段;缺失 MUST 阻断 Converge。
- **关键路径覆盖率 ≥ 80%**(见原则 III 定义范围)。
- **Pact 契约测试全部通过**(消费者驱动)。
- **SAST / SCA 扫描无高危漏洞**(见原则 I)。
- **性能基准测试**:延迟、错误率满足 Performance Standards。

## Governance

**优先级**:本宪法是项目最高治理约束。任何子条款,须满足以下任一条件才能修改:

### 修订流程
1. **提案**:任何团队成员均可提交修订提案(Issue 或 RFC)。
2. **评审**:提案 MUST 经过 Tech Lead Council 评审,提交 **Sync Impact Report**:
   - 受影响原则与条款列表(原标题 → 新标题,如重命名)
   - 迁移计划(含时间表、回滚方案、影响团队)
   - 风险评估与缓解措施
3. **批准**:修订 MUST 由 **Tech Lead Council 过半数** 批准。
4. **公告**:批准后 MUST 同步公告 3 个团队,并在 `docs/governance/` 归档。
5. **版本号**:
   - **MAJOR**:删除或重新定义原则(向后不兼容)。
   - **MINOR**:新增原则或对既有原则进行实质性扩展。
   - **PATCH**:澄清措辞、修正笔误、非语义性改进。
6. **生效**:修订公告 + 迁移计划确认 + 同步公告三方齐备后生效。

### 合规审查
- 所有 PR / Code Review / 发布流程 MUST 校验本宪法的合规性。
- 复杂度(Microservices、抽象层级、跨团队依赖) MUST 在 PR 中显式说明理由。
- 性能、安全、可观测性、Spec 引用、Converge、Owner 缺失 MUST 在 CI 阶段被拦截,
  不得人工豁免。
- Owner 变更与人工豁免 MUST 走 RFC 流程并形成书面记录。

### 运行时指引
- 详细运行时开发指引参见 `docs/dx/` 与 `reference/validation` 脚本。
- 本宪法修改记录见 `docs/governance/constitution-changelog.md`(由治理流程自动维护)。
- Converge 报告模板见 `/speckit-converge` 输出目录。

---

**Version**: 1.1.0 | **Ratified**: 2026-10-14 | **Last Amended**: 2026-10-14