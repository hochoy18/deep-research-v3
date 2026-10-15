# 部署指南 (Deployment Guide)

> 适用范围：deep-research v1（单机 docker-compose），v2（K8s）规划占位。

---

## 1. 环境要求

| 项目 | 最低 | 推荐 |
|------|------|------|
| CPU | 8 核 | ≥ 16 核（Milvus + Embedding 推理需大量 SIMD） |
| 内存 | 16 GB | ≥ 32 GB（LangGraph 并发节点 + 浏览器抓取容器） |
| 磁盘 | 50 GB SSD | ≥ 100 GB NVMe SSD（向量索引 + MinIO 对象存储） |
| OS | Linux / macOS / WSL2 | Ubuntu 22.04 LTS |
| Docker | 24.0+ | 26.x |
| Docker Compose v2 | 2.20+ | 内置 |
| uv | 0.4+ | 用于本地 Backend 调试 |
| pnpm | 9+ | 用于本地 Frontend 调试 |

> 注意：Mac Apple Silicon 需勾选 `experimental: true`（Rosetta 转译 Milvus 镜像内部分库），否则启动会报 `Illegal instruction`。

---

## 2. 端口分配

| 服务 | 容器内端口 | 宿主机端口 | 备注 |
|------|----------|----------|------|
| Frontend (Next.js) | 3000 | 3000 | 仅本地/CI preview |
| Backend (FastAPI) | 8000 | 8000 | `/docs` Swagger UI |
| Postgres | 5432 | 5432 | 主数据 |
| Redis | 6379 | 6379 | 缓存 / Celery broker |
| Langfuse Web | 3000 | 3100 | 与 Frontend 错开 |
| Langfuse API | 3001 | 3101 | OTel receiver |
| Milvus Standalone | 19530 | 19530 | gRPC |
| Milvus etcd | 2379 | 2379 | 内部 |
| Milvus MinIO | 9000 | 9000 | 内部 |
| MinIO (业务) | 9000 / 9001 | 9100 / 9101 | 抓取产物 / 报告附件 |
| OTLP Collector | 4317 / 4318 | 4317 / 4318 | 可选，统一 trace 上报 |

> CI preview 环境使用 `docker-compose.preview.yml`，把 3000 / 8000 映射到 PR 编号 + 10000（避免并发 PR 冲突）。

---

## 3. 首次启动顺序

仓库根目录提供 `Taskfile.yml`（兼容 `make`），常用任务：

```bash
task deps          # 复制 .env.example -> .env，生成随机密码到 .env.local
task pull          # docker compose pull 镜像
task up            # docker compose up -d
task wait-healthy  # 轮询 /healthz 直到 Postgres / Redis / Milvus / Langfuse 全部 healthy
task migrate       # alembic upgrade head
task seed          # 写入 Langfuse project + 默认 admin
task open          # 浏览器打开 http://localhost:3000
```

`make` 是 `Taskfile.yml` 的软链接别名，仅为兼容老习惯；新命令优先用 `task`。

**冷启动顺序（按依赖拓扑）：**

1. `postgres`（被 Langfuse / Backend 依赖）
2. `redis`
3. `minio-init`（一次性创建桶 + 访问密钥）
4. `milvus-standalone` + 内部 etcd / minio
5. `langfuse-web` + `langfuse-worker`
6. `backend`（运行 `alembic upgrade head` + uvicorn）
7. `frontend`（`next start`）

任何一步失败 `task up` 不会继续，需要先 `task logs <service>` 排查。

---

## 4. CI 预览环境（PR 预发）

`.github/workflows/preview.yml` 在 PR 打开 / 同步时触发：

- checkout → build backend & frontend 镜像（多阶段，缓存层）
- `docker compose -f docker-compose.preview.yml up -d`
- 端口映射 `10000 + PR_NUMBER`（如 PR #42 → 30042 / 80042）
- 运行 `pytest -m integration` + Playwright smoke
- 评论里贴上 URL：`https://pr-42.preview.deep-research.local`

预览环境与生产同源同镜像，仅替换 `DATABASE_URL` / `LANGFUSE_HOST` 到独立命名空间；用完销毁，不保留数据。

---

## 5. 故障切换（Failover）

v1 阶段服务全部 docker-compose 单实例，**无自动 failover**，故障切换指人工流程：

| 故障 | 切换动作 |
|------|---------|
| Backend OOM | `task restart backend`，若仍 OOM 检查 `MEM_LIMIT=4g` 是否生效 |
| Postgres 损坏 | `task backup:restore` 从 `pg_dump` 最近一次全量恢复 |
| Milvus 索引丢失 | 重新跑 `python -m research_backend.scripts.reindex` |
| Langfuse 不可用 | 业务降级：Backend 自动切换为本地 `OTLP -> stdout` exporter，trace 仍记录 |
| MinIO 桶损坏 | `mc mirror` 从异地备份桶恢复 |

每次切换在 `#incident` 频道开 issue，附 `task logs` 输出和 `task doctor` 报告。

---

## 6. 回滚流程

镜像标签规范：`{git_short_sha}-{build_timestamp}`，CI 推送到 GHCR。

```bash
# 1. 查看上一次成功的 deploy
task deploy:history

# 2. 回滚 backend 到上一个镜像
task rollback backend v0.3.2-1700000000

# 3. 回滚 frontend（前端可独立回滚）
task rollback frontend v0.3.1-1699990000

# 4. 验证 /healthz 与 smoke 测试
task smoke
```

数据库迁移不回滚；破坏性变更必须前向兼容（expand / contract 模式），参见 ADR 0008。

---

## 7. v2 K8s 路线图

v1 验证完成、用户量上来后迁移到 K8s。占位文件：`deploy/helm/deep-research/`。

规划：

- namespace：`deep-research-{env}`（dev / staging / prod）
- Helm chart 包内含 backend / frontend / worker（v2 拆分 Celery）
- Postgres → CloudNativePG Operator
- Redis → Redis Operator
- Milvus → Milvus Operator（standalone → cluster）
- MinIO → 对象存储 / S3 兼容
- ArgoCD GitOps 同步 `infra/prod/kustomization.yaml`
- HPA：backend CPU > 60% 触发扩容；Milvus 单独 autoscaler

> v1 阶段不要在 K8s 上投入精力，先把单图跑稳。

---

## 8. 日常运维命令

```bash
task ps            # 容器状态
task logs backend  # 跟踪 backend 日志
task shell backend # 进入 backend 容器
task doctor        # 跑全套自检（端口 / 磁盘 / 内存 / 证书）
task backup        # pg_dump + MinIO snapshot 到 ./backups/
task prune         # 清理 dangling 镜像 + 旧备份（保留 7 天）
```
