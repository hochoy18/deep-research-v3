# Runbook: LLM API 触发限流 (llm-ratelimit)

- Owner: @cai.he
- Severity: P1（影响研究流主干）
- 上次演练: 2026-10-15
- 相关 ADR: ADR 0011（multi-model routing）

## 概述

deep-research v1 调用 5 个 LLM 提供商（GPT-4o、o3-mini、Qwen3-Max、
DeepSeek-V3、GLM-4.6）。每个提供商对账号 / 模型 / region 都有独立的
RPM / TPM 配额，触发 429 时表现为：

- HTTP 状态 `429 Too Many Requests`；
- 响应头 `Retry-After: <seconds>` 或 `x-ratelimit-reset-*`；
- 部分提供商（OpenAI、阿里云）会附带详细 `x-ratelimit-remaining-requests`。

我们的策略：

1. **FastAPI middleware + Redis 计数**：在调用 LLM 前对每个 `(model, route)`
   维度做滑动窗口计数，超过阈值则排队（`asyncio.Semaphore`）等待；
2. **自动 retry**：检测到 `429` 时读 `Retry-After` 自动 sleep 后重试
   （指数退避：1s → 2s → 4s → 8s，最多 4 次）；
3. **切备选模型**：连续 retry 仍失败的，`model_router` 切 fallback 节点；
4. **用户告知**：FastAPI 通过 SSE 流式把 `event: rate_limited` 与
   `event: switched_model` 推给前端 UI。

## 症状

1. **单个节点 latency 升高**：
   Langfuse span 显示 `latency > 2 × p95`，且包含 `attempts=2`、`retry_count=1` 字段。

2. **HTTP 5xx 增加**：
   Prometheus `langgraph_node_errors_total{reason="rate_limited"}` 计数
   在 5 分钟窗口内 > 10。

3. **Provider Dashboard 报错**：
   用户（owner）在 OpenAI / 阿里云控制台看到 429 spike。

4. **LangGraph trace 出现 `model.fallback_triggered=true`**：
   Langfuse dashboard 通过 `model.fallback_triggered` 维度过滤可定位。

## 应急步骤

### 短期：扩配额 + 启用备选

1. **扩容 RPM/TPM**：
   - OpenAI：在 dashboard 提工单或在账户设置购买 Tier 3/4；
   - 阿里云百炼：在控制台申请模型扩配；
   - DeepSeek-V3 自部署：通过 K8s HPA 拉起 vLLM worker。

2. **临时切换 primary 模型**：

   ```bash
   # 编辑 config/model_router.yaml，把出问题的 primary 改为 fallback
   vim /etc/dr/model_router.yaml
   # 例：把 qwen3-max 暂时切到 glm-4.6
   python -m dr.model_router.reload
   ```

   进程会监听 SIGHUP，无需重启服务。

3. **限流并发数**：在 FastAPI middleware 临时下调 `LLM_MAX_CONCURRENCY`：

   ```bash
   curl -X POST http://api.internal.hochoy.cn/admin/concurrency \
     -d '{"key":"global","value":4}'
   ```

   默认 16，临时降到 4 可显著降低 RPM。

### 长期：智能调度

1. **预 token 计数**：调用前用 `tiktoken` 或对应 tokenizer 估算 token 数，
   提前发现 TPM 瓶颈；
2. **多账号 round-robin**：OpenAI / 阿里云支持多 API key 配额叠加，
   配置在 `secrets/llm_keys/` 下，调度器自动 round-robin；
3. **LLM-aware cache**：相同 prompt 的检索类调用（如 search query 生成）
   加 Redis-backed LRU cache，TTL 5 分钟，可降低 ~25% QPS。

## 恢复步骤

1. 验证 provider 配额已恢复：

   ```bash
   # OpenAI
   curl -i https://api.openai.com/v1/chat/completions \
     -H "Authorization: Bearer $OPENAI_API_KEY" \
     -d '{"model":"gpt-4o","messages":[{"role":"user","content":"ping"}],"max_tokens":1}'
   # 期望：HTTP 200
   ```

2. 检查 Redis 限流计数已清空：

   ```bash
   redis-cli -h redis.internal.hochoy.cn KEYS 'ratelimit:*' | head
   redis-cli -h redis.internal.hochoy.cn --scan --pattern 'ratelimit:*' | xargs -L 100 DEL
   ```

3. 跑端到端冒烟测试：

   ```bash
   pytest tests/e2e/test_research_flow.py -k "smoke" -v
   ```

   期望所有用例在 < 60s 内通过。

4. 切回原 primary 模型：恢复 `model_router.yaml` 的原配置；

6. 通知用户在 Slack `# dr-ops` 频道贴 incident 总结：
   故障模型、起止时间、影响 thread 数、自动切换的 fallback 模型、后续改进项。

## 监控指标

| 指标                              | 阈值                | 触发动作 |
|----------------------------------|---------------------|----------|
| `llm_429_total{model="..."}`       | > 10 / 5min          | P2 通知  |
| `llm_429_total{model="..."}`       | > 100 / 5min         | P1 + 自动降级 |
| `llm_fallback_triggered_total{model="..."}` | > 50 / 1h | P3 通知 + 团队复盘 |
| `llm_latency_p99{model="..."}`     | > 2 × baseline       | P2 通知 |
| `model_router_queue_wait_seconds` | > 30                 | P2 通知 |

Prometheus YAML 片段：

```yaml
- alert: LLMRateLimitSpike
  expr: sum by (model) (rate(llm_429_total[5m])) > 0.033
  for: 5m
  labels:
    severity: p2
    runbook: llm-ratelimit
```

```yaml
- alert: LLMRateLimitCritical
  expr: sum by (model) (rate(llm_429_total[5m])) > 0.33
  for: 3m
  labels:
    severity: p1
    runbook: llm-ratelimit
```

## 用户告知

通过 SSE（Server-Sent Events）实时推送给前端：

```typescript
// 前端 EventSource 监听
source.addEventListener('rate_limited', (e) => {
  toast.warning(`LLM ${e.model} 触发限流，自动切换到 ${e.fallback}`);
});
source.addEventListener('switched_model', (e) => {
  toast.info(`已切换到 ${e.fallback}，功能正常继续`);
});
```

文案：避免使用"故障 / 失败"等措辞，改为"限流 / 自动切换 / 继续中"。

## 长期方案

- **Predictive throttling**：基于 Langfuse 历史 trace 训练每分钟 RPM 预测
  模型，提前 5 分钟降速；2027-Q1 计划；
- **Provider mesh**：把模型路由抽成可插拔 provider，支持临时接入新模型
  （如 Doubao、Claude 4）作为兜底；ADR 0015 占位；
- **Bulkhead 隔离**：每个 provider 一个 asyncio.Semaphore，避免单个
  provider 限流拖垮其他 provider 的调用。

## 演练频率

每季度演练一次（最近一次 2026-10-15）：用 `tc` 网络工具模拟 429
注入，验证 middleware + fallback + 用户告知链路通畅。

## 联系人

- 主线 on-call: @cai.he
- 备线: @hochoy
- 升级路径: 如果 P1 超 30 分钟未恢复，提升 P0，团队会议决定
  是否切回 OpenAI Tier 2 + 临时禁用其他模型。