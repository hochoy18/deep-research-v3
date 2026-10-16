"""DB URL 工具：asyncio ↔ sync driver 互转（alembic / session 共用）。

提取到独立模块以便单测直接 import，不触碰 alembic context。
"""
from __future__ import annotations

import os


def to_sync_database_url(alembic_config_url: str | None = None) -> str:
    """将 postgresql+asyncpg:// 翻译为 postgresql://（兼容 sync driver）。

    注意：alembic 1.13+ 仍要求同步 driver；本函数是 env.py 与测试共用入口。
    """
    raw = os.environ.get("DATABASE_URL") or alembic_config_url or ""
    if raw.startswith("postgresql+asyncpg://"):
        return raw.replace("postgresql+asyncpg://", "postgresql://", 1)
    return raw
