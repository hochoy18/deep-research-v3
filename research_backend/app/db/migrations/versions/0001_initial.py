"""Initial migration: threads + messages + 2 indexes + 1 partial index。

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-16

字段与 index 严格 1:1 对齐 data-model.md §2/§3 与 app/db/models.py：
- threads (7 字段)
- messages (7 字段 + FK ON DELETE CASCADE)
- idx_threads_user_id (user_id, updated_at)
- idx_threads_status (partial: status=active)
- idx_messages_thread_id (thread_id, created_at)
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PGUUID


# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "threads",
        sa.Column("thread_id", PGUUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", PGUUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default="新对话"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("langgraph_thread_id", PGUUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "idx_threads_user_id", "threads", ["user_id", "updated_at"]
    )
    op.create_index(
        "idx_threads_status",
        "threads",
        ["status"],
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "messages",
        sa.Column(
            "message_id", PGUUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "thread_id",
            PGUUID(as_uuid=True),
            sa.ForeignKey("threads.thread_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="streaming"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_messages_thread_id", "messages", ["thread_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_messages_thread_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("idx_threads_status", table_name="threads")
    op.drop_index("idx_threads_user_id", table_name="threads")
    op.drop_table("threads")
