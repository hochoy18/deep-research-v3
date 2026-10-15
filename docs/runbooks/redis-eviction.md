# Runbook: Redis Checkpoint 被淘汰 (redis-eviction)

- Owner: @cai.he
- Severity: P1（直接影响研究流恢复）
- 上次演练: 2026-10-15
- 相关 ADR: ADR 0010（LangGraph interrupt + checkpointer）

## 概述

LangGraph 1.2.x 使用 Redis（或 Postgres）保存 checkpointer 状态，
支撑 `interrupt()` 的暂停 / 恢复语义。deep-research v1 部署的
Redis 实例配置如下：

- 实例：`redis://redis.internal.hochoy.cn:6379/0`
- 内存上限：`maxmemory 4gb`
- 淘汰策略：`maxmemory-policy allkeys-lru`（**当前配置**，本 ADR 会讨论
  调整为 `noeviction`）
- 持久化：`appendonly yes`，`appendfsync everysec`

`allkeys-lru` 在内存满时会**主动淘汰任意 key**，包括 LangGraph 的 checkpoint
blob 与 blob TTL。一旦发生：

- 用户创建**新 session**（即新 `thread_id`）可能因 Redis SETNX 失败而抛
  `CheckpointerError`；
- 已存在的历史 thread 在 `graph.get_state(config)` 时拿不到对应 blob，
  UI 会显示 "thread not found"。

## 症状

1. **新 session 创建失败**：
   LangGraph runtime 日志出现
   `redis.exceptions.ConnectionError: Error 4 MISCONF Redis is configured
   to have maxmemory limit... or Error 0OOM command not allowed...`，
   错误码 `MISCONF` 或 `OOM`。

2. **历史 thread 无法恢复**：
   用户进入 `/threads/{id}` 路由时，UI 显示 "session lost"，且 Langfuse
   trace 显示 `checkpoint_load=null`。

3. **Redis 监控告警**：

   ```bash
   redis-cli -h redis.internal.hochoy.cn INFO memory | grep -E 'used_memory_human|maxmemory_human'
   # 输出：used_memory_human=3.98G / maxmemory_human=4.00G
   ```

4. **evicted_keys 指标飙升**：

   ```bash
   redis-cli -h redis.internal.hochoy.cn INFO stats | grep evicted_keys
   ```

## 应急步骤

### 短期：扩容 + 改策略

1. **即时扩容**（如果 Redis 是单机 / 非集群）：

   ```bash
   # 修改 redis.conf 中 maxmemory 至 16gb
   sudo sed -i 's/^maxmemory 4gb/maxmemory 16gb/' /etc/redis/redis.conf
   sudo systemctl reload redis
   ```

   或者临时通过 CLI 在线调整（需要 `CONFIG SET` 启用）：

   ```bash
   redis-cli -h redis.internal.hochoy.cn CONFIG SET maxmemory 16gb
   ```

2. **改淘汰策略为 `noeviction`**（关键，避免后续继续丢数据）：

   ```bash
   redis-cli -h redis.internal.hochoy.cn CONFIG SET maxmemory-policy noeviction
   redis-cli -h redis.internal.hochoy.cn CONFIG REWRITE
   ```

   改后若再次达到上限，Redis 直接返回 OOM，但**不会淘汰**已有 checkpoint。

3. **手动修复被淘汰的 thread**（可选）：

   ```bash
   # 通过 LangGraph Python SDK 列出有 Postgres 但无 Redis 的 thread
   python -c "
   from langgraph_sdk import get_client
   import asyncio
   async def main():
       c = get_client(url='http://lg.internal.hochoy.cn:8123')
       threads = await c.threads.search()
       for t in threads['threads']:
           try:
               await c.threads.get_state(thread_id=t['thread_id'])
           except Exception as e:
               print(t['thread_id'], 'LOST', e)
   asyncio.run(main())
   "
   ```

### 长期：归档冷 checkpoint 到 Postgres

避免 Redis 持续承担冷数据：

1. **迁移 checkpoint**（v1.5 计划）：在 LangGraph 的 `PostgresSaver` 中实现
   warm/cold 分层——活跃 thread 留 Redis，超过 7 天未访问的 checkpoint
   从 Redis 移到 Postgres 表 `cold_checkpoints`；

2. **压缩 blob**：启用 `langgraph.checkpoint.compression=zstd`，实测可
   缩小 ~40%；

3. **每日 compaction cron**：每天 02:00 跑 `python -m dr.langgraph.gc --older-than 7d --target postgres`，
   删除 Postgres 中 30 天前且无活跃引用的 checkpoint。

## 恢复步骤

1. 验证 Redis 健康：

   ```bash
   redis-cli -h redis.internal.hochoy.cn PING
   redis-cli -h redis.internal.hochoy.cn INFO memory
   ```

2. 创建测试 session：

   ```bash
   curl -X POST http://lg.internal.hochoy.cn:8123/threads \
     -H 'Content-Type: application/json' \
     -d '{"thread_id":"smoke-test","graph_id":"deep-research"}'
   ```

3. 让 LangGraph 跑一个 dummy node，确认 `graph.invoke` 返回 `__interrupt__`
   或最终 result，且 Redis key 被正确写入（`KEYS langgraph:checkpoint:*`）；

4. **批量补发被影响用户**：从 Postgres `audit_log` 表查出过去 1 小时
   报 `MISCONF` 错误的 thread，发送 Slack DM 通知用户重新发起流程；
   LangGraph 当前对回放失败的策略不友好，告知用户即可。

## 告警触发条件

```yaml
- alert: RedisCheckpointEvicted
  expr: redis_evicted_keys_total > 0
  for: 1m
  labels:
    severity: p1
    runbook: redis-eviction
```

```yaml
- alert: RedisMemoryNearFull
  expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.85
  for: 5m
  labels:
    severity: p2
    runbook: redis-eviction
```

## 长期方案

- 切到 **Redis Cluster + 哨兵**：避免单点内存瓶颈；2026-Q4；
- 评估 **DragonflyDB**：单实例可承载 > 10x Redis 数据集，迁移成本可控；
- 在 LangGraph SDK 上游修复 OOM 错误传播（v0.2 计划）。

## 演练频率

每月演练一次（最近一次 2026-10-15）：故意把 maxmemory 调到 64MB，
触发 LRU 淘汰，验证 runbook 步骤齐全。

## 联系人

- 主线 on-call: @cai.he
- 备线: @hochoy
- 升级路径: 如果新 session 失败 > 30 分钟，提升 P0，召集团队会议，
  考虑切到 PostgresSaver 单后端临时运行。