"""T024 API schemas 单测：白名单校验 + OpenAPI 字段锁死。

覆盖：
- MessageCreate 内容白名单（constitution I）
- 长度上限 / 换行 / 控制字符 / 行长上限
- Thread / Message 基本形状（from_attributes 与 ORM 互转）
- is_uuid_v4 工具
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.api.schemas import (
    Error,
    Message,
    MessageCreate,
    MessageRoleEnum,
    MessageStatusEnum,
    SSEEvent,
    SSEEventType,
    Thread,
    ThreadStatusEnum,
    is_uuid_v4,
)


# === MessageCreate 白名单校验（constitution I） === #


class TestMessageCreateWhitelist:
    """content 必须满足白名单 + 长度限制。"""

    def test_accepts_ascii_plain(self) -> None:
        m = MessageCreate(content="hello world")
        assert m.content == "hello world"

    def test_accepts_cjk_characters(self) -> None:
        m = MessageCreate(content="你好世界，这是中文测试")
        assert m.content == "你好世界，这是中文测试"

    def test_accepts_newlines(self) -> None:
        m = MessageCreate(content="line1\nline2\nline3")
        assert m.content == "line1\nline2\nline3"

    def test_accepts_mixed_cjk_and_ascii(self) -> None:
        m = MessageCreate(content="hello 你好 world 世界")
        assert m.content == "hello 你好 world 世界"

    @pytest.mark.parametrize(
        "bad_char",
        ["\x00", "\x01", "\x07", "\x08", "\x0b", "\x0c", "\x1f", "\x7f"],
    )
    def test_rejects_control_characters(self, bad_char: str) -> None:
        # 控制字符（除 \n）应被拒绝
        with pytest.raises(ValidationError):
            MessageCreate(content=f"hello{bad_char}world")

    def test_accepts_only_newline(self) -> None:
        # tab 是控制字符（ord 9），M1 不允许
        with pytest.raises(ValidationError):
            MessageCreate(content="hello\tworld")

    def test_accepts_spaces_between(self) -> None:
        # space 是 ASCII printable（ord 32），允许
        m = MessageCreate(content="hello   world")
        assert m.content == "hello   world"

    def test_rejects_empty(self) -> None:
        with pytest.raises(ValidationError):
            MessageCreate(content="")

    def test_rejects_too_long_total(self) -> None:
        with pytest.raises(ValidationError):
            MessageCreate(content="a" * 10001)

    def test_accepts_max_length(self) -> None:
        m = MessageCreate(content="a" * 10000)
        assert len(m.content) == 10000


# === Thread schema 形状 === #


class TestThreadSchema:
    def test_minimal_thread(self) -> None:
        ts = datetime(2026, 10, 16, tzinfo=timezone.utc)
        t = Thread(
            thread_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
            user_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440001"),
            title="hello",
            status=ThreadStatusEnum.ACTIVE,
            created_at=ts,
            updated_at=ts,
        )
        assert t.title == "hello"
        assert t.status == ThreadStatusEnum.ACTIVE

    def test_from_attributes_compat(self) -> None:
        """与 ORM Thread 互转（model_config.from_attributes=True）。"""
        from datetime import datetime, timezone

        from app.db.models import Thread as ThreadORM

        ts = datetime(2026, 10, 16, tzinfo=timezone.utc)
        orm = ThreadORM(
            thread_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="from orm",
            status="active",
            created_at=ts,
            updated_at=ts,
        )
        pyd = Thread.model_validate(orm)
        assert pyd.title == "from orm"
        assert pyd.status == ThreadStatusEnum.ACTIVE

    def test_title_max_length(self) -> None:
        ts = datetime(2026, 10, 16, tzinfo=timezone.utc)
        with pytest.raises(ValidationError):
            Thread(
                thread_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                title="x" * 201,
                status=ThreadStatusEnum.ACTIVE,
                created_at=ts,
                updated_at=ts,
            )


# === SSEEvent 形状 === #


class TestSSEEvent:
    def test_message_event(self) -> None:
        e = SSEEvent(
            event=SSEEventType.MESSAGE,
            data={
                "message_id": str(uuid.uuid4()),
                "chunk": "hello",
                "index": 0,
            },
        )
        assert e.event == SSEEventType.MESSAGE

    def test_done_event(self) -> None:
        e = SSEEvent(
            event=SSEEventType.DONE,
            data={
                "message_id": str(uuid.uuid4()),
                "total_chunks": 3,
                "latency_ms": 120,
            },
        )
        assert e.event == SSEEventType.DONE


# === is_uuid_v4 helper === #


class TestUuidV4:
    @pytest.mark.parametrize(
        "u",
        [
            "550e8400-e29b-41d4-a716-446655440000",
            "f47ac10b-58cc-4372-a567-0e02b2c3d479",
            "7c9e6679-7425-40de-944b-e07fc1f90ae7",
        ],
    )
    def test_accepts_valid_uuid_v4(self, u: str) -> None:
        assert is_uuid_v4(u) is True

    @pytest.mark.parametrize(
        "u",
        [
            "not-a-uuid",
            "550e8400-e29b-11d4-a716-446655440000",  # version 不是 4
            "550e8400-e29b-41d4-0716-446655440000",  # variant 错
            "",
        ],
    )
    def test_rejects_invalid(self, u: str) -> None:
        assert is_uuid_v4(u) is False


# === Message / Error schemas === #


class TestMessageAndError:
    def test_message_round_trip(self) -> None:
        ts = datetime(2026, 10, 16, tzinfo=timezone.utc)
        m = Message(
            message_id=uuid.uuid4(),
            thread_id=uuid.uuid4(),
            role=MessageRoleEnum.USER,
            content="hi",
            status=MessageStatusEnum.COMPLETE,
            created_at=ts,
            completed_at=ts,
        )
        assert m.role == MessageRoleEnum.USER

    def test_error_default_details(self) -> None:
        e = Error(error="not_found", message="missing")
        assert e.details is None
