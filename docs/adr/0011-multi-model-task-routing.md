# ADR 0011: 按任务类型路由 LLM（Multi-model Routing by Task Type）

- Status: Accepted
- Date: 2026-10-15
- Deciders: @cai.he, @hochoy

## Context

deep-research 需要在多个节点调用 LLM，每个节点对 LLM 的能力诉求不同：

| 节点             | 关键能力              | 延迟容忍 |
|----------------|---------------------|---------|
| Clarify 生成澄清问题 | 指令遵循 + 短文本生成   | < 2s    |
| Topic List 规划    | 长程推理 + 结构化输出 | < 8s    |
| Search Query 生成  | 关键词提取 + 创造性   | < 3s    |
| Web 抓取内容摘要    | 长上下文 + 压缩能力   | < 6s    |
| 最终报告撰写       | 长文写作 + 引用合规   | < 30s   |
| LLM-as-judge 评测  | 评估对齐 + 一致性    | < 5s    |

可选模型与成本（2026-Q4 数据，每百万 token）：

- GPT-4o：输入 $2.5 / 输出 $10，擅长结构化 + 工具调用；
- o3-mini：输入 $1.1 / 输出 $4.4，擅长推理 + 数学；
- Qwen3-Max（阿里云百炼）：输入 ¥8 / 输出 ¥24，中文语境最优；
- DeepSeek-V3（自部署 via vLLM）：输入 ¥2 / 输出 ¥8，超高性价比 + 128k 窗口；
- GLM-4.6（智谱）：输入 ¥5 / 输出 ¥18，中文 + 长文档均衡。

需要在四个候选方案中选一个：

### 方案 E1: 单模型全用 GPT-4o

统一调用，所有节点享受 OpenAI 生态成熟度。

### 方案 E2: 主备（GPT-4o 主，其余备用）

GPT-4o 失败时降级到其他模型；其余节点不切分。

### 方案 E3: 按任务类型路由（本节点）

每个节点通过 `model_router.resolve(node_name, payload)` 选模型。

### 方案 E4: 随机采样 + 在线评估

每个请求随机选模型，用 Langfuse 收集质量指标，自动偏好流量。

## Decision

**采用方案 E3：按任务类型路由。** 路由表由 `config/model_router.yaml` 声明：

```yaml
nodes:
  clarify:                  { primary: qwen3-max,    fallback: gpt-4o }
  topic_planner:            { primary: o3-mini,      fallback: gpt-4o }
  search_query:             { primary: qwen3-max,    fallback: deepseek-v3 }
  scrape_summarize:         { primary: deepseek-v3,  fallback: qwen3-max }
  report_write:             { primary: qwen3-max,    fallback: gpt-4o }
  llm_judge:                { primary: gpt-4o,       fallback: glm-4.6 }
```

约束：

- 路由函数对调用方透明：`get_chat_model(node_name) -> BaseChatModel`；
- Fallback 模型仅在 primary 5xx / 429 触发，不在低质量场景触发；
- 路由决策写入 Langfuse span attribute `model.routed_to` 与
  `model.fallback_triggered`，便于离线统计；
- 模型升级时仅改 yaml，无需改图节点代码。

## Consequences

正面：

- **成本最优**：长上下文节点（scrape_summarize、report_write）走 DeepSeek-V3
  与 Qwen3-Max，相比全 GPT-4o 降低 ~60% token 成本；
- **性能最优**：推理节点（topic_planner）走 o3-mini，比 GPT-4o 在结构化
  规划上更稳（团队内部 benchmark 4 次实验平均胜率 3/4）；
- **能力对齐**：中文语境节点走 Qwen3-Max / GLM-4.6，规避 GPT-4o 在中文长文
  写作出处偶发的语态失真；
- **可演进**：未来新增"代码生成"或"图表生成"节点，仅需加 yaml 一行。

负面 / 约束：

- 跨模型评测需要规范化：Langfuse LLM-as-judge 必须使用同一 judge 模型
  （`gpt-4o`），且所有输出统一走 `usage_tracking.json` 标准化；
- 模型 API key 数量从 1 增加到 5，密钥管理复杂度提升；通过
  `doppler run` + `.env.template` 统一管理；
- 不同模型的 token 计费与限流策略不同，需要 Langfuse dashboard 按
  `model.routed_to` 切片做成本归因；
- 单模型故障的 fallback 链路需 E2E 测试覆盖（`tests/e2e/routing/`）。

补充技术债：

- 暂无在线自动偏好（方案 E4），但保留 Langfuse trace 数据，半年后回看
  是否有必要切换为 E4；详见 ADR 0014（未来扩展）。