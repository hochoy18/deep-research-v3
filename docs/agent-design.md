# Agent 设计（Agent Design）

> 4 个 Agent（Planner / Researcher / Writer / Critic）的设计契约：抽象层、prompt 模板、LLM 路由、输出 schema。LangGraph 节点定义、State schema、HITL interrupt 见 [`graph-design.md`](./graph-design.md)。

---

## 1. 设计原则

1. **共性抽象**：4 个 Agent 的"接 state → 调 LLM → 解析输出 → 返回 state diff"流程高度相似，抽象成 `BaseAgent` 模板方法。
2. **Prompt 集中管理**：所有 system prompt 放在 `app/agents/prompts.py`，便于版本控制和 A/B。
3. **结构化输出优先**：所有 Agent 用 `with_structured_output(PydanticModel)`，避免脆弱的字符串解析。
4. **LLM 路由透明**：每个 Agent 声明 `model_role`（"planner" / "researcher" / "writer" / "critic"），路由层按 role 选具体模型。
5. **HITL 透明**：所有 HITL 触发（`interrupt()`）都在 Agent 内部统一调用，BaseAgent 提供 `await_user_input()` 辅助方法。

## 2. BaseAgent 抽象类

```python
# app/agents/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Any
from langchain_core.messages import BaseMessage
from app.graph.state import AgentState
from app.observability.langfuse import observe

StateT = TypeVar("StateT", bound=AgentState)
OutputT = TypeVar("OutputT")


class BaseAgent(ABC, Generic[StateT, OutputT]):
    """4 个 Agent 的基类。LangGraph node 接口 = __call__(state) -> dict."""

    name: str                                # "planner" / "researcher" / ...
    model_role: str                          # 用于 LLM 路由层查表
    system_prompt: str                       # 从 prompts.py 加载
    output_schema: type[OutputT]             # Pydantic 模型

    def __init__(self, llm_router, tools: List[Any] | None = None):
        self.llm = llm_router.for_role(self.model_role)
        self.tools = tools or []
        self.llm_with_struct = self.llm.with_structured_output(self.output_schema)

    @abstractmethod
    def build_user_prompt(self, state: StateT) -> List[BaseMessage]:
        """从 state 提取上下文 + 渲染 user prompt。子类实现。"""

    @abstractmethod
    async def post_process(self, output: OutputT, state: StateT) -> dict:
        """解析后处理（如更新 plan 状态、写入 sources）。子类实现。"""

    @observe(name="agent.run", as_type="span")
    async def __call__(self, state: StateT) -> dict:
        """LangGraph node 接口：接 state → 调 LLM → 解析 → 返回 state diff。"""
        user_prompt = self.build_user_prompt(state)
        output: OutputT = await self.llm_with_struct.ainvoke(
            [self.system_message()] + user_prompt
        )
        return await self.post_process(output, state)

    def system_message(self) -> BaseMessage:
        from langchain_core.messages import SystemMessage
        return SystemMessage(content=self.system_prompt)
```

要点：
- `__call__` 已经是 LangGraph node 接口（StateGraph 直接接 `Planner(...)` 即可）
- `@observe` 是 Langfuse OTel decorator，自动上报 `agent.run` span
- `model_role` 让 LLM 路由层与 Agent 实现解耦

## 3. 4 个 Agent 详细设计

### 3.1 Planner

**职责**：把 query 拆成结构化子任务列表（带依赖关系），后续 Researcher 按计划执行。

**State 输入**：`{ query, research_brief }`

**输出 schema**（`app/agents/schemas.py`）：

```python
class SubTask(BaseModel):
    id: str                          # 短横线命名，如 "st-1"
    description: str                 # 子任务描述
    depends_on: List[str] = []       # 依赖的其他子任务 id
    search_queries: List[str] = []   # 建议的搜索词
    expected_sources: int = 3        # 期望检索的来源数

class PlanOutput(BaseModel):
    subtasks: List[SubTask]
    reasoning: str                   # 拆分思路（用于 Langfuse trace）
```

**System prompt 草稿**（`app/agents/prompts.py`）：

```
You are a research planner. Given a user query and an optional research brief
(filled after clarification), decompose it into 3-7 concrete sub-tasks.

Rules:
- Each sub-task should be independently searchable (have clear search queries).
- Use `depends_on` to express logical ordering (e.g. "compare A vs B" needs
  researching A and B first).
- 3-7 sub-tasks, no more. Combine related topics.
- Reasoning field should briefly explain your decomposition strategy.
- Output must be valid JSON matching the schema. No markdown fences.
```

**LLM 路由**：`model_role = "planner"` → 默认 `gpt-4o`（fallback: `qwen3-max`）

**Post-process**：把 `subtasks` 写入 `state["plan"]`；初始化每个 sub-task 的 `status="pending"`。

---

### 3.2 Researcher

**职责**：对每个 pending sub-task，执行 `web_search` + `fetch_page` + 摘要；把结果累加到 `state["sources"]`。HITL 触发点：**topic list 审阅**（在 Researcher 启动前）。

**State 输入**：`{ plan, sources, current_subtask_id }`

**输出 schema**：

```python
class SourceItem(BaseModel):
    id: str                              # uuid short
    url: str
    title: str
    excerpt: str                         # 200-500 字摘要
    score: float = Field(ge=0, le=1)     # 相关度
    fetched_at: datetime
    used_in_subtask: str                 # 哪个 sub-task 用到

class ResearcherOutput(BaseModel):
    sources: List[SourceItem]
    next_subtask_id: str | None          # None 表示 plan 全部完成
    needs_more_search: bool = False
```

**System prompt 草稿**：

```
You are a research executor. You will receive one sub-task at a time.
For each sub-task:
1. Use web_search with the suggested queries (or refine if needed).
2. For the top 3-5 results, use fetch_page to get the full content.
3. Write a concise excerpt (200-500 chars) for each.
4. Score relevance 0-1 based on how well it answers the sub-task.
5. Decide if you need more search (return needs_more_search=True) or move on.

Output must be valid JSON. No markdown fences.
```

**LLM 路由**：`model_role = "researcher"` → 默认 `gpt-4o`（fallback: `qwen3-max`）

**Post-process**：
- 把新 `sources` 追加到 `state["sources"]`（去重 by URL）
- 更新当前 sub-task 的 `status` 为 `done`
- 移动 `current_subtask_id` 到下一个 pending；如果都 done 返回 `next_subtask_id=None`
- HITL 触发：当 sub-task 列表生成后、`current_subtask_id` 设置前调用 `await_user_input()` 让用户增删改 topic

**循环控制**：

```python
def should_continue_research(state):
    plan = state["plan"]
    if state.get("current_subtask_id") is None:
        return "writer"          # plan 全部完成
    if state.get("iteration", 0) >= MAX_RESEARCH_ITERATIONS:
        return "writer"          # 兜底，避免无限循环
    return "researcher"
```

---

### 3.3 Writer

**职责**：基于 `plan` + `sources` 生成 Markdown draft；流式输出（每个 token 一个 SSE event）。

**State 输入**：`{ plan, sources, draft, query, research_brief }`

**输出 schema**（注意：writer 用 streaming，所以不强制 structured output，而是用 token stream + 末尾输出 draft 全文）：

```python
class WriterOutput(BaseModel):
    """Writer 末尾输出，用于 Langfuse trace。中间是 token stream。"""
    final_draft: str
    word_count: int
    citation_count: int
```

**System prompt 草稿**：

```
You are a research writer. Write a Markdown research report based on the
provided plan and sources.

Rules:
- Use ATX headings (##, ###).
- Use citation markers like [1], [2] matching the source list order.
- Every factual claim MUST have a citation marker.
- Use tables / lists where appropriate.
- DO NOT fabricate sources. Only use what's in `sources`.
- DO NOT include "References" section; the system appends it.
- Length: 1500-3000 words depending on topic complexity.
- Stream your output token by token.
```

**LLM 路由**：`model_role = "writer"` → 默认 `gpt-4o`（fallback: `qwen3-max`）

**流式输出实现**：

```python
async def post_process_streaming(self, state):
    """Writer 不走 structured output，走 token stream。"""
    user_prompt = self.build_user_prompt(state)
    draft_chunks = []
    async for chunk in self.llm.astream([self.system_message()] + user_prompt):
        token = chunk.content
        draft_chunks.append(token)
        yield {"type": "message", "delta": token}    # SSE event
    final_draft = "".join(draft_chunks)
    return {"draft": final_draft, "messages": [...]} # 末尾写回 state
```

**Post-process**：把完整 draft 写入 `state["draft"]`；生成引用映射（`[1] → SourceItem`）。

---

### 3.4 Critic

**职责**：检查 draft 给出 critique；决定回 Planner / Researcher / Writer 还是结束。

**State 输入**：`{ plan, sources, draft, critique, iteration }`

**输出 schema**：

```python
class CritiqueItem(BaseModel):
    severity: Literal["low", "medium", "high"]
    category: Literal["factual", "citation", "coverage", "logic", "style"]
    location: str                     # 哪一段（draft 的字符 offset）
    issue: str
    suggestion: str

class CriticDecision(str, Enum):
    APPROVE = "approve"               # 通过，进入 END
    REVISE_PLAN = "revise_plan"       # 拆分问题，回到 Planner
    REVISE_RESEARCH = "revise_research"  # 检索不足，回到 Researcher
    REVISE_DRAFT = "revise_draft"     # 写作问题，回到 Writer

class CriticOutput(BaseModel):
    decision: CriticDecision
    critiques: List[CritiqueItem]
    reasoning: str
```

**System prompt 草稿**：

```
You are a research critic. Review the draft for:
1. Factual accuracy (any claim without citation or with weak citation)
2. Citation density (every claim has a [N] marker)
3. Coverage (all sub-tasks in the plan are addressed)
4. Logical consistency (no contradictions)
5. Style (clear, no fluff, appropriate depth)

Output decision: approve / revise_plan / revise_research / revise_draft.
For revise_*, give specific critiques with location + suggestion.
DO NOT nitpick style. Only flag substantive issues.
```

**LLM 路由**：`model_role = "critic"` → 默认 `o3-mini`（fallback: `deepseek-v3`）—— Critic 是推理任务，用强推理模型更稳。

**Post-process**：把 critique 写入 `state["critique"]`；`iteration` +1；如果 `iteration >= 2` 强制 `approve`（防无限循环）。

---

## 4. LLM 路由（model_role → 具体模型）

详见 [`docs/architecture.md` §3.3](./architecture.md) 和 ADR-0011。

| `model_role` | 主选 | 备选 | 用途 |
|---|---|---|---|
| `planner` | `gpt-4o` | `qwen3-max` | 任务拆解 |
| `researcher` | `gpt-4o` | `qwen3-max` | 搜索策略 + 摘要 |
| `writer` | `gpt-4o` | `qwen3-max` | 综合写作 |
| `critic` | `o3-mini` | `deepseek-v3` | 推理 / 事实核查 |
| `summarizer`（v2）| `gpt-4o-mini` | `glm-4.6` | 摘要 / 提取 |
| `clarifier` | `gpt-4o-mini` | `qwen3-max` | HITL 澄清问题生成 |

实现：`app/llm/router.py`

```python
class LLMRouter:
    def __init__(self, settings: Settings):
        self._clients = {
            "openai-gpt4o": ChatOpenAI(model="gpt-4o", ...),
            "openai-o3-mini": ChatOpenAI(model="o3-mini", ...),
            "openai-gpt4o-mini": ChatOpenAI(model="gpt-4o-mini", ...),
            "dashscope-qwen3-max": ChatDashScope(model="qwen3-max", ...),
            "dashscope-deepseek-v3": ChatDashScope(model="deepseek-v3", ...),
            "dashscope-glm-4-6": ChatDashScope(model="glm-4-6", ...),
        }
        self._role_map = {
            "planner":     ["openai-gpt4o", "dashscope-qwen3-max"],
            "researcher":  ["openai-gpt4o", "dashscope-qwen3-max"],
            "writer":      ["openai-gpt4o", "dashscope-qwen3-max"],
            "critic":      ["openai-o3-mini", "dashscope-deepseek-v3"],
            "summarizer":  ["openai-gpt4o-mini", "dashscope-glm-4-6"],
            "clarifier":   ["openai-gpt4o-mini", "dashscope-qwen3-max"],
        }

    def for_role(self, role: str):
        """返回首个可用的 client；主选失败自动降级。"""
        for client_id in self._role_map[role]:
            client = self._clients[client_id]
            try:
                if client.is_available():
                    return client
            except Exception:
                continue
        raise RuntimeError(f"No LLM available for role={role}")
```

降级策略：每个 client 的 `is_available()` 走健康检查（Redis 计数器记录最近 5 分钟内失败率 > 50% 则不可用）。

## 5. Prompt 版本管理

所有 prompt 集中在 `app/agents/prompts.py`，每个 prompt 顶部带版本号 + 改动说明：

```python
# app/agents/prompts.py

PLANNER_SYSTEM_PROMPT_V1 = """You are a research planner... (见上文)"""

PLANNER_SYSTEM_PROMPT_V2 = """... 改进：增加多语言 query 支持 ..."""

PLANNER_SYSTEM_PROMPT = PLANNER_SYSTEM_PROMPT_V2   # 当前生效版本

# 每个 prompt 对应一个 Langfuse prompt：
#   PLANNER_PROMPT_NAME = "planner-system"
#   上报到 Langfuse 后可在 UI 上做 A/B 测试
```

Langfuse prompt 上报：

```python
from langfuse import get_client
lf = get_client()
lf.create_prompt(
    name="planner-system",
    prompt=PLANNER_SYSTEM_PROMPT,
    labels=["production"],
)
```

## 6. 测试策略（Agent 级）

每个 Agent 必须有：

- **单测**（`tests/agents/test_<name>.py`）：
  - `test_build_user_prompt_*`：覆盖典型 state 输入，断言 user prompt 包含必要 context
  - `test_post_process_*`：覆盖正常 + 异常路径
  - Mock LLM（固定 response）跑端到端 `__call__`
- **集成测试**（`tests/integration/test_graph.py`）：4 个 Agent 一起跑，验证 state 流转
- **E2E**（`tests/e2e/test_hotpotqa.py`）：HotpotQA 子集真 LLM，跑完整 graph，校验最终 draft 包含正确答案
- **Langfuse eval**：`tests/eval/run_eval.py` 跑批量，校验 LLM-as-judge score 阈值

详见 [`docs/eval.md`](./eval.md) 和 [`docs/contributing.md` §6](./contributing.md)。

## 7. 相关文档

- LangGraph 节点 / 边 / HITL interrupt → [`graph-design.md`](./graph-design.md)
- Langfuse trace / score → [`observability.md`](./observability.md)
- 评估数据集 / LLM-as-judge → [`eval.md`](./eval.md)
- LLM 路由策略 → [ADR-0011](./adr/0011-multi-model-task-routing.md)
- HITL clarification prompt → [ADR-0010](./adr/0010-hitl-clarify-with-interrupt.md)
