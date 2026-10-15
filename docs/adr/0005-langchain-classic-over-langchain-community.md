# ADR 0005：使用 langchain-classic 而非 langchain-community

- **Status**：Accepted（2026-07-15）
- **Date**：2026-07-15
- **Deciders**：架构组 @cai.he、@bob

---

## Context

deep-research 使用 LangChain 1.4.6 构建 Agent 与 RAG。LangChain 官方在 2025-10 宣布 `langchain-community` 进入 sunset 状态：

- 1.x 版本后 `langchain-community` 不再接受新功能
- 新拆分的 `langchain-classic`、`langchain-core`、`langchain-text-splitters` 等官方包承担社区集成
- `langchain-community` 仅保留安全补丁至 2026-12
- 第三方集成（loaders、vectorstores、document transformers）迁移到对应官方包或独立社区包

项目当前在 `pyproject.toml` 引入 `langchain-community` 用于：

- WebBaseLoader、PlaywrightURLLoader（抓取）
- 部分自定义 retriever / chain helper

需要决定新代码的依赖策略。

---

## Decision

1. 新代码**禁止**新增 `langchain-community` 依赖
2. 等价集成优先迁移到 **`langchain-classic`**（官方推荐 drop-in 替代）
3. `langchain-classic` 未覆盖的能力（loader、retriever）按以下顺序选择：
   - 官方一等公民包（如 `langchain-milvus`）
   - 独立维护的社区包（评估活跃度后引入）
   - 自写薄封装（最后手段，仅当无可信替代时）
4. 存量 `langchain-community` 用法在 v1.1 之前迁移完毕，迁移工单统一跟踪 issue `MIG-COMM-001`

---

## Consequences

**正面：**

- 与 LangChain 官方路线一致，规避 sunset 包停止维护带来的安全 / 兼容性风险
- `langchain-classic` 提供更稳定的 API surface，升级 LangChain 主版本时改动可控
- 减少 transitive 依赖（`langchain-community` 体积大、传递依赖多）

**负面：**

- 部分 loader（如 `PlaywrightURLLoader`）需自写或换源，短期内增加开发量
- 团队需建立"先查 `langchain-classic`，没有再查官方一等公民包，再考虑自写"的决策习惯
- 迁移期间 `langchain-community` 与 `langchain-classic` 并存，需要清晰边界

---

## Alternatives

### A. 继续使用 langchain-community

- 优点：零迁移成本
- 缺点：sunset 包无新特性、安全补丁窗口短（2026-12 截止）；长期看必迁，晚迁成本更高
- 否决原因：技术债只增不减，且与 LangChain 官方推荐路径冲突

### B. 全面弃用 LangChain，自研 Agent 框架

- 优点：完全掌控依赖
- 缺点：自研 Agent 框架工程量大（tool calling、memory、streaming、RAG 抽象）；团队 3-5 人无法承担
- 否决原因：研发 ROI 过低；LangChain 1.x 已稳定，社区活跃度高

### C. 切换到 LlamaIndex 或其他框架

- 优点：LlamaIndex 在 RAG 场景抽象更直接
- 缺点：Agent 与 tool calling 能力不如 LangChain 成熟；项目核心是 deep research agent（多步推理 + 工具调用），不是纯 RAG
- 否决原因：与项目核心场景（Agent）匹配度低于 LangChain

---

## Notes

- 迁移 checklist 见 `docs/runbooks/migrate-langchain-community.md`
- 新引入依赖需在 PR 中说明是否经过 `langchain-classic` 评估，由架构组 review
