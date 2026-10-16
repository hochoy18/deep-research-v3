"""T019 ORM 模型单元测试：不连 DB，只查 metadata。

覆盖：
- 表名匹配（threads / messages）
- 字段集合匹配 data-model.md §2/§3
- 索引匹配 data-model.md
- enum 字符串值正确
"""
from __future__ import annotations

from app.db.models import (
    Base,
    Message,
    MessageRole,
    MessageStatus,
    Thread,
    ThreadStatus,
)


class TestThreadModel:
    """Thread ORM schema 锁定（data-model.md §2）。"""

    def test_table_name(self) -> None:
        assert Thread.__tablename__ == "threads"

    def test_required_columns_present(self) -> None:
        cols = {c.name for c in Thread.__table__.columns}
        expected = {
            "thread_id",
            "user_id",
            "title",
            "status",
            "created_at",
            "updated_at",
            "langgraph_thread_id",
        }
        assert expected.issubset(cols)

    def test_thread_id_is_primary_key(self) -> None:
        pk_cols = [c.name for c in Thread.__table__.primary_key.columns]
        assert pk_cols == ["thread_id"]

    def test_title_default_is_new_conversation(self) -> None:
        """默认 title = '新对话'（data-model.md §2）。"""
        title_col = Thread.__table__.columns["title"]
        assert title_col.server_default.arg == "新对话"

    def test_status_default_is_active(self) -> None:
        status_col = Thread.__table__.columns["status"]
        assert status_col.server_default.arg == "active"

    def test_user_id_is_not_nullable(self) -> None:
        assert Thread.__table__.columns["user_id"].nullable is False

    def test_indexes_present(self) -> None:
        idx_names = {idx.name for idx in Thread.__table__.indexes}
        assert "idx_threads_user_id" in idx_names
        assert "idx_threads_status" in idx_names


class TestMessageModel:
    """Message ORM schema 锁定（data-model.md §3）。"""

    def test_table_name(self) -> None:
        assert Message.__tablename__ == "messages"

    def test_required_columns_present(self) -> None:
        cols = {c.name for c in Message.__table__.columns}
        expected = {
            "message_id",
            "thread_id",
            "role",
            "content",
            "status",
            "created_at",
            "completed_at",
        }
        assert expected.issubset(cols)

    def test_message_id_is_primary_key(self) -> None:
        pk_cols = [c.name for c in Message.__table__.primary_key.columns]
        assert pk_cols == ["message_id"]

    def test_thread_id_fk_with_cascade(self) -> None:
        fk_cols = [
            c for c in Message.__table__.columns if c.name == "thread_id"
        ]
        assert len(fk_cols) == 1
        fks = list(fk_cols[0].foreign_keys)
        assert len(fks) == 1
        fk = fks[0]
        assert fk.column.table.name == "threads"
        assert fk.column.name == "thread_id"
        assert fk.ondelete == "CASCADE"

    def test_status_default_is_streaming(self) -> None:
        status_col = Message.__table__.columns["status"]
        assert status_col.server_default.arg == "streaming"

    def test_completed_at_is_nullable(self) -> None:
        assert Message.__table__.columns["completed_at"].nullable is True

    def test_index_on_thread_created_at(self) -> None:
        idx_names = {idx.name for idx in Message.__table__.indexes}
        assert "idx_messages_thread_id" in idx_names


class TestEnums:
    """data-model.md 中 3 个 enum 字符串值锁定。"""

    def test_thread_status_values(self) -> None:
        assert ThreadStatus.ACTIVE.value == "active"
        assert ThreadStatus.ARCHIVED.value == "archived"

    def test_message_role_values(self) -> None:
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"

    def test_message_status_values(self) -> None:
        assert MessageStatus.STREAMING.value == "streaming"
        assert MessageStatus.COMPLETE.value == "complete"
        assert MessageStatus.FAILED.value == "failed"


class TestMetadataRegistration:
    """两个模型都注册到 Base.metadata（alembic target）。"""

    def test_base_metadata_contains_both_tables(self) -> None:
        tables = set(Base.metadata.tables.keys())
        assert {"threads", "messages"}.issubset(tables)
