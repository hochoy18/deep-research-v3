"""FastAPI 路由：threads / messages / SSE / health（OpenAPI v0.1.0-m1）。

M1 极简版（spec Q1 + contracts/openapi.yaml）：
- /health：检查 DB / Redis / Langfuse
- POST /threads：创建 thread（绑定 cookie user_id）
- GET /threads：列当前 user_id 的 threads
- GET /threads/{thread_id}：单 thread 详情；越权 403 / 不存在 404
- POST /threads/{thread_id}/messages：发 query + SSE 流式回显
- GET /threads/{thread_id}/messages：列 thread 消息

依赖注入（Dev.cai.1 拥有 app/api/deps.py）：
- 暂时在本路由内直接 stub：request.state.user_id、compiled graph 等
- Dev.cai.1 上线 deps.py 后切换

越权校验（spec FR-011a）：
- GET /threads/{id} / POST /threads/{id}/messages：比对 thread.user_id 与 cookie user_id
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Annotated, AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sse_starlette.sse import EventSourceResponse

from app.agents.echo import chunk_text
from app.api.schemas import (
    Error,
    Message,
    MessageCreate,
    MessageRoleEnum,
    MessageStatusEnum,
    SSEEvent,
    SSEEventType,
    Thread,
    is_uuid_v4,
)
from app.db.session import get_session
from app.graph.graph import get_compiled_graph
from app.observability.langfuse import check_langfuse_configured


# 注意：以下 import 是模块级；不要在 _stream_echo_response 局部 try 里 re-import，
# 否则会触发 UnboundLocalError（局部变量遮蔽模块级）。
from app.db.models import Message as MessageORM  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter()


# === Dependency: cookie user_id（M1 stub；Dev.cai.4 拥有正式 middleware） === #


def _get_user_id(request: Request) -> str:
    """M1 dev stub：Dev.cai.4 的 app/auth/anonymous.py 上线前用 header 替代。

    Phase 2 阶段：支持 ``X-User-Id`` 头（测试用）+ ``user_id`` cookie（前端自动带）
    """
    # 优先 cookie（前端浏览器行为）
    if "user_id" in request.cookies:
        return request.cookies["user_id"]
    # 再 header（测试 / curl）
    if "X-User-Id" in request.headers:
        return request.headers["X-User-Id"]
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=Error(
            error="unauthorized", message="user_id cookie/header missing"
        ).model_dump(),
    )


def _ensure_user_id_format(user_id: str) -> None:
    """data-model.md §1 UUID v4 严格校验。"""
    if not is_uuid_v4(user_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=Error(
                error="unauthorized", message="user_id must be a UUID v4"
            ).model_dump(),
        )


# === /health === #


@router.get("/health", tags=["health"])
async def health() -> dict:
    """后端健康检查（contracts/openapi.yaml /health）。"""
    deps: dict[str, str] = {}
    # Langfuse 状态（最廉价的检查）
    lf_ok, lf_msg = check_langfuse_configured()
    deps["langfuse"] = "up" if lf_ok else f"down ({lf_msg})"
    # DB / Redis 不真正连（M1 简化为 env presence）
    deps["postgres"] = "env-present" if _env_has("DATABASE_URL") else "missing"
    deps["redis"] = "env-present" if _env_has("REDIS_URL") else "missing"
    overall = "ok" if all(v in {"up", "env-present"} for v in deps.values()) else "degraded"
    return {"status": overall, "dependencies": deps}


def _env_has(name: str) -> bool:
    import os

    return bool(os.environ.get(name))


# === /threads (POST = create, GET = list) === #


@router.post(
    "/threads",
    tags=["threads"],
    status_code=status.HTTP_201_CREATED,
    response_model=Thread,
)
async def create_thread(request: Request) -> Thread:
    user_id = _get_user_id(request)
    _ensure_user_id_format(user_id)

    from app.db.models import ThreadStatusEnum, Thread as ThreadORM

    new_id = uuid.uuid4()
    async with get_session() as session:
        orm = ThreadORM(
            thread_id=new_id,
            user_id=uuid.UUID(user_id),
            title="新对话",
            status=ThreadStatusEnum.ACTIVE.value,
            langgraph_thread_id=new_id,
        )
        session.add(orm)
        await session.flush()
        # 必须 flush 后才能读到 server_default（title / status / created_at 等）
        await session.refresh(orm)

    return Thread.model_validate(orm)


@router.get("/threads", tags=["threads"])
async def list_threads(request: Request) -> dict:
    user_id = _get_user_id(request)
    _ensure_user_id_format(user_id)

    from sqlalchemy import select

    from app.db.models import Thread as ThreadORM

    async with get_session() as session:
        stmt = (
            select(ThreadORM)
            .where(ThreadORM.user_id == uuid.UUID(user_id))
            .order_by(ThreadORM.updated_at.desc())
        )
        rows = (await session.execute(stmt)).scalars().all()

    return {"threads": [Thread.model_validate(r) for r in rows]}


# === /threads/{id} (GET) === #


@router.get("/threads/{thread_id}", tags=["threads"], response_model=Thread)
async def get_thread(thread_id: str, request: Request) -> Thread:
    if not is_uuid_v4(thread_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=Error(error="not_found", message="invalid thread id").model_dump(),
        )
    user_id = _get_user_id(request)
    _ensure_user_id_format(user_id)

    from sqlalchemy import select

    from app.db.models import Thread as ThreadORM

    async with get_session() as session:
        stmt = select(ThreadORM).where(ThreadORM.thread_id == uuid.UUID(thread_id))
        row = (await session.execute(stmt)).scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=Error(error="not_found", message="thread not found").model_dump(),
        )

    if str(row.user_id) != user_id:
        # 越权读防护（spec FR-011a / SC-011）
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=Error(error="forbidden", message="not your thread").model_dump(),
        )

    return Thread.model_validate(row)


# === /threads/{id}/messages (POST = send + SSE, GET = list) === #


@router.get("/threads/{thread_id}/messages", tags=["messages"])
async def list_messages(thread_id: str, request: Request) -> dict:
    """列 thread 下所有消息（GET 路径上同样走越权校验）。"""
    if not is_uuid_v4(thread_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=Error(error="not_found", message="invalid thread id").model_dump(),
        )
    user_id = _get_user_id(request)
    _ensure_user_id_format(user_id)

    from sqlalchemy import select

    from app.db.models import Message as MessageORM, Thread as ThreadORM

    async with get_session() as session:
        # 先校验 thread 越权
        thread = (
            await session.execute(
                select(ThreadORM).where(ThreadORM.thread_id == uuid.UUID(thread_id))
            )
        ).scalar_one_or_none()

        if thread is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Error(error="not_found", message="thread not found").model_dump(),
            )
        if str(thread.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=Error(error="forbidden", message="not your thread").model_dump(),
            )

        msgs = (
            (
                await session.execute(
                    select(MessageORM)
                    .where(MessageORM.thread_id == uuid.UUID(thread_id))
                    .order_by(MessageORM.created_at.asc())
                )
            )
            .scalars()
            .all()
        )

    return {"messages": [Message.model_validate(m) for m in msgs]}


@router.post("/threads/{thread_id}/messages", tags=["messages"])
async def post_message(
    thread_id: str,
    request: Request,
) -> EventSourceResponse:
    """发消息 + 返回 SSE 流（M1 极简 echo）。

    SSE event 流：
        1. ``state_update`` status=streaming
        2. 1..N ``message`` event（按 word 切片）
        3. ``state_update`` status=complete + completed_at
        4. ``done`` total_chunks=N + latency_ms

    错误路径：
        - 422（schema 校验失败：白名单 + 长度）
        - 403 / 404（thread 越权 / 不存在）
        - ``error`` SSE event（运行时错）
    """
    # === 路径参数校验 === #
    if not is_uuid_v4(thread_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=Error(error="not_found", message="invalid thread id").model_dump(),
        )
    user_id = _get_user_id(request)
    _ensure_user_id_format(user_id)

    # === 请求体校验（白名单） === #
    try:
        body_raw = await request.body()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=Error(error="bad_request", message="body read failed").model_dump(),
        )
    if not body_raw:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=Error(error="validation_error", message="empty body").model_dump(),
        )

    import json

    try:
        payload = json.loads(body_raw.decode("utf-8"))
        create = MessageCreate.model_validate(payload)
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=Error(
                error="validation_error",
                message=str(exc) if isinstance(exc, ValidationError) else "bad json",
            ).model_dump(),
        )

    # === 越权 / thread 存在性 === #
    from sqlalchemy import select

    from app.db.models import Message as MessageORM, Thread as ThreadORM

    async with get_session() as session:
        thread = (
            await session.execute(
                select(ThreadORM).where(ThreadORM.thread_id == uuid.UUID(thread_id))
            )
        ).scalar_one_or_none()

        if thread is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=Error(error="not_found", message="thread not found").model_dump(),
            )
        if str(thread.user_id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=Error(error="forbidden", message="not your thread").model_dump(),
            )

        # 持久化 user message
        user_msg_id = uuid.uuid4()
        user_msg = MessageORM(
            message_id=user_msg_id,
            thread_id=uuid.UUID(thread_id),
            role=MessageRoleEnum.USER.value,
            content=create.content,
            status=MessageStatusEnum.COMPLETE.value,
        )
        session.add(user_msg)
        # 创建 assistant message 占位
        assistant_msg_id = uuid.uuid4()
        assistant_msg = MessageORM(
            message_id=assistant_msg_id,
            thread_id=uuid.UUID(thread_id),
            role=MessageRoleEnum.ASSISTANT.value,
            content="",  # streaming 时填
            status=MessageStatusEnum.STREAMING.value,
        )
        session.add(assistant_msg)

    # === SSE 流 === #
    return EventSourceResponse(
        _stream_echo_response(
            thread_id=thread_id,
            user_id=user_id,
            user_query=create.content,
            assistant_message_id=str(assistant_msg_id),
        ),
        media_type="text/event-stream",
    )


async def _stream_echo_response(
    *,
    thread_id: str,
    user_id: str,
    user_query: str,
    assistant_message_id: str,
) -> AsyncIterator[dict]:
    """SSE event 生成器：state_update → message* → done。

    不调真 LLM：直接 echo。
    完成后写 assistant message status=complete + completed_at + content。
    """
    start = time.monotonic()
    chunks = list(chunk_text(user_query))
    total = len(chunks)
    built_content = ""

    # 1. streaming 状态
    yield {
        "event": SSEEventType.STATE_UPDATE.value,
        "data": {
            "message_id": assistant_message_id,
            "status": MessageStatusEnum.STREAMING.value,
        },
    }

    # 2. message events
    for i, chunk in enumerate(chunks):
        await asyncio.sleep(0)  # 让出事件循环给 consumer
        built_content += chunk
        yield {
            "event": SSEEventType.MESSAGE.value,
            "data": {
                "message_id": assistant_message_id,
                "chunk": chunk,
                "index": i,
            },
        }

    # 3.1 同步更新 DB（complete）
    try:
        from datetime import datetime, timezone

        from sqlalchemy import select

        async with get_session() as session:
            stmt = select(MessageORM).where(
                MessageORM.message_id == uuid.UUID(assistant_message_id)
            )
            msg = (await session.execute(stmt)).scalar_one_or_none()
            if msg is not None:
                msg.status = MessageStatusEnum.COMPLETE.value
                msg.content = built_content
                msg.completed_at = datetime.now(timezone.utc)
    except Exception as exc:
        logger.exception("failed to update assistant msg: %s", exc)
        yield {
            "event": SSEEventType.ERROR.value,
            "data": {"code": "internal_error", "message": str(exc)},
        }
        return

    # 3.2 state_update complete
    yield {
        "event": SSEEventType.STATE_UPDATE.value,
        "data": {
            "message_id": assistant_message_id,
            "status": MessageStatusEnum.COMPLETE.value,
        },
    }

    # 4. done
    latency_ms = int((time.monotonic() - start) * 1000)
    yield {
        "event": SSEEventType.DONE.value,
        "data": {
            "message_id": assistant_message_id,
            "total_chunks": total,
            "latency_ms": latency_ms,
        },
    }


# === Re-export compiled graph getter for deps === #
__all__ = ["router", "get_compiled_graph"]
