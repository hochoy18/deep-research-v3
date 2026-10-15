# Data Model: FEATURE-001-m1-infra

> **Phase 1 Output** — `/speckit-plan` 阶段产出。
> 详细定义 spec.md 中 5 个 Key Entity 的字段、关系、生命周期、验证规则。
> M1 阶段仅使用 Postgres（thread + message）+ Redis（限流 + checkpoint）+ Langfuse（trace）。Milvus / MinIO M2+ 引入。

---

## 实体关系图（ER）

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│   User   │ 1     N │  Thread  │ 1     N │ Message  │
│ (匿名)   │─────────│  会话    │─────────│  消息    │
│ UUID v4  │         │ UUID v4  │         │ UUID v4  │
└──────────┘         └──────────┘         └──────────┘
      │                                          │
      │ 1                                      1 │
      │                                          │
      │ N                                        │
┌──────────┐                               ┌──────────┐
│  Trace   │                               │  Trace   │
│ Langfuse │                               │ Langfuse │
└──────────┘                               └──────────┘
   (User 维度)                            (Message 维度)
```

> 实际 Langfuse trace 与 Thread 是 1:1 关系（一次对话请求 = 一条 trace），此处为简化展示。

---

## 实体 1: User（匿名用户）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `user_id` | UUID v4 (string, 36 chars) | ✅ | 主键；后端首次访问时生成 |
| `created_at` | timestamp with timezone | ✅ | 首次访问时间 (UTC) |
| `last_seen_at` | timestamp with timezone | ✅ | 最近一次请求时间（30 天滑窗用） |
| `ip_hash` | string(64) | ❌ | IP SHA256，仅用于限流（不存明文 IP，合规） |

### 生命周期

- **创建**: 首次访问，无 `user_id` cookie → 后端生成 UUID v4，写 cookie
- **存活**: 30 天无访问则 cookie 过期，下次访问视为新 user
- **删除**: M1 阶段不主动删除（constitution 数据保留 ≥ 7 天，30 天 cookie TTL 自然清理）

### 验证规则

- `user_id` MUST 是合法 UUID v4（regex: `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`）
- `ip_hash` MUST 是 SHA256 hex string (64 chars)

### 存储位置

- **不在 Postgres 持久化**（M1 简化）：仅 Redis 存 `user_id → {created_at, last_seen_at, ip_hash}`，TTL 30 天
- 理由: M1 阶段 User 不需要跨服务查询，Redis 足够；M2+ 鉴权时再迁 Postgres

---

## 实体 2: Thread（会话线程）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `thread_id` | UUID v4 (string, 36 chars) | ✅ | 主键；后端创建 thread 时生成 |
| `user_id` | UUID v4 | ✅ | 外键 → User（逻辑外键，不做 FK 约束） |
| `title` | string(200) | ❌ | 默认 "新对话"；M1 阶段不实现自动命名 |
| `status` | enum | ✅ | `active` / `archived`（M1 阶段只用 active） |
| `created_at` | timestamp with timezone | ✅ | 创建时间 (UTC) |
| `updated_at` | timestamp with timezone | ✅ | 最后消息时间 (UTC) |
| `langgraph_thread_id` | string(36) | ❌ | LangGraph checkpoint key（与 thread_id 相同或派生） |

### 生命周期

- **创建**: 用户首次发起对话 → POST `/threads` → 后端生成 thread_id，返回给前端
- **存活**: 30 天无更新 → 自动归档（M1 阶段可暂时不实现自动归档）
- **删除**: M1 阶段不实现软删 / 硬删（constitution 数据保留）

### 验证规则

- `user_id` MUST 匹配当前请求的 cookie user_id（防越权读）
- `title` 长度 ≤ 200
- `status` MUST ∈ {`active`, `archived`}

### Postgres Schema

```sql
CREATE TABLE threads (
    thread_id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(200) DEFAULT '新对话',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    langgraph_thread_id UUID
);

CREATE INDEX idx_threads_user_id ON threads (user_id, updated_at DESC);
CREATE INDEX idx_threads_status ON threads (status) WHERE status = 'active';
```

---

## 实体 3: Message（消息）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `message_id` | UUID v4 | ✅ | 主键 |
| `thread_id` | UUID v4 | ✅ | 外键 → Thread |
| `role` | enum | ✅ | `user` / `assistant` / `system` |
| `content` | text | ✅ | 消息内容（Markdown） |
| `status` | enum | ✅ | `streaming` / `complete` / `failed` |
| `created_at` | timestamp with timezone | ✅ | 创建时间 (UTC) |
| `completed_at` | timestamp with timezone | ❌ | 完成时间（status=complete 时填） |

### 生命周期

- **创建**: 用户提交 query → POST `/threads/{thread_id}/messages` → role=user, status=streaming
- **追加**: 后端流式推送时 → 内部创建 role=assistant, status=streaming
- **完成**: 流式完成 → status=complete, completed_at=NOW()
- **失败**: 流式中断 / LLM 错误 → status=failed

### 验证规则

- `role` MUST ∈ {`user`, `assistant`, `system`}
- `status` MUST ∈ {`streaming`, `complete`, `failed`}
- `content` 长度 ≤ 100,000 字符（防 DoS）
- `content` MUST 经过白名单校验（constitution I）：M1 阶段限制 ASCII + 常见中日韩字符，禁控制字符（除换行）

### Postgres Schema

```sql
CREATE TABLE messages (
    message_id UUID PRIMARY KEY,
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'streaming',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_messages_thread_id ON messages (thread_id, created_at ASC);
```

---

## 实体 4: Trace（追踪）

> Trace 不存 Postgres；由 Langfuse 持久化。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `trace_id` | UUID v4 | ✅ | Langfuse trace ID |
| `thread_id` | UUID v4 | ✅ | 关联 Thread |
| `user_id` | UUID v4 | ✅ | 关联 User |
| `node_name` | string | ✅ | M1 阶段固定为 `echo_agent` |
| `input` | JSON | ✅ | 入参：用户 query |
| `output` | JSON | ✅ | 出参：mock 流式切片（数组） |
| `latency_ms` | int | ✅ | 单次节点耗时（OTel 自动） |
| `started_at` | timestamp with timezone | ✅ | 开始时间 (UTC) |
| `ended_at` | timestamp with timezone | ✅ | 结束时间 (UTC) |

### 生命周期

- **创建**: 每次 POST `/threads/{thread_id}/messages` → `@start_as_current_observation` 创建 trace
- **完成**: 流式推送结束 → observation 结束
- **TTL**: Langfuse self-hosted 默认保留 30 天（与 thread TTL 一致）

### 字段规范（observability.md §1）

```
trace_id        = thread_id（复用，便于关联）
node_name       = "echo_agent"
input           = { query: string }
output          = { chunks: string[] }
latency_ms      = OTel span duration
```

---

## 实体 5: Service（本地服务）

> 非持久化实体；仅用于 docker-compose 配置描述。

| 服务 | 镜像 | 端口 | 数据卷 |
|---|---|---|---|
| `postgres` | postgres:16 | 5432 | `postgres_data:/var/lib/postgresql/data` |
| `redis` | redis:8 | 6379 | `redis_data:/data` |
| `langfuse-server` | langfuse/langfuse:4.59.0 | 3001 | `langfuse_data:/data` |
| `backend` | 自建（research_backend/Dockerfile） | 8000 | — |
| `frontend` | 自建（research_frontend/Dockerfile） | 3000 | — |

### 启动顺序（依赖关系）

```
postgres ─┐
redis ────┼─→ backend ─→ frontend
langfuse ─┘
```

### 健康检查

每个服务 MUST 暴露 `/health` 或等价探针；`task dev:up` 等所有 health 通过后才视为启动完成。

---

## 实体间约束

| 约束 | 规则 | 实现 |
|---|---|---|
| Thread 越权读防护 | `thread.user_id == cookie.user_id` | 后端中间件校验 |
| Message 越权读防护 | `message.thread.user_id == cookie.user_id` | 后端 JOIN 校验 |
| 限流粒度 | `(ip_hash, user_id)` 二元组 | Redis `INCR` + `EXPIRE` |
| Thread 唯一性 | `thread_id` 唯一 | Postgres PRIMARY KEY |
| Trace 关联完整性 | `trace.thread_id == 实际 thread` | LangGraph `config.thread_id` 注入 |

---

## M1 → M2+ 演进

| 实体 | M1 状态 | M2+ 演进 |
|---|---|---|
| User | Redis 临时 | 迁 Postgres + 加 `email` / `password_hash` / `role` |
| Thread | 简化字段 | 加 `research_brief` / `sub_tasks` / `status` 扩展 |
| Message | 简化字段 | 加 `citation_ids` / `critique_results` / `score.*` |
| Trace | Langfuse | 加 score.* 维度（factual / citation / coverage） |
| Service | 5 个 | 加 Milvus / MinIO（v2 启动时） |

---

## ADR 引用

- [ADR-0003 postgres-milvus-minio](../../docs/adr/0003-postgres-milvus-minio.md) — M1 阶段 Milvus/MinIO 留白
- [ADR-0006 langfuse-v5-otel-api](../../docs/adr/0006-langfuse-v5-otel-api.md) — trace 协议
- [ADR-0009 v1-no-auth](../../docs/adr/0009-v1-no-auth.md) — User 实体匿名化
- [ADR-0010 hitl-clarify-with-interrupt](../../docs/adr/0010-hitl-clarify-with-interrupt.md) — M2+ Thread 状态扩展
