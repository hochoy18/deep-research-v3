# 可观测性设计（Observability）

本文档定义 deep-research v3 在 Langfuse self-hosted（v4.59.0）中的 trace 字段规范、score 维度、OTel API 接入方式、trace 流转图与告警阈值。所有运行时埋点必须遵循此规范，避免后期改字段导致 trace 关联断裂。

## 1. Trace 字段规范

每个 LangGraph 运行（一次完整研究请求）对应一条 Langfuse **trace**，由 4 个嵌套 **observation**（Planner / Researcher / Writer / Critic）组成。统一字段如下：

| 字段 | 类型 | 来源 | 说明 |
| --- | --- | --- | --- |
| `thread_id` | string | LangGraph `config.thread_id` | 关联 Redis checkpoint，支持断点恢复 |
| `node` | string | observation name | 取值 `planner` / `researcher` / `writer` / `critic` |
| `input` | JSON | observation input | node 入参（query / state snapshot） |
| `output` | JSON | observation output | node 出参（plan / evidence / report / critique） |
| `latency_ms` | int | OTel span duration | 由 OTel 自动采集，单次节点耗时 |
| `tokens` | object | LangChain callback | `{prompt, completion, total}` |
| `tools_called` | string[] | Researcher node | 实际调用的工具名（`web_search` / `milvus_search` / `fetch_page`） |
| `score.*` | float | Critic node + judge | 评估分（见第 2 节） |

## 2. Score 维度

评估分挂在 trace 上，分两类：**自动**（节点结束时写）与 **延迟**（LLM-as-judge 离线计算后回写）。

| 维度 | 写入方 | 取值范围 | 含义 |
| --- | --- | --- | --- |
| `score.factual_accuracy` | Critic 节点 + judge | 0–1 | 报告断言与引用源是否一致 |
| `score.citation_density` | Critic 节点 | 0–1 | `引用数 / 关键事实数` |
| `score.coverage` | Critic 节点 | 0–1 | 计划中子问题被覆盖的比例 |
| `score.latency` | OTel | int(ms) | 端到端总耗时 |
| `score.token_cost` | callback | float(USD) | 累计模型成本，按 task → model 路由单价计 |
| `score.tool_failure_rate` | Researcher 节点 | 0–1 | 失败调用 / 总调用 |

## 3. OTel API 接入（Langfuse Python SDK 5.0.1）

Langfuse 5.x 全面拥抱 OpenTelemetry，统一通过 `langfuse.get_client()` + `@start_as_current_observation` 管理 span。推荐用 decorator 形式包裹每个 agent 节点：

```python
from langfuse import get_client
from langfuse.decorators import start_as_current_observation

langfuse = get_client()

@start_as_current_observation(name="researcher", as_type="span")
def run_researcher(state: ResearchState) -> ResearchState:
    state["evidence"] = web_search(state["plan"], trace_id=langfuse.get_current_trace_id())
    return state
```

启动期需配置环境变量 `LANGFUSE_HOST` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`，由 `docker-compose.yml` 注入；LangChain 回调 `CallbackHandler` 通过 `langfuse.get_client().get_callback_handler()` 取得，自动把模型 `tokens` 写入对应 span。

## 4. Trace 流转图

```
HTTP POST /research (query)
   │
   ▼
[trace: thread_id=T1, user_id=U1]
   │
   ├── [span: planner]       input=query              output=plan.sub_questions
   │       └── [gen: qwen3-max] tokens={p:800,c:200}
   │
   ├── [span: researcher]    input=plan               output=evidence[]
   │       ├── [tool: web_search]      tools_called=["web_search"]
   │       ├── [tool: milvus_search]
   │       └── [tool: fetch_page]
   │
   ├── [span: writer]        input=evidence           output=report.md
   │       └── [gen: gpt-4o]          tokens={p:1200,c:900}
   │
   └── [span: critic]        input=report             output=scores
           └── [gen: o3-mini]         tokens={p:600,c:400}
           score.factual_accuracy=0.87
           score.citation_density=0.65
           score.coverage=0.80
   score.latency=42_300ms
   score.token_cost=0.18
```

## 5. 告警阈值

Langfuse webhook + Alertmanager 双通道，任一触发即推送 Lark：

| 指标 | 阈值 | 评估窗口 |
| --- | --- | --- |
| 失败率（`status=error`） | > 5% | 滚动 15 分钟 |
| p95 端到端延迟 | > 60s | 滚动 1 小时 |
| 单次 token 成本 | > $0.50 | 当次 |
| 当日累计 token 成本 | > $20 | 自然日 |

阈值集中在 `infra/langfuse/alerts.yaml`，禁止在代码里硬编码。

## 6. 落地清单

- [x] `docker-compose.yml` 启动 `langfuse/langfuse:latest` + Postgres backend
- [x] `src/observability/langfuse.py` 封装 `get_client()` 单例
- [x] 每个 node 入口加 `@start_as_current_observation`
- [x] `critic` 节点统一调用 `langfuse.score_current_observation(score.name=..., value=...)`
- [x] Grafana 仪表盘引用 Langfuse Postgres 直查（v4 的 PG 元数据可读）
