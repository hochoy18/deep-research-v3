"""Async SQLAlchemy engine + sessionmaker + alembic 集成。

约定：
- engine 与 sessionmaker 都用单例（避免每次请求重新创建）
- DATABASE_URL 通过 app.config.Settings 提供（Dev.cai.1 拥有 settings 类，
  本模块仅 import 调用）
- alembic 集成：Base.metadata 暴露给 env.py；migrations 与 Base 字段同步
- 提供 get_session() 上下文管理器给 dep 注入使用
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.models import Base


def _build_database_url() -> str:
    """M1 阶段允许从 env 直读 DATABASE_URL；Dev.cai.1 的 Settings 上线后切换。"""
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres",
    )


# Engine / sessionmaker 单例
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    """获取（或惰性初始化）全局 async engine。

    - echo=False：M1 简化；M2+ 接 sqlalchemy.events 监听器
    - pool_pre_ping=True：避免 stale connection
    - pool_size=5 / max_overflow=10：本地 1-3 用户规模
    """
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _build_database_url(),
            echo=False,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            future=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取（或惰性初始化）sessionmaker 工厂。"""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
            class_=AsyncSession,
        )
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI Depends 注入用的 session 上下文管理器。

    - 自动 commit / rollback / close
    - usage::

        async with get_session() as session:
            result = await session.execute(...)
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """开发期直接 create_all；生产环境必须用 alembic（app/db/migrations/）。"""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def metadata_for_alembic():
    """alembic env.py 调用：拿到 Base.metadata 喂给 target_metadata。"""
    return Base.metadata


# 测试用 reset（避免 import 期连接）
def _reset_singletons_for_tests() -> None:
    """仅测试可调用；强制 next 次 get_*() 重新生成。"""
    global _engine, _session_factory
    if _engine is not None:
        # AsyncEngine 不能在 loop 已 close 后 dispose；这里仅置 None
        _engine = None
    _session_factory = None
