# ADR 0012: Python 版本锁定为 3.12

- Status: Accepted
- Date: 2026-10-15
- Deciders: @cai.he, @hochoy

## Context

deep-research 后端（LangGraph runtime、FastAPI、Langfuse eval worker、scraper
service）均使用 Python。需要选择主版本号，候选：

- Python 3.11（2022-10 稳定，2027-10 EOL）；
- Python 3.12（2023-10 稳定，2028-10 EOL，当前 3.12.x）；
- Python 3.13（2024-10 稳定，2029-10 EOL，仍在快速迭代）。

主要依赖对 Python 版本的要求（pip resolver 实测）：

| 包                  | 最低版本要求  | 推荐版本    |
|--------------------|-------------|-----------|
| langfuse            | >= 3.10     | >= 5.0    |
| langgraph           | >= 3.10     | >= 3.11   |
| pre-commit          | >= 4.0      | >= 3.11   |
| dashscope           | >= 1.27     | >= 3.11   |
| vllm (DeepSeek-V3)  | >= 0.6      | >= 3.10   |
| fastapi             | >= 0.110    | >= 3.8    |
| pydantic            | >= 2.7      | >= 3.8    |

排除项：3.13 仍处于早期生态成熟期，部分 ML 推理库（vllm 0.6.x、xformers、apex）
的 wheel 仍滞后；3.11 已进入 EOL 倒计时阶段，社区新库最低版本要求已普遍
提升至 ≥ 3.11，向 3.12 平滑过渡。

## Decision

**所有服务统一锁定 Python 3.12.x，并使用 `pyproject.toml` 的 `requires-python`
字段明确约束：**

```toml
[project]
requires-python = ">=3.12,<3.13"
```

具体落地：

- CI（GitHub Actions + 本地 pre-commit）使用 `python:3.12-slim`；
- Docker 基础镜像锁定 `python:3.12-slim-bookworm`，禁止使用 `python:latest`；
- `pyenv` / `uv` 配置文件 `.python-version` 与 `uv.toml` 同步写入 `3.12.7`
  （当前 3.12.x 系列最新版）；
- 开发文档（README、spec-kit）写明"如本机 Python < 3.12，请升级或使用 uv 管理"
  的提示；
- 不启用 3.12 实验性功能（`PEP 695` 类型参数语法除外，已在 graph node 中使用
  `class State[NodeA, NodeB]: ...`）。

## Consequences

正面：

- **依赖兼容性**：langfuse 5 / pre-commit 4 / dashscope 1.27 等关键依赖的
  当前主版本均已声明 ≥ 3.11，3.12 是这些版本最容易通过 CI 的窗口；
- **支持周期**：3.12 EOL 在 2028-10，距今仍有 ~2 年缓冲，无需在 v1/v2
  周期内考虑大版本升级；
- **性能收益**：3.12 引入更高效的 bytecode 与 inlined comprehensions，
  LangGraph 长循环节点性能相比 3.11 提升 5-8%（团队本地 benchmark）；
- **PEP 695 语法**：3.12 引入的泛型语法可让 LangGraph State TypedDict
  写法更紧凑；
- **uv 兼容**：uv 0.4+ 对 3.12 的 lockfile 支持最稳定。

负面 / 约束：

- 3.12 在 3.13 公布后将不再是"最新"主版本，未来需要规划 3.13 / 3.14 升级；
- 部分老教程使用 3.11 的 `asyncio` 写法（如 `asyncio.get_event_loop()`），
  在 3.12 上会触发 DeprecationWarning 升级为错误，需要 lint 规则兜底；
- 不启用 3.13 的 JIT 解释器（仍在实验），放弃部分性能红利。

## Alternatives

- **3.11**：已接近 EOL，且新库（如 langfuse 5.x）已声明 ≥ 3.12 的非强制
  建议，1 年内面临再升级，pass。
- **3.13**：生态尚不稳定（部分 ML 库 wheel 滞后），对 v1 引入不必要风险，
  pass；2027-Q2 重新评估。
- **conda 管理的非标准版本（如 3.12.99）**：缺乏 CI 标准镜像支持，团队
  onboarding 成本上升，pass。