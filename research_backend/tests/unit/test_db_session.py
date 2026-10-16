"""T020 session 单测：URL 转换 + 单例惰性 init + alembic URL 助手。

不连真实 DB（覆盖单例 + URL 拼接 + URL 转换的纯函数路径）。
集成测试（需要真实 Postgres）由 Dev.cai.4 写（test_thread_crud.py T081）。
"""
from __future__ import annotations

import pytest


class TestBuildDatabaseUrl:
    """session.py URL 构造（读 env 或用 default）。"""

    def test_returns_postgres_async_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from app.db.session import _build_database_url

        url = _build_database_url()
        assert url.startswith("postgresql+asyncpg://")

    def test_returns_env_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        target = "postgresql+asyncpg://u:p@h:5432/d"
        monkeypatch.setenv("DATABASE_URL", target)
        from app.db.session import _build_database_url

        assert _build_database_url() == target


class TestSessionSingletons:
    """engine + sessionmaker 单例行为。"""

    def test_get_engine_returns_singleton(self) -> None:
        from app.db import session as s

        s._reset_singletons_for_tests()
        e1 = s.get_engine()
        e2 = s.get_engine()
        assert e1 is e2

    def test_get_session_factory_returns_singleton(self) -> None:
        from app.db import session as s

        s._reset_singletons_for_tests()
        f1 = s.get_session_factory()
        f2 = s.get_session_factory()
        assert f1 is f2

    def test_reset_clears_singletons(self) -> None:
        from app.db import session as s

        s._reset_singletons_for_tests()
        f1 = s.get_session_factory()
        s._reset_singletons_for_tests()
        f2 = s.get_session_factory()
        assert f1 is not f2


class TestMetadataForAlembic:
    """alembic env 桥接。"""

    def test_metadata_for_alembic_returns_base_metadata(self) -> None:
        from app.db import session as s

        meta = s.metadata_for_alembic()
        assert "threads" in meta.tables
        assert "messages" in meta.tables


class TestSyncUrlConversion:
    """URL 转换纯函数（env.py / 单元测试共用）。"""

    def test_translates_asyncpg_to_psycopg2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.db._url_utils import to_sync_database_url

        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@host/db")
        assert to_sync_database_url() == "postgresql://u:p@host/db"

    def test_passthrough_when_already_sync(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.db._url_utils import to_sync_database_url

        monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@host/db")
        assert to_sync_database_url() == "postgresql://u:p@host/db"

    def test_falls_back_to_alembic_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.db._url_utils import to_sync_database_url

        monkeypatch.delenv("DATABASE_URL", raising=False)
        out = to_sync_database_url("postgresql://x:y@h/d")
        assert out == "postgresql://x:y@h/d"

    def test_empty_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.db._url_utils import to_sync_database_url

        monkeypatch.delenv("DATABASE_URL", raising=False)
        assert to_sync_database_url() == ""
