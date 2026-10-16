# research_backend (M1 STUB)

> **Main Owner: Dev.cai.2 (US-2 backend). pyproject.toml/Dockerfile 由 Dev.cai.1 拥有 (T002/T013)**

极简回显后端骨架；M1 阶段仅 echo 单节点，不接真实 LLM。

## 路径分工

| Owner | 路径 |
|---|---|
| Dev.cai.1 | `pyproject.toml`, `Dockerfile`, `app/main.py`, `app/config.py`, `app/api/deps.py`, `app/observability/logging.py` |
| Dev.cai.2 | `app/db/`, `app/api/{schemas.py,routes.py}`, `app/agents/`, `app/graph/`, `app/observability/langfuse.py` |
| Dev.cai.4 | `app/auth/`, `app/ratelimit/`, dev deps |

## 本地跑

```bash
# 1) 安装依赖
uv sync --extra dev

# 2) 跑测试
uv run pytest
```
