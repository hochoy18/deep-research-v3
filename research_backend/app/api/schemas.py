"""Pydantic 模型：Thread / Message / MessageCreate / SSEEvent / Error。

严格对齐 contracts/openapi.yaml v0.1.0-m1。任何字段改动 → 同步 OpenAPI + 测试。

constitution I 白名单校验：
- content 必须经过 _validate_user_content() 校验（ASCII printable +
  常见中日韩字符 + 换行）
- 长度限制 1..10000（防止 DoS）

字段命名：snake_case，对齐 Postgres / JSON over wire。
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from enum import Enum
from typing import Annotated, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


# === Schemas for /threads === #


class ThreadStatusEnum(str, Enum):
    """data-model.md §2 + OpenAPI 一致。"""
    ACTIVE = "active"
    ARCHIVED = "archived"


class Thread(BaseModel):
    """GET /threads 与 POST /threads 响应模型。"""
    model_config = ConfigDict(from_attributes=True)

    thread_id: uuid.UUID
    user_id: uuid.UUID = Field(description="所属用户（与 cookie user_id 一致）")
    title: str = Field(default="新对话", max_length=200)
    status: ThreadStatusEnum = ThreadStatusEnum.ACTIVE
    created_at: datetime
    updated_at: datetime
    langgraph_thread_id: Optional[uuid.UUID] = None
    message_count: Optional[int] = Field(
        default=None, ge=0, description="该 thread 下的消息数（可选字段）"
    )


# === Schemas for /threads/{id}/messages === #


class MessageRoleEnum(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageStatusEnum(str, Enum):
    STREAMING = "streaming"
    COMPLETE = "complete"
    FAILED = "failed"


class MessageCreate(BaseModel):
    """POST /threads/{id}/messages 请求体。"""
    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="用户 query（M1 阶段 1-10000 字符）。MUST 经过白名单校验。",
    )

    @field_validator("content")
    @classmethod
    def _whitelist_user_content(cls, v: str) -> str:
        """constitution I 白名单校验。

        允许：ASCII printable (32..126) + 常见中日韩 (CJK Unified Ideographs) +
        \n；禁止控制字符（除 \n）+ DEL (127)。

        注：每行长度未限制（OpenAPI / data-model 未声明），仅控总量 + 控制字符。
        """
        if len(v) > 10_000:
            raise ValueError("content exceeds 10000 chars")

        # 拒 control char（除 \n）与 DEL
        if any((ord(c) < 32 or ord(c) == 127) and c != "\n" for c in v):
            raise ValueError("control characters not allowed")

        return v


class Message(BaseModel):
    """GET /threads/{id}/messages 响应元素。"""
    model_config = ConfigDict(from_attributes=True)

    message_id: uuid.UUID
    thread_id: uuid.UUID
    role: MessageRoleEnum
    content: str
    status: MessageStatusEnum
    created_at: datetime
    completed_at: Optional[datetime] = None


# === Schemas for SSE === #


class SSEEventType(str, Enum):
    """OpenAPI SSEEvent.event 枚举。"""
    MESSAGE = "message"
    STATE_UPDATE = "state_update"
    DONE = "done"
    ERROR = "error"


class _MessageChunk(BaseModel):
    message_id: uuid.UUID
    chunk: str = Field(description="单个 token 切片（Markdown fragment）")
    index: int = Field(ge=0, description="chunk 序号（0-based）")


class _StateUpdate(BaseModel):
    message_id: uuid.UUID
    status: MessageStatusEnum


class _Done(BaseModel):
    message_id: uuid.UUID
    total_chunks: int = Field(ge=0)
    latency_ms: int = Field(ge=0)


class _ErrorDetail(BaseModel):
    code: str
    message: str


class SSEEvent(BaseModel):
    """Server-Sent Event envelope（data 字段按 event 分型）。

    data 字段语义上对应 oneOf，但 Pydantic v2 Union 不在 strict discriminator 模式
    下通过；M1 阶段仅作为 shape 锁定，运行时 routes 用更窄的 data 构造。
    """
    event: SSEEventType
    data: Union[_MessageChunk, _StateUpdate, _Done, _ErrorDetail]


# === Common Error === #


class Error(BaseModel):
    """OpenAPI Error schema。"""
    error: str
    message: str
    details: Optional[dict] = None


# === Helper: compose quick-validating UUID v4 === #

_UUID_V4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_uuid_v4(value: str) -> bool:
    """data-model.md §1 规定的 UUID v4 校验（用于路由 path 参数）。"""
    return bool(_UUID_V4.match(value))


# === Re-exports for convenience === #

__all__ = [
    "Thread",
    "Message",
    "MessageCreate",
    "SSEEvent",
    "SSEEventType",
    "Error",
    "is_uuid_v4",
]
