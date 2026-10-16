"""SQLAlchemy 2.x async ORM: Thread + Message 模型。

字段映射 data-model.md §2/§3,严格对齐 Postgres schema：
- threads: UUID PK + user_id index + status partial index
- messages: UUID PK + FK → threads(ON DELETE CASCADE) + (thread_id, created_at) 索引

约束：
- Mapped[...] / mapped_column(...) 是 SQLAlchemy 2.0 typed style（声明式 typing）
- 不做 database-level CHECK 约束（status enum 用 Python 端校验在 app 层守门）
- migrations/001_initial.py 与本文件字段必须严格 1:1 对齐
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    Index,
    ForeignKey,
    DateTime,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """所有 ORM 模型的 declarative 基类（M1 仅 2 个模型，共用基类即可）。"""


class ThreadStatus(str, enum.Enum):
    """Thread 状态枚举（data-model.md §2）。"""
    ACTIVE = "active"
    ARCHIVED = "archived"


class MessageRole(str, enum.Enum):
    """Message role 枚举（data-model.md §3）。"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageStatus(str, enum.Enum):
    """Message status 枚举（data-model.md §3）。"""
    STREAMING = "streaming"
    COMPLETE = "complete"
    FAILED = "failed"


class Thread(Base):
    """Thread ORM 模型（data-model.md §2 Postgres schema）。

    字段：
    - thread_id:        UUID PK
    - user_id:          UUID,逻辑外键（不做 DB-level FK 约束；越权校验在路由中间件）
    - title:            VARCHAR(200),default='新对话'
    - status:           VARCHAR(20),default='active',enum: {active,archived}
    - created_at:       TIMESTAMPTZ,default NOW()
    - updated_at:       TIMESTAMPTZ,default NOW(),ON UPDATE NOW()
    - langgraph_thread_id: UUID,与 thread_id 1:1；冗余存储便于 checkpoint 恢复
    """

    __tablename__ = "threads"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, server_default="新对话"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=ThreadStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    langgraph_thread_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )

    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="thread", cascade="all, delete-orphan"
    )

    __table_args__ = (
        # 列表查询优化（spec: list 用户的 thread 按 updated_at DESC）
        Index("idx_threads_user_id", "user_id", "updated_at"),
        # partial index on active status（data-model.md §2）
        Index(
            "idx_threads_status",
            "status",
            postgresql_where=(status == ThreadStatus.ACTIVE.value),
        ),
    )


class Message(Base):
    """Message ORM 模型（data-model.md §3 Postgres schema）。

    字段：
    - message_id: UUID PK
    - thread_id: UUID FK → threads(thread_id) ON DELETE CASCADE
    - role:       VARCHAR(20), {user, assistant, system}
    - content:    TEXT
    - status:     VARCHAR(20),default='streaming',{streaming,complete,failed}
    - created_at: TIMESTAMPTZ,default NOW()
    - completed_at: TIMESTAMPTZ,nullable
    """

    __tablename__ = "messages"

    message_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("threads.thread_id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=MessageStatus.STREAMING.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    thread: Mapped[Thread] = relationship("Thread", back_populates="messages")

    __table_args__ = (
        # 单 thread 消息列表按 created_at ASC（data-model.md §3）
        Index("idx_messages_thread_id", "thread_id", "created_at"),
    )
