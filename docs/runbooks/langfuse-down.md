# Runbook: Langfuse 服务不可用 (langfuse-down)

- Owner: @cai.he
- Severity: P2（影响可观测性，不影响核心研究流）
- 上次演练: 2026-10-15
- 相关 ADR: ADR 0011（multi-model routing）、ADR 0010（LangGraph interrupt）

## 概述

Langfuse 在 deep-research 中承担两个角色：

1. **Trace 上报**：接收 LangGraph runtime、FastAPI、scraper service 的 OpenTelemetry
   span；
2. **LLM-as-judge eval**：异步消费 Langfuse 上的 trace 数据，调用 GPT-4o 作为
   judge 评估每个 node 的输出质量，写回 Langfuse dataset。

Langfuse 自托管在 `lf.internal.hochoy.cn:3000`，Postgres + ClickHouse 后端。
Langfuse 服务不可用时，**研究流本身不会中断**——Langfuse 是旁路 observer，
不参与业务链路决策。

## 影响评估

| 依赖                | 影响 | 说明 |
|---------------------|------|------|
| LangGraph 研究流     | 无   | 图执行靠 checkpointer（Postgres）恢复，不依赖 Langfuse |
| FastAPI 主服务        | 降级  | OTLP exporter 写失败时抛 warning 但不影响 HTTP 响应 |
| LLM-as-judge eval    | 中断 | 无法访问 Langfuse API 拉取 / 写回 trace |
| Langfuse Dashboard UI | 无   | 用户无法查看实时 trace，但可通过 LangGraph `stderr` 日志查 |

确认 Langfuse down 的快速命令：

```bash
curl -fsS http://lf.internal.hochoy.cn:3000/api/public/health
# 期望: {"status":"ok","version":"3.x.x"}
# 失败: curl timeout / 502 / 503
```

## 告警触发条件

Prometheus 规则 `langfuse-down.yml`：

```yaml
- alert: LangfuseUnreachable
  expr: probe_http_status_code{instance="lf.internal.hochoy.cn",job="blackbox"} != 200
  for: 2m
  labels:
    severity: p2
    runbook: langfuse-down
  annotations:
    summary: "Langfuse 探活失败 (instance {{ $labels.instance }})"
```

辅助告警：FastAPI 应用日志中出现连续 > 50 条 OTLP exporter `StatusCode.UNAVAILABLE`
时，触发 P3 通知。

## 应急降级步骤

1. **暂停 trace 上报**：在所有服务环境变量中设置
   `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317`（指向 noop collector），
   或更简单地通过 feature flag `otel.enabled=false` 在 Langfuse SDK 中关闭
   exporter（推荐）；

2. **切换 trace 到本地日志**：临时开启 LangGraph 自带的 `langgraph logs` JSON
   sink，命令：

   ```bash
   docker compose -f compose.langgraph.yaml logs -f > /var/log/dr/langgraph-$(date +%Y%m%d).jsonl
   ```

   这样可在事后把 JSONL 批量导入 Langfuse（`langfuse ingest` CLI）。

4. **暂停 LLM-as-judge eval worker**：

   ```bash
   docker compose stop langfuse-judge-worker
   ```

   worker 进程会将 in-flight 任务写回本地 queue（`/var/spool/dr/judge/`），
   待 Langfuse 恢复后自动重放。

5. **通知团队**：在 Slack `# langfuse-alerts` 频道贴上 dashboard 截图 +
   `severity=P2`、`runbook=langfuse-down`。

## 恢复步骤

1. 验证 Langfuse 健康：

   ```bash
   curl -fsS http://lf.internal.hochoy.cn:3000/api/public/health
   ```

2. 重启 judge worker：

   ```bash
   docker compose start langfuse-judge-worker
   docker compose logs -f langfuse-judge-worker | grep -E 'replayed|backfill'
   ```

   worker 启动后会从 `/var/spool/dr/judge/` 目录 replay backlog，
   正常情况下 30 分钟内追上。

3. 重新开启 OTLP exporter：撤销 `otel.enabled=false` flag，重启服务，
   验证新 trace 立即出现在 Langfuse dashboard（≤ 1 分钟）；

5. **回填历史 trace（可选）**：如有 LangGraph JSONL 日志需补传：

   ```bash
   cat /var/log/dr/langgraph-20261015.jsonl | langfuse ingest --project deep-research
   ```

6. 关闭 Slack 通知，更新 status page（如果使用）。

## 长期方案

- **HA 部署**：将 Langfuse 切到 2-replica + Cloudflare LB，并配置 ClickHouse
  replicated 引擎；2026-Q4 完成；
- **Buffer + retry**：OTLP exporter 切到 SQS-style 本地 disk queue（`otelcol`
  的 `file_storage`），避免 exporter 失败丢 trace；
- **Fallback Prometheus 指标**：所有关键 span 的计数器（`langgraph.node.duration`、
  `llm.tokens.total`）本地双写 Prometheus，Langfuse down 时仍可观测。

## 演练频率

每季度演练一次（最近一次 2026-10-15），模拟 Langfuse pod 重启，
验证降级开关与恢复链路通畅。

## 联系人

- 主线 on-call: @cai.he
- 备线: @hochoy
- 升级路径: 如果 P2 超 4 小时未恢复，提升为 P1，召集团队 review 是否切回
  Langfuse SaaS 试用环境作为临时备份。