# Quickstart: FEATURE-001-m1-infra

> **Phase 1 Output** — `/speckit-plan` 阶段产出。
> M1 阶段端到端验证指南：4 条关键路径（spec SC-006）的可重放验证步骤。
> 配套 `data-model.md`（5 个 Key Entity）+ `contracts/openapi.yaml`（API 契约）。

---

## 前置条件

| 依赖 | 版本 | 验证命令 |
|---|---|---|
| Docker Desktop | ≥ 4.25 | `docker --version` |
| Task | ≥ 3.40 | `task --version` |
| Node.js | ≥ 20.x | `node --version`（仅前端开发需要） |
| Python | ≥ 3.12 | `python3.12 --version`（仅后端开发需要） |
| Git | ≥ 2.40 | `git --version` |

---

## 1. 一键启动服务栈（验证 FR-001 / FR-002 / FR-005 / SC-001）

```bash
# 克隆仓库（如未克隆）
git clone <repo-url> && cd deep-research/v3

# 启动所有服务
task dev:up
```

**预期**：

- 5 个服务在 5 分钟内全部启动：postgres / redis / langfuse / backend / frontend
- 后端：`http://localhost:8000/health` 返回 `{"status": "ok"}`
- 前端：`http://localhost:3000` 浏览器打开对话界面
- Langfuse：`http://localhost:3001` 看到 trace 列表

**验证 SC-001**（clone 到看到本地界面 ≤ 5 分钟）：

```bash
START=$(date +%s)
task dev:up > /tmp/devup.log 2>&1
# 等待 backend /health 返回 ok
while ! curl -sf http://localhost:8000/health > /dev/null; do sleep 1; done
END=$(date +%s)
echo "耗时 $((END-START)) 秒"  # 应 ≤ 300
```

**停止**：

```bash
task dev:down
```

---

## 2. 端到端 mock 对话流（验证 FR-006 ~ FR-011 / SC-002 / SC-003 / SC-004）

### 步骤 2.1：浏览器手动验证

1. 打开 `http://localhost:3000`
2. 在输入框输入：「你好，请介绍一下 LangGraph」
3. 提交
4. 预期：对话流中看到 mock 流式响应（每 ~50ms 一个 token 切片，Markdown 渲染）
5. 完整响应时间 ≤ 3 秒（SC-002）
6. 打开 `http://localhost:3001`（Langfuse UI）→ 找到本次请求的 trace
7. 验证 trace 包含：`node_name=echo_agent` / `input={query: "..."}` / `output={chunks: [...]}`（FR-009 / SC-004）

### 步骤 2.2：CLI 验证（SSE 流式接收）

```bash
# 创建 thread
THREAD_ID=$(curl -s -X POST http://localhost:8000/threads \
  -H "Content-Type: application/json" \
  -c /tmp/cookies.txt | jq -r '.thread_id')

echo "Thread: $THREAD_ID"

# 发送 query，捕获 SSE 流
curl -N -X POST "http://localhost:8000/threads/$THREAD_ID/messages" \
  -H "Content-Type: application/json" \
  -b /tmp/cookies.txt \
  -c /tmp/cookies.txt \
  -d '{"content": "Hello World"}'
```

**预期 SSE 输出**：

```
event: message
data: {"message_id":"...","chunk":"Hello","index":0}

event: message
data: {"message_id":"...","chunk":" ","index":1}

event: message
data: {"message_id":"...","chunk":"World","index":2}

event: state_update
data: {"message_id":"...","status":"complete"}

event: done
data: {"message_id":"...","total_chunks":3,"latency_ms":150}
```

### 步骤 2.3：跨刷新恢复（验证 FR-010 / SC-010）

1. 在浏览器发起一次对话（流式响应进行中）
2. 在流式响应进行到一半时按 F5 刷新页面
3. 预期：刷新后从 checkpoint 恢复，已渲染的 token 不丢失，新 token 继续推送

### 步骤 2.4：跨会话重开（验证 FR-011 / SC-010）

1. 完成一次完整对话
2. 关闭浏览器标签
3. 重新打开 `http://localhost:3000`
4. 预期：左侧 thread 列表显示刚才的对话，点击进入看到完整历史

### 步骤 2.5：限流触发（验证 FR-011b / SC-012）

```bash
# 循环触发 11 次
for i in {1..11}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "http://localhost:8000/threads/$THREAD_ID/messages" \
    -H "Content-Type: application/json" \
    -b /tmp/cookies.txt \
    -d "{\"content\": \"test $i\"}")
  echo "请求 $i: HTTP $STATUS"
done
```

**预期**：前 10 次返回 200，第 11 次返回 429 + 错误体含 `retry_after_seconds`。

### 步骤 2.6：跨用户隔离（验证 FR-011a / SC-011）

```bash
# 用户 A 创建 thread
curl -X POST http://localhost:8000/threads \
  -H "Content-Type: application/json" \
  -c /tmp/cookies_A.txt > /tmp/thread_A.json
THREAD_A=$(jq -r '.thread_id' /tmp/thread_A.json)

# 用户 B（无 cookie）尝试读取用户 A 的 thread
curl -X GET "http://localhost:8000/threads/$THREAD_A" \
  -b /tmp/cookies_B.txt
```

**预期**：用户 B 返回 403（thread 不属于当前 user）。

---

## 3. PR 质量门禁（验证 FR-012 ~ FR-016 / SC-005 / SC-006 / SC-008）

### 步骤 3.1：故意失败的 PR

```bash
# 1. 拉分支
git checkout -b test/m1-coverage-fail

# 2. 在 backend/app/main.py 删除关键路径的一行测试
# 例如：删除 test_main.py 中 health 路由的测试用例

# 3. 提交（注意：commit message 不带 spec 引用 → 应被 pre-commit 拦截）
git add .
git commit -m "test: remove health test"
# 预期：pre-commit 失败，提示 spec 引用缺失

# 4. 修正：commit 加 Spec 字段
git commit -m "test: remove health test

Spec: FEATURE-001-m1-infra
Owner: TBD" --no-verify

git push -u origin test/m1-coverage-fail

# 5. 开 PR（GitHub Web UI / gh CLI）
gh pr create --title "test: coverage fail scenario" \
  --body "Spec: FEATURE-001-m1-infra
Owner: TBD
Tests: 故意 < 80%
Security: N/A"
```

**预期**：CI 在 10 分钟内（SC-005）跑完，**关键路径覆盖率 < 80% 阻断合并**（SC-006）。

### 步骤 3.2：合规 PR

```bash
git checkout main
git checkout -b feat/m1-impl-xxx
# 正常实现
git commit -m "feat(backend): add echo agent

Spec: FEATURE-001-m1-infra
Owner: Co-Owner #2"
gh pr create --title "feat(backend): add echo agent" \
  --body "Spec: FEATURE-001-m1-infra
Owner: Co-Owner #2
Tests: pytest 100% pass, coverage 85% on 4 critical paths
Security: bandit clean, pip-audit clean
Converge: <link to /speckit-converge report>"
```

**预期**：CI 全绿，CODEOWNERS 自动路由 reviewer，跨团队 reviewer + 领域 Owner 双签后合入。

---

## 4. 关键路径 4 条覆盖（验证 SC-006）

| 路径 | 验证方式 | 预期 |
|---|---|---|
| 路径 1：query → mock 流式响应全链路 | §2.2 SSE CLI 验证 | 完整 SSE 流，含 4 个 event types |
| 路径 2：thread CRUD + user_id 过滤 | §2.6 跨用户隔离测试 | 用户 B 读 A → 403 |
| 路径 3：cookie 生成 + IP+user_id 限流 | §2.5 限流测试 | 第 11 次请求 → 429 |
| 路径 4：可观测性 trace 写入 | §2.1 Langfuse UI 验证 | trace 含 3 字段（node/input/output） |

**覆盖率报告**：

```bash
cd backend
task backend:test
task backend:coverage
open coverage/index.html  # 浏览器查看 HTML 报告
```

**预期**：4 条关键路径行覆盖 ≥ 80%（constitution III 强制门禁）。

---

## 5. 一键跑测试（验证 FR-017 ~ FR-019）

```bash
# 后端测试
task backend:test

# 前端测试
task frontend:test

# 全部测试 + 覆盖率
task test:all
task test:coverage
```

**预期**：

- 后端：pytest 全绿，覆盖率报告输出到 `backend/coverage/`
- 前端：vitest 全绿，覆盖率报告输出到 `frontend/coverage/`
- 关键路径 4 条 ≥ 80%

---

## 6. 集成日 Demo 脚本（M1 集成日 / SC-009）

```bash
# 1. 全员 merge 所有分支
git checkout main
git pull --rebase

# 2. 启动服务
task dev:up

# 3. 端到端演示
# - 浏览器输入 query
# - SSE 流式响应
# - Langfuse UI 展示 trace
# - 跨刷新不丢内容
# - 限流触发
# - 跨用户隔离

# 4. 录屏 / 截图

# 5. 关闭服务
task dev:down
```

**预期**：1 次跑通；团队对 4 人并行开发体验评分 ≥ 4/5（SC-009）。

---

## 7. 故障排查（参考 runbooks/）

| 故障 | 排查 | 文档 |
|---|---|---|
| Langfuse 不可用 | `docker logs langfuse-server` | [runbooks/langfuse-down.md](../../docs/runbooks/langfuse-down.md) |
| LLM 限流（M2+ 才有） | — | [runbooks/llm-ratelimit.md](../../docs/runbooks/llm-ratelimit.md) |
| Redis 淘汰 | `docker exec redis redis-cli INFO stats` | [runbooks/redis-eviction.md](../../docs/runbooks/redis-eviction.md) |
| 端口冲突 | `lsof -i :8000` / `lsof -i :3000` | spec Edge Cases |
| Tailwind v4 兼容 | `frontend/package.json` 锁定 v4.0.0 | ADR-0007 / milestones §M1 关键风险 |

---

## 8. 验收清单（M1 DoD）

- [ ] §1 启动 ≤ 5 分钟
- [ ] §2 端到端 mock 对话流全跑通
- [ ] §2.5 限流触发（429）
- [ ] §2.6 跨用户隔离（403）
- [ ] §3.1 故意失败 PR 被 CI 阻断
- [ ] §3.2 合规 PR 全绿
- [ ] §4 关键路径 4 条 ≥ 80% 覆盖
- [ ] §5 一键跑测试全绿
- [ ] §6 集成日 demo 1 次跑通
- [ ] `README.md` §M1 状态从「计划中」更新为「M1 ✅ 完成」

---

## 相关文档

- [spec.md](./spec.md) — 完整 spec（含 5 个 Clarifications）
- [data-model.md](./data-model.md) — 5 个 Key Entity 详细 schema
- [contracts/openapi.yaml](./contracts/openapi.yaml) — API 契约
- [research.md](./research.md) — 10 项技术决策
- [docs/runbooks/](../../docs/runbooks/) — 故障排查手册
- [docs/contributing.md](../../docs/contributing.md) — 提交规范 / PR 流程
