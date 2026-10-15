# ADR 0006：Langfuse Python SDK v5 统一使用 OTel API

- **Status**：Accepted（2026-07-15）
- **Date**：2026-07-15
- **Deciders**：架构组 @cai.he、@bob

---

## Context

Langfuse Python SDK v3 / v4 提供了独立的 trace / span / generation API：

```python
from langfuse import Langfuse
client = Langfuse()
trace = client.trace(name="research")
span = trace.span(name="retrieve")
generation = span.generation(name="llm", model="gpt-4o")
```

v5（2026-Q2 发布）全面拥抱 **OpenTelemetry**，SDK 内部改为 OTel-based 实现：

- 旧的 `trace` / `span` / `generation` / `score` 方法标记为 **deprecated**
- 新 API：`langfuse.get_client()` + `start_as_current_observation`（as_current_span / as_current_generation）
- 底层走 OTLP exporter，可与项目内其他 OTel 信号（log、metric）统一管线
- 与 `traceloop` / `opentelemetry-instrumentation-langchain` 等生态互操作

项目当前 Backend 仍按 v3 风格调用 Langfuse；需要升级到 v5 并对齐 OTel 语义。

---

## Decision

1. 升级 `langfuse` Python SDK 到 v5.x
2. 全仓统一使用 OTel 风格 API：

```python
from langfuse import get_client
langfuse = get_client()

with langfuse.start_as_current_observation(as_type="span", name="retrieve") as span:
    span.update(input=query)
    with langfuse.start_as_current_observation(
        as_type="generation", name="llm", model="gpt-4o"
    ) as gen:
        gen.update(output=response, usage_details=usage)
        span.update(output=summary)
```

3. 禁止使用已 deprecated 的 `client.trace()` / `trace.span()` / `span.generation()`
4. 同一进程通过 `OTEL_EXPORTER_OTLP_ENDPOINT` 统一上报，trace / log / metric 共用 collector
5. 升级时同步启用 `opentelemetry-instrumentation-langchain`，自动捕获 LangChain 内部 span

---

## Consequences

**正面：**

- 与项目 OTel 战略一致（已统一 trace + log + metric 到 OTLP）
- Langfuse v5 SDK 性能优于 v3（批量上报、async pipeline）
- 自动捕获 LangChain 内部节点，代码量下降 30%+
- 与未来替换 Langfuse 为其他 OTel-compatible 后端（如 Phoenix、Arize）解耦

**负面：**

- 升级需重写现有观测代码（约 15 个调用点）
- 团队需熟悉 OTel `Context`、`traceparent` 等概念
- `instrumentation-langchain` 自动生成的 span name 可能与业务命名不一致，需要手动覆写

---

## Alternatives

### A. 继续使用 v3/v4 风格 API

- 优点：零改动
- 缺点：v5 deprecated 路径将于 2027-Q1 移除；不升级将卡死升级链
- 否决原因：技术债累积，必升

### B. 弃用 Langfuse，自接 OTLP 到自建后端

- 优点：完全自主可控
- 缺点：自建 trace 后端成本高（ClickHouse + 元数据 + UI）；v1 单用户不值得
- 否决原因：项目阶段过早自建

### C. 切换到 LangSmith

- 优点：与 LangChain 生态深度集成
- 缺点：vendor lock-in；vendor 替换成本与 Langfuse 同级；定价模型不友好
- 否决原因：与 Langfuse 收益相近，但 OTel 兼容性 Langfuse v5 更优

---

## Notes

- 升级 PR 分两步：先升级 SDK 不改调用（兼容层），再批量替换为 OTel API
- 关键 span / generation 命名规范见 `docs/runbooks/observability-naming.md`
- nightly e2e 通过 Langfuse trace 比对断言行为不退化
