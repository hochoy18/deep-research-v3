# Graph 设计（Graph Design）

> LangGraph StateGraph 的完整设计：State schema、节点、边、条件路由、HITL `interrupt()` 实现、Redis checkpoint 配置。Agent prompt / 工具集见 [`agent-design.md`](./agent-design.md)。

---

## 1. AgentState（核心 State schema）

```python
# app/graph/state.py
from typing import Annotated, List, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from datetime import datetime


class SubTask(TypedDict):
    id: str                              # "st-1"
    description: str
    depends_on: List[str]
    search_queries: List[str]
    expected_sources: int
    status: str                          # "pending" / "running" / "done" / "failed"


class SourceItem(TypedDict):
    id: str
    url: str
    title: str
    excerpt: str
    score: float
    fetched_at: str                      # ISO 8601
    used_in_subtask: str


class CritiqueItem(TypedDict):
    severity: str                        # "low" / "medium" / "high"
    category: str                        # "factual" / "citation" / "coverage" / "logic" / "style"
    location: str                        # draft 字符 offset 范围
    issue: str
    suggestion: str


class AgentState(TypedDict, total=False):
    """LangGraph 持久化的全部 state。

    total=False：所有字段可选；Agent 按需填充。
    """

    # === 基础会话 ===
    thread_id: str
    query: str
    research_brief: Dict[str, Any]       # HITL 澄清后填充

    # === 消息历史（LangGraph 标准）===
    messages: Annotated[List[BaseMessage], add_messages]

    # === 规划 ===
    plan: List[SubTask]
    current_subtask_id: str | None

    # === 检索结果 ===
    sources: List[SourceItem]

    # === 写作 ===
    draft: str

    # === 审查 ===
    critique: List[CritiqueItem]
    iteration: int                       # 防止 Critic 无限循环

    # === 元数据 ===
    metadata: Dict[str, Any]             # tokens / cost / 触发 HITL 次数 / start_ts / end_ts / langfuse_trace_id
    config: Dict[str, Any]               # 用户传入的运行时配置（如模型路由 override）
```

要点：
- `messages` 用 `add_messages` reducer，自动追加而不是覆盖
- 其它字段都是直接覆盖（覆盖语义由 LangGraph 默认行为决定）
- `total=False` 让所有字段可选，方便部分恢复

## 2. StateGraph 节点图

```
                ┌────────────────────────────────────────────────────────────┐
                │                                                            │
                │    ┌──────────────────┐                                     │
                │    │  clarify_with_user │  ★ interrupt (HITL 触发点 1)        │
                │    └────────┬──────────┘                                     │
                │             │ Command(resume=user_reply, goto=...)           │
                │             ▼                                               │
                │    ┌──────────────────┐                                     │
                │    │ write_research_   │                                    │
                │    │      brief        │                                    │
                │    └────────┬──────────┘                                     │
                │             ▼                                               │
   ┌────────────┴────────────┐                                              │
   │       Planner           │  把 query 拆成 SubTask 列表                    │
   └────────────┬────────────┘                                              │
                │                                                          │
                ▼                                                          │
   ┌──────────────────────────┐                                            │
   │  HITL topic list 审阅    │  ★ interrupt (HITL 触发点 2，sub-task 列表)   │
   └────────────┬─────────────┘                                            │
                │ Command(resume=modified_topics, goto=...)                 │
                ▼                                                          │
   ┌────────────────────────────┐                                          │
   │       Researcher           │  循环：web_search + fetch_page            │
   │  (sub-graph, see §3)       │  直到 plan 全部 done                       │
   └────────────┬───────────────┘                                          │
                │                                                          │
                ▼                                                          │
   ┌────────────────────────────┐                                          │
   │       Writer               │  流式输出 draft                            │
   └────────────┬───────────────┘                                          │
                │                                                          │
                ▼                                                          │
   ┌────────────────────────────┐                                          │
   │       Critic               │  decision: approve / revise_*             │
   └────────────┬───────────────┘                                          │
                │ (conditional edge)                                       │
                ├─ approve ─────────────────────────────→ END               │
                ├─ revise_plan ──────────────────────────→ Planner          │
                ├─ revise_research ─────────────────────→ Researcher       │
                └─ revise_draft ───────────────────────→ Writer            │
                                                                       │
                                                                       │
                └────────────────────────────────────────────────────────┘
```

## 3. Researcher 子图（sub-graph）

Researcher 内部是循环结构，用 LangGraph 的 `add_conditional_edges` 控制：

```python
researcher_graph = StateGraph(ResearcherState)

researcher_graph.add_node("search",        search_node)        # 调 web_search
researcher_graph.add_node("fetch",         fetch_node)         # 调 fetch_page
researcher_graph.add_node("summarize",     summarize_node)     # 调 LLM 摘要
researcher_graph.add_node("decide_next",   decide_next_node)   # 决定下一个 sub-task

researcher_graph.set_entry_point("search")
researcher_graph.add_edge("search",    "fetch")
researcher_graph.add_edge("fetch",     "summarize")
researcher_graph.add_edge("summarize", "decide_next")
researcher_graph.add_conditional_edges(
    "decide_next",
    lambda s: "search" if s["next_subtask_id"] else "__end__",
    {"search": "search", "__end__": END},
)

researcher_subgraph = researcher_graph.compile()
```

主图把 Researcher 节点定义为一个 `Command(goto=...)` 包装，调用 `researcher_subgraph.ainvoke()` 后跳到 Writer。

## 4. HITL interrupt 实现（重点）

### 4.1 双轨判定（是否需要追问）

```python
# app/agents/clarifier.py
from langgraph.types import interrupt
from langfuse import get_client

NEED_CLARIFY_RULES = [
    lambda q: len(q.strip()) < 10,                              # 太短
    lambda q: any(w in q.lower() for w in ["best", "top", "good"]),  # 主观词
    lambda q: not any(w in q.lower() for w in [                 # 缺关键参数
        "budget", "time", "year", "month", "audience", "for"
    ]),
]

def needs_clarification(query: str) -> bool:
    if any(rule(query) for rule in NEED_CLARIFY_RULES):
        return True
    # 第二轨：LLM 评分类
    return _llm_judge_clarification(query)

async def _llm_judge_clarification(query: str) -> bool:
    from langchain_openai import ChatOpenAI
    from pydantic import BaseModel
    llm = ChatOpenAI(model="gpt-4o-mini").with_structured_output(ClarifyDecision)

    class ClarifyDecision(BaseModel):
        needs_clarification: bool
        question: str = ""
        verification: str = ""

    result = await llm.ainvoke([clarify_system_prompt(), query])
    return result.needs_clarification
```

### 4.2 `clarify_with_user` 节点

```python
# app/graph/nodes.py
from langgraph.types import interrupt, Command

async def clarify_with_user_node(state: AgentState) -> Command:
    """HITL 触发点 1：在 Planner 之前澄清方向。"""

    # 判定是否需要追问
    needs_clarify = needs_clarification(state["query"])
    if not needs_clarify:
        return Command(
            update={
                "research_brief": {"verified": True, "scope": state["query"]},
                "metadata": {**state.get("metadata", {}), "skipped_clarification": True},
            },
            goto="write_research_brief",
        )

    # 生成追问问题（3-5 个 chip + 自由输入）
    questions = await generate_clarification_questions(state["query"])

    # ★ interrupt 暂停在这里
    user_reply = interrupt({
        "type": "clarify",
        "questions": questions,    # [{ "id": "scope", "label": "范围", "options": [...] }, ...]
        "skip_available": True,
    })

    # 用户回复后恢复（Command(resume=user_reply) 触发）
    return Command(
        update={
            "research_brief": parse_user_reply(user_reply),
            "messages": [AIMessage(content=user_reply_summary(questions, user_reply))],
        },
        goto="write_research_brief",
    )
```

恢复调用（前端触发）：

```python
# FastAPI route: POST /api/research/{thread_id}/resume
from langgraph.types import Command

graph = compiled_graph()
async def resume_research(thread_id: str, user_reply: dict):
    config = {"configurable": {"thread_id": thread_id}}
    async for event in graph.astream(Command(resume=user_reply), config=config):
        yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
```

### 4.3 topic list 审阅节点

```python
async def topic_review_node(state: AgentState) -> Command:
    """HITL 触发点 2：让用户增删改 topic 列表。"""

    topics = [st["description"] for st in state["plan"]]

    user_modified = interrupt({
        "type": "topic_review",
        "topics": topics,                  # ["固态电池 消费电子应用", "动力电池 进展", ...]
        "operations": ["add", "delete", "edit"],
        "skip_available": True,
    })

    if user_modified.get("skip"):
        return Command(goto="researcher")

    new_plan = apply_topic_changes(state["plan"], user_modified)
    return Command(update={"plan": new_plan}, goto="researcher")
```

### 4.4 prompt 模板（clarifier）

```python
# app/agents/prompts.py

CLARIFY_WITH_USER_INSTRUCTIONS = """\
You are a research clarification assistant. Given the user's query, decide \
whether you need to ask clarifying questions.

Generate exactly 3-5 pivotal questions, ranked by priority:
1. scope / domain coverage
2. time range
3. audience / depth
4. output format
5. source preference
6. language

Format: JSON array of { id, label, options: [{ value, label }, ...] }
Each question should have 2-4 chip options + allow free text.

Rules:
- Be concise while gathering all necessary information.
- Don't ask for unnecessary information.
- If the user has already provided the information, do NOT re-ask.
- If the query is clear enough, return needs_clarification=false and a \
  verification string like "I'll cover X from Y for Z in format W."
"""
```

引用 LangChain Open Deep Research 的 `clarify_with_user_instructions`（参考 `src/open_deep_research/prompts.py`）并做了以下微调：

1. **加入中文 query 适配**：instruction 末尾加 "If query is Chinese, generate Chinese options"
2. **chip 数量上限 4**：避免选项爆炸
3. **verification 字段**：当无需追问时显式说明会覆盖什么，给用户建立信任

## 5. 边与条件路由

```python
# app/graph/edges.py
from langgraph.graph import END

def critic_decision_router(state: AgentState) -> str:
    """Critic 节点的输出 → 下一节点。"""
    last_critique = state.get("critique", [])[-1] if state.get("critique") else None
    if not last_critique:
        return "approve"

    # iteration 兜底（防无限循环）
    if state.get("iteration", 0) >= 2:
        return "approve"

    # 决策路由（写入 critic 输出里的 decision 字段）
    decision = last_critique.get("decision", "approve")
    return {
        "approve": END,
        "revise_plan": "planner",
        "revise_research": "researcher",
        "revise_draft": "writer",
    }.get(decision, END)


def researcher_loop_router(state: AgentState) -> str:
    """Researcher 子图 → 主图下一节点。"""
    if state.get("current_subtask_id") is None:
        return "writer"
    return "researcher"
```

主图构建：

```python
# app/graph/workflow.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.redis import RedisCheckpointSaver
from app.graph.state import AgentState
from app.graph.nodes import (
    clarify_with_user_node,
    write_research_brief_node,
    planner_node,
    topic_review_node,
    researcher_node,
    writer_node,
    critic_node,
)
from app.graph.edges import critic_decision_router

builder = StateGraph(AgentState)

builder.add_node("clarify_with_user", clarify_with_user_node)
builder.add_node("write_research_brief", write_research_brief_node)
builder.add_node("planner", planner_node)
builder.add_node("topic_review", topic_review_node)
builder.add_node("researcher", researcher_node)
builder.add_node("writer", writer_node)
builder.add_node("critic", critic_node)

builder.add_edge(START, "clarify_with_user")
builder.add_edge("write_research_brief", "planner")
builder.add_edge("planner", "topic_review")
builder.add_edge("topic_review", "researcher")
builder.add_edge("researcher", "writer")
builder.add_edge("writer", "critic")
builder.add_conditional_edges(
    "critic",
    critic_decision_router,
    {
        "approve": END,
        "revise_plan": "planner",
        "revise_research": "researcher",
        "revise_draft": "writer",
    },
)

# Redis checkpoint
checkpointer = RedisCheckpointSaver(
    redis_url=settings.redis_url,
    ttl=7 * 24 * 3600,       # 7 天
)

compiled_graph = builder.compile(checkpointer=checkpointer)
```

## 6. SSE event 协议

```python
# app/api/routes.py
from fastapi.responses import StreamingResponse

@router.post("/research/stream")
async def research_stream(req: ResearchRequest):
    config = {"configurable": {"thread_id": req.thread_id or str(uuid4())}}
    inputs = {"query": req.query, "messages": [], "metadata": {}}

    async def event_generator():
        async for event in compiled_graph.astream(inputs, config=config):
            # event 形如: ("node_name", {"state_field": value, ...}) 或 interrupt 事件
            for sse_event in to_sse_events(event):
                yield f"event: {sse_event['event']}\ndata: {json.dumps(sse_event['data'])}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def to_sse_events(raw_event) -> List[dict]:
    """LangGraph event → 前端 SSE event。"""
    events = []
    if isinstance(raw_event, dict):
        if "messages" in raw_event and raw_event["messages"]:
            for msg in raw_event["messages"]:
                events.append({"event": "message", "data": serialize_message(msg)})
        if "plan" in raw_event:
            events.append({"event": "state_update", "data": {"plan": raw_event["plan"]}})
        if "sources" in raw_event:
            events.append({"event": "state_update", "data": {"sources": raw_event["sources"]}})
        if "draft" in raw_event:
            events.append({"event": "state_update", "data": {"draft": raw_event["draft"]}})
        if "critique" in raw_event:
            events.append({"event": "state_update", "data": {"critique": raw_event["critique"]}})
    elif isinstance(raw_event, tuple) and raw_event[0] == "interrupt":
        events.append({"event": "interrupt", "data": raw_event[1]})
    return events
```

完整 SSE event 类型：

| event | data 字段 | 触发时机 |
|---|---|---|
| `node_start` | `{ node, thread_id, ts }` | 每个节点开始 |
| `tool_call` | `{ tool, input, ts }` | Planner / Researcher 调工具 |
| `tool_result` | `{ tool, output, latency_ms }` | 工具返回 |
| `message` | `{ role, content (delta) }` | 流式 token |
| `state_update` | `{ plan / sources / draft / critique }` | state 字段更新 |
| `interrupt` | `{ type, questions / topics }` | HITL 触发 |
| `done` | `{ thread_id, report_url, total_tokens }` | 研究流结束 |
| `error` | `{ code, message }` | 异常 |

## 7. Redis Checkpoint 配置

```python
# app/persistence/redis_checkpoint.py
from langgraph.checkpoint.redis import RedisCheckpointSaver

def get_checkpointer(settings):
    return RedisCheckpointSaver(
        redis_url=settings.redis_url,
        ttl={
            "default": 7 * 24 * 3600,         # 7 天
            "default_refresh_ttl": True,      # 每次访问刷新 TTL
        },
        key_prefix="deep-research:checkpoint:",
        # 把 state 压缩（pickle 之前 gzip）
        serde="gzip",
    )
```

Key 命名：`deep-research:checkpoint:{thread_id}:{checkpoint_id}`

容量估算：单条 state 平均 50KB（含 plan / sources / draft）；1000 个活跃 thread ≈ 50MB。Redis 8 起步 4GB 内存足够。

## 8. 完整调用流程（一次研究）

```
1. POST /api/research/stream { query: "...", thread_id: null }
2. backend 创建 thread_id（uuid4）→ 写 Postgres threads 表
3. 打开 Langfuse trace (OTel current_observation)
4. compiled_graph.astream(inputs, configurable={"thread_id": ...})
5. 流经过程：
   - clarify_with_user 触发 interrupt → SSE: event: interrupt
   - 用户在前端回答 → POST /api/research/{thread_id}/resume { user_reply }
   - backend 调 graph.astream(Command(resume=user_reply), ...)
   - 继续流过 write_research_brief / planner / topic_review ...
6. 流经过程中：
   - 每个节点产生 token / state_update 事件 → SSE
   - Writer 的 token 流式输出 → SSE
7. END 节点：生成 report → 写 Postgres + MinIO
8. Langfuse LLM-as-judge 打分 → 上报
9. SSE: event: done { thread_id, report_url, total_tokens, scores }
```

## 9. 失败恢复

用户中断（关浏览器）后回到原页面：

```
1. GET /api/threads/{thread_id}
2. 后端读 Postgres 拿最新 state（也用 Redis checkpoint 兜底）
3. 前端展示当前 state（plan / sources / draft / critique）
4. 如果 state 是 interrupted 状态，前端展示追问面板等用户回答
5. 用户回答 → POST /api/research/{thread_id}/resume
```

异常恢复（后端崩溃 / k8s 重启）：

```
1. Redis checkpoint 里有最近一次 state
2. 新实例启动后，用户刷新页面 → GET /api/threads/{thread_id}
3. 后端从 Redis 恢复 state → 继续
```

## 10. 相关文档

- 4 个 Agent 的 prompt / LLM 路由 → [`agent-design.md`](./agent-design.md)
- 工具契约（web_search / fetch_page / cite）→ [`agent-design.md` §3.4](./agent-design.md)
- Langfuse trace / score → [`observability.md`](./observability.md)
- 评估 / HotpotQA → [`eval.md`](./eval.md)
- HITL interrupt 决策 → [ADR-0010](./adr/0010-hitl-clarify-with-interrupt.md)
- LangGraph 选型 → [ADR-0001](./adr/0001-langgraph-over-crewai.md)
